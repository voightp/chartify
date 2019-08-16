from PySide2.QtGui import QImage, QPixmap, QColor, QPainter, QFont, QFontMetrics
from PySide2.QtWidgets import QApplication, QWidget
from PySide2.QtCore import Qt, QPoint, QBuffer, QTemporaryFile


class Pixmap(QPixmap):
    """
    Wrapper class which allows changing a color
    of .PNG icon.

    Note that this only works well for black and
    transparent icons as all the pixels color is
    overridden using specified RGB values.
    """

    def __init__(self, path, r=0, g=0, b=0, a=1):
        super().__init__(path)

        if not (r == 0 and g == 0 and b == 0 and a == 1):
            self.repaint(path, r, g, b, a)

    def repaint(self, path, r, g, b, a):
        """ Repaint all non-transparent pixels with given color. """
        try:
            img = QImage(path)
            for x in range(img.width()):
                for y in range(img.height()):
                    col = img.pixelColor(x, y)
                    r1, g1, b1, f = col.getRgbF()
                    new_col = QColor(r, g, b, f * 255 * a)
                    img.setPixelColor(x, y, new_col)

            self.convertFromImage(img)

        except IOError:
            print(f"Could not open {path}")

    def as_temp(self):
        """ Save the pixmap as a temporary file. """
        buff = QBuffer()
        self.save(buff, "PNG")

        tf = QTemporaryFile()
        tf.open()
        tf.write(buff.data())
        tf.close()
        return tf


def text_to_pixmap(text, font, color, size=None):
    """ Convert text to QPixmap of a given size. """

    def text_geometry():
        fm = QFontMetrics(font)
        return fm.width(text), fm.height()

    if not size:
        w, h = text_geometry()
    else:
        w, h = size

    pix = QPixmap(w, h)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setPen(color)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignCenter, text)
    p.end()
    return pix
