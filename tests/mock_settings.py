from PySide2.QtCore import QSettings, QSize, QPoint
from pathlib import Path
from collections import namedtuple

# helper tuple to be returned from pytest fixture
TestTuple = namedtuple("TestTuple", ["widget", "settings"])


class MockSettings:
    """
    Class which represents global application settings.


    """

    ROOT = Path(__file__).parents[1]
    URL = "http://127.0.0.1:8080/"
    PALETTE_PATH = str(Path(ROOT, "styles/palettes.json"))
    CSS_PATH = str(Path(ROOT, "styles/app_style.css"))
    ICONS_PATH = str(Path(ROOT, "icons/"))
    PALETTE = None

    IP_ENERGY_UNITS = ["Btu", "kBtu", "MBtu"]
    IP_POWER_UNITS = ["Btu/h", "kBtu/h", "MBtu/h", "W"]
    SI_ENERGY_UNITS = ["Wh", "kWh", "MWh", "J", "MJ", "GJ"]
    SI_POWER_UNITS = ["W", "kW", "MW"]

    CURRENT_FILE_ID = None

    ENERGY_UNITS = "J"
    POWER_UNITS = "W"
    UNITS_SYSTEM = "SI"
    RATE_TO_ENERGY = False
    CUSTOM_UNITS = True
    LOAD_PATH = ""
    SAVE_PATH = ""
    PALETTE_NAME = "default"

    INTERVAL = None
    ALL_FILES = False
    TOTALS = False
    TREE_VIEW = False

    SIZE = QSize(800, 600)
    POSITION = QPoint(50, 50)
    MIRRORED = False
    SPLIT = [524, 400]

    @classmethod
    def load_reg_settings(cls):
        """ Load application settings. """
        pass

    @classmethod
    def write_reg_settings(cls):
        """ Store application settings. """
        pass
