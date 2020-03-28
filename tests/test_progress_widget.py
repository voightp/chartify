import pytest

from chartify.ui.progress_widget import ProgressContainer


@pytest.fixture
def container(qtbot):
    container = ProgressContainer()
    container.show()
    qtbot.add_widget(container)
    return container


def test_sorted_files():
    assert False


def test_visible_files():
    assert False


def test_visible_widgets():
    assert False


def test__get_visible_index():
    assert False


def test__position_changed():
    assert False


def test__update_bar():
    assert False


def test_add_file():
    assert False


def test_set_range():
    assert False


def test_update_progress():
    assert False


def test_set_failed():
    assert False


def test_set_pending():
    assert False


def test_remove_file():
    assert False
