import pytest
import pytestqt
import time

from chartify.view.treeview_widget import View


@pytest.fixture
def tree_view(qtbot):
    tree_view = View(0, "test")
    tree_view.show()
    return tree_view


def test_01_init_tree_view(qtbot, tree_view):
    assert tree_view.rootIsDecorated()
    assert tree_view.uniformRowHeights()
    assert tree_view.isSortingEnabled()
    assert tree_view.hasMouseTracking()

    qtbot.addWidget(tree_view)


def test_02_update_model(qtbot, tree_view):
    assert tree_view.rootIsDecorated()
    assert tree_view.uniformRowHeights()
    assert tree_view.isSortingEnabled()
    assert tree_view.hasMouseTracking()

    qtbot.addWidget(tree_view)
