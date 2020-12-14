from pathlib import Path
from typing import Union, Tuple

from PySide2.QtCore import Qt, QIODevice, QRectF, QSize, QFile
from PySide2.QtGui import QImage, QPixmap, QColor, QPainter, QFontMetrics, QPen, QFont


class Pixmap(QPixmap):
    """ Wrapper class which allows changing a color of .PNG icon.

    Note that this only works well for black and transparent icons
    as all the pixels color is overridden using specified RGB values.

    """

    def __init__(
        self, path: Union[str, Path], r: int = 0, g: int = 0, b: int = 0, a: float = 1
    ):
        super().__init__(path if isinstance(path, str) else str(path))
        if not (r == 0 and g == 0 and b == 0 and a == 1):
            self.repaint(r, g, b, a)

    @classmethod
    def repaint_icon(
        cls, source_path: Path, dest_dir: Path, r: int = 0, g: int = 0, b: int = 0, a: float = 1
    ) -> str:
        """ Repaint given icons and store it into given dir. """
        if not source_path.exists():
            raise FileNotFoundError(f"Cannot find url: '{source_path}'!")
        p = Pixmap(source_path, r, g, b, a)
        name = f"{source_path.stem} {r}{g}{b}{a}" + source_path.suffix
        dest_path = Path(dest_dir, name)
        f = QFile(str(dest_path))
        f.open(QIODevice.WriteOnly)
        p.save(f)
        f.close()
        return f.fileName()

    def repaint(self, r: int, g: int, b: int, a: float) -> None:
        """ Repaint all non-transparent pixels with given color. """
        img = QImage(self.toImage())
        for x in range(img.width()):
            for y in range(img.height()):
                col = img.pixelColor(x, y)
                r1, g1, b1, f = col.getRgbF()
                new_col = QColor(r, g, b, f * 255 * a)
                if f > 0:
                    img.setPixelColor(x, y, new_col)
        self.convertFromImage(img)


def text_to_pixmap(text: str, font: QFont, color: QColor, size: QSize = None) -> QPixmap:
    """ Convert text to QPixmap of a given size. """
    if not size:
        fm = QFontMetrics(font)
        w, h = fm.horizontalAdvance(text), fm.height()
    else:
        w, h = size.width(), size.height()
    pix = QPixmap(w, h)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setPen(color)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignCenter, text)
    p.end()
    return pix


def draw_filled_circle_icon(
    size: QSize,
    c1: QColor,
    c2: QColor = None,
    border_color: QColor = None,
    border_width: int = 1,
    fraction: float = 0.7,
) -> QPixmap:
    """ Draw a pixmap with one or two colors filled circle. """
    pix = QPixmap(size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    w, h = size.width(), size.height()
    x = (w - (fraction * w)) / 2
    y = (h - (fraction * h)) / 2
    rect_w = w * fraction
    rect_y = h * fraction

    rect = QRectF(x, y, rect_w, rect_y)
    p.setBrush(c1)
    p.setPen(QPen(Qt.transparent, 0))

    if not c2:
        # draw full circle
        p.drawChord(rect, 0, 360 * 16)
    else:
        p.drawChord(rect, -90 * 16, -180 * 16)
        p.setBrush(c2)
        p.drawChord(rect, -90 * 16, 180 * 16)

    if border_color:
        # draw the border
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(border_color, border_width))
        p.drawChord(rect, 0, 360 * 16)

    p.end()

    return pix


def draw_radio_icon(
    size: QSize,
    c1: QColor,
    border_color: QColor,
    border_width: int = 1,
    inner_circle_fraction: float = 0.7,
    fraction: float = 0.7,
    checked: bool = True,
) -> QPixmap:
    """ Draw a custom radio button pixmap. """
    pix = QPixmap(size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    w, h = size.width(), size.height()
    x = (w - (fraction * w)) / 2
    y = (h - (fraction * h)) / 2
    rect_w = w * fraction
    rect_y = h * fraction

    # draw outer circle
    outer_rect = QRectF(x, y, rect_w, rect_y)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(border_color, border_width))
    p.drawEllipse(outer_rect)

    # draw inner circle
    x = (w - (fraction * inner_circle_fraction * w)) / 2
    y = (h - (fraction * inner_circle_fraction * h)) / 2
    rect_w = w * fraction * inner_circle_fraction
    rect_y = h * fraction * inner_circle_fraction

    if checked:
        inner_rect = QRectF(x, y, rect_w, rect_y)
        p.setBrush(Qt.NoBrush)
        p.setBrush(c1)
        p.setPen(QPen(Qt.transparent, 0))
        p.drawEllipse(inner_rect)

    p.end()

    return pix


def combine_colors(
    c1: Tuple[int, int, int], c2: Tuple[int, int, int], fraction: float, as_tuple=False
) -> Union[str, Tuple[int, int, int]]:
    """ Combine given colors. """
    # colors need to be passed as rgb tuple
    # fr define fraction of the first color
    rgb = []
    for i in range(3):
        c = c1[i] * fraction + c2[i] * (1 - fraction)
        rgb.append(int(c))
    return tuple(rgb) if as_tuple else f"rgb({', '.join([str(c) for c in rgb])})"
