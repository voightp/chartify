from pathlib import Path

import pytest
from PySide2.QtCore import Qt
from esofile_reader import EsoFile

from chartify.view.treeview_widget import View
from tests import ROOT


@pytest.fixture(scope="module")
def eso_file():
    return EsoFile(Path(ROOT, "eso_files", "eplusout1.eso"))


@pytest.fixture
def tree_view(qtbot):
    tree_view = View(0, "test")
    tree_view.show()
    qtbot.addWidget(tree_view)
    return tree_view


def test_00_class_attributes(tree_view: View):
    assert tree_view.settings["widths"]["interactive"] == 200
    assert tree_view.settings["widths"]["fixed"] == 70
    assert tree_view.settings["order"] == ("variable", Qt.AscendingOrder)
    assert tree_view.settings["header"] == ["variable", "key", "units"]
    assert tree_view.settings["expanded"] == set()


def test_01_init_tree_view(tree_view: View):
    assert tree_view.rootIsDecorated()
    assert tree_view.uniformRowHeights()
    assert tree_view.isSortingEnabled()
    assert tree_view.hasMouseTracking()

    assert not tree_view.dragEnabled()
    assert not tree_view.wordWrap()
    assert not tree_view.alternatingRowColors()

    assert tree_view.selectionBehavior() == View.SelectRows
    assert tree_view.selectionMode() == View.ExtendedSelection
    assert tree_view.editTriggers() == View.NoEditTriggers
    assert tree_view.defaultDropAction() == Qt.CopyAction
    assert tree_view.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert tree_view.focusPolicy() == Qt.NoFocus

    assert tree_view.id_ == 0
    assert tree_view.name == "test"


def test_02_populate_model(qtbot, tree_view, eso_file):
    hourly_data = None
    print(eso_file)
