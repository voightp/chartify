import sys
from pathlib import Path
from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QFontDatabase

from chartify.view.main_window import MainWindow
from chartify.controller.app_controller import AppController
from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.utils.utils import install_fonts
from chartify.settings import Settings
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    root = Path(__file__).parent
    app = QApplication()

    db = QFontDatabase()
    install_fonts(str(Path(root, "resources")), db)
    db.addApplicationFont(str(Path(root, "resources/Roboto-Regular.ttf")))

    Settings.load_reg_settings()

    view = MainWindow()
    model = AppModel()
    wv_controller = WVController(model, view.web_view)
    controller = AppController(model, view, wv_controller)
    view.show()

    sys.exit(app.exec_())
