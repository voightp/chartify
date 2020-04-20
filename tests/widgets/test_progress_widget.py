import pytest
from PySide2.QtCore import Qt

from chartify.ui.progress_widget import ProgressContainer


@pytest.fixture
def container(qtbot):
    container = ProgressContainer()
    container.show()
    qtbot.add_widget(container)

    for i in range(1, 9):
        container.add_file(f"{i}", f"file-{i}", f"C:/dummy/path/file-{i}.eso")
        container.set_range(f"{i}", 10 * i, 100)

    return container


def test_init(container: ProgressContainer):
    assert len(container.widgets) == 5
    assert len(container.files) == 8
    assert len(container.locked) == 0


def test_sorted_files(qtbot, container: ProgressContainer):
    assert container.sorted_files == list(container.files.values())[::-1]


def test_visible_files(qtbot, container: ProgressContainer):
    test_files = [
        container.files["8"],
        container.files["7"],
        container.files["6"],
        container.files["5"],
        container.files["4"],
    ]
    assert container.visible_files == test_files
    for wgt, f in zip(container.widgets, test_files):
        assert wgt.file_ref == f


def test_invisible_files(qtbot, container: ProgressContainer):
    test_files = [
        container.files["3"],
        container.files["2"],
        container.files["1"],
    ]
    for f in test_files:
        assert not f.widget


def test__get_visible_index(container: ProgressContainer):
    file = container.files["5"]
    assert container._get_visible_index(file) == 3


def test__get_visible_index_hidden(container: ProgressContainer):
    file = container.files["1"]
    assert not container._get_visible_index(file)


def test__position_not_changed(container: ProgressContainer):
    file = container.files["5"]
    assert not container._position_changed(file)


def test__position_changed(container: ProgressContainer):
    file = container.files["5"]
    file.value = 99
    assert container._position_changed(file)


def test__position_changed_hidden_file(container: ProgressContainer):
    file = container.files["1"]
    file.value = 99
    assert container._position_changed(file)


def test__update_bar_display_summary(container: ProgressContainer):
    container.MAX_VISIBLE_JOBS = 4
    container.widgets.pop(0)
    container._update_bar()

    test_files = [
        container.files["8"],
        container.files["7"],
        container.files["6"],
        container.files["5"],
    ]
    assert container.summary.label.text() == "processing 4 files..."
    assert container.visible_files == test_files


def test_add_file(container: ProgressContainer):
    container.add_file("100", "added file", "C:/added/file/path.eso")
    file = container.files["100"]
    assert len(container.files) == 9
    assert file.id_ == "100"
    assert file.label == "added file"
    assert file.file_path == "C:/added/file/path.eso"
    assert file.maximum == 0
    assert file.value == 0
    assert not file.failed
    assert not file.widget


def test_add_file_visible(container: ProgressContainer):
    for i in range(4, 9)[::-1]:
        container.remove_file(str(i))

    container.add_file("100", "added file", "C:/added/file/path.eso")
    file = container.files["100"]
    widget = container.widgets[3]

    assert len(container.files) == 4
    assert file.id_ == "100"
    assert file.label == "added file"
    assert file.file_path == "C:/added/file/path.eso"
    assert file.maximum == 0
    assert file.value == 0
    assert file.status == ""
    assert not file.failed
    assert file.widget == widget

    assert widget.file_ref == file
    assert widget.label
    assert widget.progress_bar.value() == 0
    assert widget.progress_bar.maximum() == 0
    assert widget.file_btn.text == "File: C:/added/file/path.eso\nPhase: "


def test_set_range_invisible_to_visible(container: ProgressContainer):
    container.set_range("1", 500, 1000, "range set!")
    file = container.files["1"]
    widget = container.widgets[3]

    assert container._get_visible_index(file) == 3
    assert file.maximum == 1000
    assert file.value == 500
    assert file.status == "range set!"
    assert file.relative_value == 500 / 1000 * 100
    assert not file.failed
    assert file.widget == widget

    assert widget.file_ref == file
    assert widget.label.text() == "file-1"
    assert widget.progress_bar.value() == 500
    assert widget.progress_bar.maximum() == 1000
    assert widget.file_btn.text == "File: C:/dummy/path/file-1.eso\nPhase: range set!"


def test_update_progress(container: ProgressContainer):
    container.update_progress("8", 99)
    file = container.files["8"]
    widget = container.widgets[0]

    assert container._get_visible_index(file) == 0
    assert file.maximum == 100
    assert file.value == 99
    assert file.relative_value == 99 / 100 * 100

    assert widget.file_ref == file
    assert widget.label.text() == "file-8"
    assert widget.progress_bar.value() == 99
    assert widget.progress_bar.maximum() == 100
    assert widget.file_btn.text == "File: C:/dummy/path/file-8.eso\nPhase: "


def test_update_status_visible(container: ProgressContainer):
    test_status = "testing status!"
    container.set_status("8", test_status)
    file = container.files["8"]
    widget = container.widgets[0]

    assert file.status == "testing status!"
    assert widget.file_btn.text == f"File: C:/dummy/path/file-8.eso\nPhase: {test_status}"


def test_update_status_invisible(container: ProgressContainer):
    test_status = "testing status!"
    container.set_status("1", test_status)
    file = container.files["1"]

    assert file.status == "testing status!"
    assert not file.widget


def test_set_failed(container: ProgressContainer):
    container.set_failed("8", "Failed for some evil reason!")
    file = container.files["8"]
    widget = container.widgets[0]

    assert file.maximum == 999
    assert file.value == 999
    assert file.failed
    assert file.status == "Failed for some evil reason!"
    assert file.widget == widget

    assert widget.file_ref == file
    assert widget.label.text() == "file-8"
    assert widget.progress_bar.value() == 999
    assert widget.progress_bar.maximum() == 999
    assert widget.file_btn.text == f"File: C:/dummy/path/file-8.eso" \
                                        f"\nPhase: Failed for some evil reason!"
    assert widget.property("failed")


def test_set_pending(container: ProgressContainer):
    container.set_pending("8", "pending!")
    file = container.files["8"]
    widget = container.widgets[0]

    assert file.maximum == 0
    assert file.value == 0
    assert file.status == "pending!"

    assert widget.file_ref == file
    assert widget.label.text() == "file-8"
    assert widget.progress_bar.value() == 0
    assert widget.progress_bar.maximum() == 0
    assert widget.file_btn.text == f"File: C:/dummy/path/file-8.eso" \
                                        f"\nPhase: pending!"


def test_remove_file(container: ProgressContainer):
    container.remove_file("8")
    with pytest.raises(KeyError):
        _ = container.files["8"]
    assert len(container.files) == 7


def test_summary_file(container: ProgressContainer):
    summary = container.summary
    assert summary.label.text() == "processing 3 files..."
    assert summary.progress_bar.value() == -1
    assert summary.progress_bar.maximum() == 0
    assert summary.isVisible()


def test_summary_hidden(qtbot, container: ProgressContainer):
    for i in range(4, 9)[::-1]:
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

    assert container.locked == [file]
    assert container.visible_files[0] == file

    with qtbot.wait_signal(widget.remove):
        qtbot.mouseClick(widget.file_btn, Qt.LeftButton)

    with pytest.raises(KeyError):
        _ = container.files["1"]

    assert widget.file_ref == container.files["8"]
    assert not widget.file_btn.isEnabled()
