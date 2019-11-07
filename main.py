import sys

from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QFontDatabase

from esopie.view.main_window import MainWindow
from esopie.controller.app_controller import AppController
from esopie.model.model import AppModel
from esopie.utils.utils import install_fonts
from esopie.settings import Settings

if __name__ == "__main__":
    app = QApplication()

    db = QFontDatabase()
    install_fonts("./resources", db)
    db.addApplicationFont("./resources/Roboto-Regular.ttf")

    Settings.load_reg_settings()

    view = MainWindow()
    model = AppModel()
    controller = AppController(model, view)
    view.show()

    sys.exit(app.exec_())
