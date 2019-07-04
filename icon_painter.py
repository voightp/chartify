from PySide2.QtWidgets import QApplication, QWidget
from PySide2.QtCore import Qt, QPoint
from PySide2.QtGui import QPixmap, QPainter, QFont, QImage, QFontDatabase
import sys
from icons import Pixmap, text_to_pixmap
from app import install_fonts

app = QApplication()
db = QFontDatabase()
install_fonts("./resources", db)
db.addApplicationFont("./resources/Roboto-Regular.ttf")

col = dict(r=255, g=255, b=255)
f1 = Pixmap("./icons/check_black.png", **col)

f1.save("./icons/check_white.png")



