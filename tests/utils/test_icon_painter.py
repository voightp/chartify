from pathlib import Path

from PySide2.QtCore import QSize, Qt
from PySide2.QtGui import QColor, QFont

from chartify.utils.icon_painter import (
    Pixmap,
    text_to_pixmap,
    draw_filled_circle_icon,
    combine_colors,
)
from tests import ROOT


class TestPixmap:
    def test_repaint(self, qtbot):
        p = Pixmap(Path(ROOT, "./resources/icons/test.png"), r=110, g=120, b=110, a=0.5)
        img = p.toImage()
        assert img.pixelColor(10, 10).getRgb() == QColor(110, 120, 110, 127).getRgb()


def test_text_to_pixmap(qtbot):
    f = QFont("Times", 20, QFont.Bold)
    p = text_to_pixmap("TEST TEXT", f, QColor(100, 100, 100))
    assert p.size() == QSize(149, 31)


def test_text_to_pixmap_set_size(qtbot):
    f = QFont("Times", 20, QFont.Bold)
    p = text_to_pixmap("TEST TEXT", f, QColor(100, 100, 100), size=QSize(200, 200))
    assert p.size() == QSize(200, 200)


def test_filled_circle_pixmap(qtbot):
    p = draw_filled_circle_icon(QSize(100, 100), QColor(100, 100, 100))
    img = p.toImage()
    assert p.size() == QSize(100, 100)
    assert img.pixelColor(50, 50) == QColor(100, 100, 100)


def test_filled_circle_pixmap_fraction(qtbot):
    p = draw_filled_circle_icon(QSize(100, 100), QColor(100, 100, 100), fraction=0.1)
    img = p.toImage()
    assert p.size() == QSize(100, 100)
    assert img.pixelColor(35, 50) == Qt.transparent


def test_filled_circle_pixmap_border(qtbot):
    p = draw_filled_circle_icon(
        QSize(100, 100),
        QColor(100, 100, 100),
        border_color=QColor(200, 200, 200),
        border_width=5,
    )
    img = p.toImage()
    assert img.pixelColor(16, 50) == QColor(200, 200, 200)


def test_filled_circle_pixmap_two_colors(qtbot):
    p = draw_filled_circle_icon(QSize(100, 100), QColor(100, 100, 100), QColor(0, 0, 0))
    img = p.toImage()
    assert p.size() == QSize(100, 100)
    assert img.pixelColor(35, 50) == QColor(100, 100, 100)
    assert img.pixelColor(65, 50) == QColor(0, 0, 0)


def test_combine_colors(qtbot):
    c = combine_colors((100, 100, 100), (0, 0, 0), fraction=0.5)
    assert c == "rgb(50, 50, 50)"


def test_combine_colors_as_tuple(qtbot):
    c = combine_colors((100, 100, 100), (0, 0, 0), fraction=0.5, as_tuple=True)
    assert c == (50, 50, 50)
