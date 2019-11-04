import sys

from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QFontDatabase

from esopie.view.main_window import MainWindow
from esopie.utils.utils import install_fonts

sys_argv = sys.argv
app = QApplication()
db = QFontDatabase()
install_fonts("./resources", db)

db.addApplicationFont("./resources/Roboto-Regular.ttf")
main_window = MainWindow()
main_window.show()

sys.exit(app.exec_())
