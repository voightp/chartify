from PySide2.QtGui import QImage, QPixmap, QColor


class Pixmap(QPixmap):
    """
    Wrapper class which allows changing a color
    of .PNG icon.

    Note that this only works well for black and
    transparent icons as all the pixels color is
    overridden using specified RGB values.
    """

    def __init__(self, path, r=0, g=0, b=0, *args, a=1, **kwargs):
        super().__init__(path, *args, **kwargs)

        if not (r == 0 and g == 0 and b == 0 and a == 1):
            self.repaint(path, r, g, b, a)

    def repaint(self, path, r, g, b, a):
        print("Repainting!")
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
            print("Could not open f{path}")
