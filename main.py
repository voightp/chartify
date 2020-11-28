import logging
import sys
from pathlib import Path
import shutil
from PySide2.QtGui import QFontDatabase
from PySide2.QtWidgets import QApplication

from chartify.controller.app_controller import AppController
from chartify.controller.wv_controller import WVController
from chartify.model.model import AppModel
from chartify.settings import Settings
from chartify.ui.main_window import MainWindow
from chartify.utils.utils import install_fonts

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    shutil.rmtree(Settings.APP_TEMP_DIR, ignore_errors=True)
    Settings.APP_TEMP_DIR.mkdir()

    root = Path(__file__).parent
    app = QApplication()

    db = QFontDatabase()
    install_fonts(str(Path(root, "resources/fonts")), db)
    db.addApplicationFont(str(Path(root, "resources/fonts/Roboto-Regular.ttf")))

    Settings.load_settings_from_json()

    view = MainWindow()
    model = AppModel()
    wv_controller = WVController(model, view.web_view)
    controller = AppController(model, view, wv_controller)
    view.show()

    sys.exit(app.exec_())
