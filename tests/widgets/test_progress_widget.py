import pytest
from PySide2.QtCore import Qt

from chartify.ui.widgets.progress_widget import ProgressContainer


@pytest.fixture
def container(qtbot):
    container = ProgressContainer(None, n_visible_widgets=3)
    container.show()
    qtbot.add_widget(container)

    for i in range(1, 6):
        container.add_file(f"{i}", f"file-{i}", f"C:/dummy/path/file-{i}.eso")
        container.set_range(f"{i}", 10 * i, 100)

    return container


def test_init(container: ProgressContainer):
    assert len(container.widgets) == 3
    assert len(container.files) == 5


def test_sorted_files(qtbot, container: ProgressContainer):
    assert container.sorted_files == list(container.files.values())


def test_visible_files(qtbot, container: ProgressContainer):
    test_files = [container.files["1"], container.files["2"]]
    for wgt, f in zip(container.widgets, test_files):
        assert wgt.file_ref == f


def test_invisible_files(qtbot, container: ProgressContainer):
    for f in [container.files["5"], container.files["4"], container.files["3"]]:
        assert not f.widget


def test_add_file(container: ProgressContainer):
    container.add_file("100", "added file", "C:/added/file/path.eso")
    file = container.files["100"]
    assert len(container.files) == 6
    assert file.id_ == "100"
    assert file.label == "added file"
    assert file.file_path == "C:/added/file/path.eso"
    assert file.maximum == 0
    assert file.value == 0
    assert not file.failed
    assert not file.widget


def test_update_progress(container: ProgressContainer):
    container.update_progress("1", 99)
    file = container.files["1"]
    widget = container.widgets[0]

    assert file.maximum == 100
    assert file.value == 99

    assert widget.file_ref == file
    assert widget.label.text() == "file-1"
    assert widget.progress_bar.value() == 99
    assert widget.progress_bar.maximum() == 100
    assert widget.file_btn.status == "File: C:/dummy/path/file-1.eso\n"


def test_update_status_visible(container: ProgressContainer):
    test_status = "testing status!"
    container.set_status("1", test_status)
    file = container.files["1"]
    widget = container.widgets[0]

    assert file.status == "testing status!"
    assert widget.file_btn.status == f"File: C:/dummy/path/file-1.eso\n{test_status}"


def test_update_status_invisible(container: ProgressContainer):
    test_status = "testing status!"
    container.set_status("5", test_status)
    file = container.files["5"]

    assert file.status == "testing status!"
    assert not file.widget


def test_set_failed(container: ProgressContainer):
    container.set_failed("1", "Failed for some evil reason!")
    file = container.files["1"]
    widget = container.widgets[0]

    assert file.maximum == 999
    assert file.value == 999
    assert file.failed
    assert file.status == "Failed for some evil reason!"
    assert file.widget == widget

    assert widget.file_ref == file
    assert widget.label.text() == "file-1"
    assert widget.progress_bar.value() == 999
    assert widget.progress_bar.maximum() == 999
    assert (
        widget.file_btn.status == "File: C:/dummy/path/file-1.eso"
        "\nFailed for some evil reason!"
    )
    assert widget.property("failed")


def test_set_pending(container: ProgressContainer):
    container.set_pending("1")
    file = container.files["1"]
    widget = container.widgets[0]

    assert file.maximum == 0
    assert file.value == 0

    assert widget.file_ref == file
    assert widget.label.text() == "file-1"
    assert widget.progress_bar.value() == 0
    assert widget.progress_bar.maximum() == 0


def test_remove_file(container: ProgressContainer):
    container.remove_file("1")
    with pytest.raises(KeyError):
        _ = container.files["1"]
    assert len(container.files) == 4


def test_summary_file(container: ProgressContainer):
    summary = container.summary
    assert summary.label.text() == "+ 3 files..."
    assert summary.progress_bar.value() == -1
    assert summary.progress_bar.maximum() == 0
    assert summary.isVisible()


def test_summary_hidden(qtbot, container: ProgressContainer):
    for i in range(4, 6)[::-1]:
        container.remove_file(str(i))

    summary = container.summary
    assert summary.label.text() == ""
    assert not summary.isVisible()


def test_button_disabled(qtbot, container: ProgressContainer):
    for wgt in container.widgets:
        assert not wgt.file_btn.isEnabled()
        with qtbot.assert_not_emitted(wgt.remove):
            qtbot.mouseClick(wgt.file_btn, Qt.LeftButton)


def test_button_remove_file(qtbot, container: ProgressContainer):
    container.set_failed("1", "Horribly failed!")
    file = container.files["1"]
    widget = container.widgets[0]

    assert file.widget == widget
    assert widget.file_ref == file
    assert widget.file_btn.isEnabled()
    assert widget.property("failed")

    with qtbot.wait_signal(widget.remove):
        qtbot.mouseClick(widget.file_btn, Qt.LeftButton)

    with pytest.raises(KeyError):
        _ = container.files["1"]

    assert widget.file_ref == container.files["2"]
    assert not widget.file_btn.isEnabled()
