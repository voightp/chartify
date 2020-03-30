import pytest

from chartify.ui.progress_widget import ProgressContainer


@pytest.fixture
def container(qtbot):
    container = ProgressContainer()
    container.show()
    qtbot.add_widget(container)

    for i in range(1, 9):
        container.add_file(str(i), f"file-{i}")
        container.set_range(str(i), 10 * i, 100)

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
        container.files[str(7)],
        container.files[str(6)],
        container.files[str(5)],
        container.files[str(4)],
        summary
    ]
    assert container.visible_files == test_files


def test__get_visible_index(container: ProgressContainer):
    file = container.files[str(5)]
    assert container._get_visible_index(file) == 2


def test__get_visible_index_hidden(container: ProgressContainer):
    file = container.files[str(1)]
    assert not container._get_visible_index(file)


def test__position_changed(container: ProgressContainer):
    assert False


def test__update_bar(container: ProgressContainer):
    assert False


def test_add_file(container: ProgressContainer):
    assert False


def test_set_range(container: ProgressContainer):
    assert False


def test_update_progress(container: ProgressContainer):
    assert False


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
