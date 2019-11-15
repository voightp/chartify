import sys

from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QFontDatabase

from chartify.view.main_window import MainWindow
from chartify.controller.app_controller import AppController
from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.utils.utils import install_fonts
from chartify.settings import Settings

if __name__ == "__main__":
    app = QApplication()

    db = QFontDatabase()
    install_fonts("./resources", db)
    db.addApplicationFont("./resources/Roboto-Regular.ttf")

    Settings.load_reg_settings()

    view = MainWindow()
    model = AppModel()
    controller = AppController(model, view)
    wv_controller = WVController(model, view.web_view)
    view.show()

    sys.exit(app.exec_())
