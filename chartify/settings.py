from PySide2.QtCore import QSettings, QSize, QPoint
from pathlib import Path


class Settings:
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

    ENERGY_UNITS = None
    POWER_UNITS = None
    UNITS_SYSTEM = None
    RATE_TO_ENERGY = None
    CUSTOM_UNITS = None
    FS_PATH = None
    PALETTE_NAME = None

    INTERVAL = None
    ALL_FILES = None
    TOTALS = None
    TREE_VIEW = None

    SIZE = None
    POSITION = None
    MIRRORED = None
    SPLIT = None

    @classmethod
    def as_str(cls):
        return "Current Settings:" \
               f"\n\tInterval: '{cls.INTERVAL}'" \
               f"\n\tEnergy units: '{cls.ENERGY_UNITS}'" \
               f"\n\tPower units: '{cls.POWER_UNITS}'" \
               f"\n\tUnits system: '{cls.UNITS_SYSTEM}'" \
               f"\n\tRate to Energy: '{cls.RATE_TO_ENERGY}'" \
               f"\n\tCustom units: '{cls.CUSTOM_UNITS}'"

    @classmethod
    def load_reg_settings(cls):
        """ Load application settings. """
        s = QSettings()
        cls.ENERGY_UNITS = s.value("Units/energyUnits", "kWh")
        cls.POWER_UNITS = s.value("Units/powerUnits", "kW")
        cls.UNITS_SYSTEM = s.value("Units/unitsSystem", "SI")
        cls.RATE_TO_ENERGY = bool(s.value("Units/rateToEnergy", 0))
        cls.CUSTOM_UNITS = bool(s.value("Units/customUnits", 1))
        cls.FS_PATH = s.value("MainWindow/loadPath", "")
        cls.PALETTE_NAME = s.value("MainWindow/scheme", "default")

        cls.INTERVAL = s.value("MainWindow/interval", None)
        cls.ALL_FILES = bool(s.value("MainWindow/allFiles", 0))
        cls.TOTALS = bool(s.value("MainWindow/totals", 0))
        cls.TREE_VIEW = bool(s.value("MainWindow/treeView", 0))

        cls.SIZE = QSettings().value("MainWindow/size", QSize(800, 600))
        cls.POSITION = QSettings().value("MainWindow/pos", QPoint(50, 50))
        cls.MIRRORED = bool(QSettings().value("MainWindow/mirrored", False))
        cls.SPLIT = (QSettings().value("MainWindow/split", [524, 400]))

    @classmethod
    def write_reg_settings(cls):
        """ Store application settings. """
        s = QSettings()
        s.setValue("Units/energyUnits", cls.ENERGY_UNITS)
        s.setValue("Units/powerUnits", cls.POWER_UNITS)
        s.setValue("Units/unitsSystem", cls.UNITS_SYSTEM)
        s.setValue("Units/customUnits", int(cls.CUSTOM_UNITS))
        s.setValue("Units/rateToEnergy", int(cls.RATE_TO_ENERGY))
        s.setValue("MainWindow/allFiles", int(cls.ALL_FILES))
        s.setValue("MainWindow/treeView", int(cls.TREE_VIEW))
        s.setValue("MainWindow/scheme", cls.PALETTE_NAME)
        s.setValue("MainWindow/loadPath", cls.FS_PATH)
        s.setValue("MainWindow/size", cls.SIZE)
        s.setValue("MainWindow/pos", cls.POSITION)
        s.setValue("MainWindow/mirrored", int(cls.MIRRORED))
        s.setValue("MainWindow/split", cls.SPLIT)
