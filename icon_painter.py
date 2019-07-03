from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt
from PySide2.QtGui import QPixmap
import sys
from icons import Pixmap

app = QApplication()

col = dict(r=255, g=255, b=255)
# f1 = Pixmap("./icons/chevron_right.png", **col)
# f2 = Pixmap("./icons/chevron_left.png", **col)
#
# f1.save("./icons/chevron_right_white.png")
# f2.save("./icons/chevron_left_white.png")

tr = QPixmap(16, 16)
tr.fill(Qt.transparent)
tr.save("./icons/transparent.png")

