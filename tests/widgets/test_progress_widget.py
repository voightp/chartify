import pytest

from chartify.ui.progress_widget import ProgressContainer


@pytest.fixture
def container(qtbot):
    container = ProgressContainer()
    container.show()
    qtbot.add_widget(container)

    for i in range(1, 9):
        container.add_file(f"{i}", f"file-{i}")
        container.set_range(f"{i}", 10 * i, 100)

    return container


def test_init(container: ProgressContainer):
    assert len(container.widgets) == 5
    assert len(container.files) == 8
    assert len(container.locked) == 0


def test_sorted_files(qtbot, container: ProgressContainer):
    assert container.sorted_files == list(container.files.values())[::-1]


def test_visible_files(qtbot, container: ProgressContainer):
    summary = container.widgets[-1].file_ref
    test_files = [
        container.files["8"],
        container.files["7"],
        container.files["6"],
        container.files["5"],
        summary
    ]
    assert container.visible_files == test_files


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
    summary = container.widgets[-1].file_ref
    test_files = [
        container.files["8"],
        container.files["7"],
        container.files["6"],
        summary
    ]
    assert summary.label == "processing 5 files..."
    assert container.visible_files == test_files


def test_add_file(container: ProgressContainer):
    container.add_file("100", "added file")
    file = container.files["100"]
    assert len(container.files) == 9
    assert file.id_ == "100"
    assert file.label == "added file"
    assert file.maximum == 0
    assert file.value == 0
    assert not file.failed


def test_set_range(container: ProgressContainer):
    container.set_range("8", 1, 200)
    file = container.files["8"]
    assert not container._get_visible_index(file)
    assert file.maximum == 200
    assert file.value == 1
    assert file.relative_value == 1 / 200 * 100
    assert not file.failed


def test_update_progress(container: ProgressContainer):
    container.update_progress("8", 99)
    file = container.files["8"]
    assert not container._get_visible_index(file)
    assert file.maximum == 100
    assert file.value == 99
    assert file.relative_value == 99 / 100 * 100
    assert not file.failed


def test_set_failed(container: ProgressContainer):
    assert False


def test_set_pending(container: ProgressContainer):
    assert False


def test_remove_file(container: ProgressContainer):
    assert False


def test_summary_file(container: ProgressContainer):
    summary = container.widgets[-1].file_ref
    assert summary.maximum == 0
    assert summary.value == 0
    assert summary.label == "processing 4 files..."
    assert summary.file_ref == "summary"
    assert summary.failed == False
