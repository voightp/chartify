import json
from pathlib import Path
from typing import Optional

from PySide2.QtCore import QSize


class Settings:
    """
    Class which represents global application settings.


    """

    ROOT = Path(__file__).parents[1]
    URL = "http://127.0.0.1:8080/"
    PALETTE_PATH = str(Path(ROOT, "resources/styles/palettes.json"))
    CSS_PATH = str(Path(ROOT, "resources/styles/app_style.css"))
    ICONS_PATH = str(Path(ROOT, "resources/icons/"))
    SETTINGS_PATH = Path(Path.home(), ".chartify", "settings.json")

    IP_ENERGY_UNITS = ["Btu", "kBtu", "MBtu"]
    IP_POWER_UNITS = ["Btu/h", "kBtu/h", "MBtu/h", "W"]
    SI_ENERGY_UNITS = ["Wh", "kWh", "MWh", "J", "MJ", "GJ"]
    SI_POWER_UNITS = ["W", "kW", "MW"]

    ICON_SMALL_SIZE = QSize(20, 20)
    ICON_MEDIUM_SIZE = QSize(40, 40)
    ICON_LARGE_SIZE = QSize(60, 60)

    PALETTE = None

    CURRENT_FILE_ID = None

    ENERGY_UNITS = None
    POWER_UNITS = None
    UNITS_SYSTEM = None
    RATE_TO_ENERGY = None
    CUSTOM_UNITS = None
    LOAD_PATH = None
    SAVE_PATH = None
    PALETTE_NAME = None

    TABLE_NAME = None
    ALL_FILES = None
    TOTALS = None
    TREE_NODE = None
    SHOW_SOURCE_UNITS = None

    SIZE = None
    POSITION = None
    MIRRORED = None
    SPLIT = None

    SIMPLE = None
    TREE = None

    _EXCLUDE = [
        "_EXCLUDE",
        "ROOT",
        "PALETTE",
        "TABLE_NAME",
        "URL",
        "PALETTE_PATH",
        "CSS_PATH",
        "ICONS_PATH",
        "ICON_SMALL_SIZE",
        "ICON_MEDIUM_SIZE",
        "ICON_LARGE_SIZE",
        "SETTINGS_PATH",
    ]

    @classmethod
    def attribute_dict(cls):
        attrs = [a for a in dir(cls) if not a.startswith("__")]
        return {a: getattr(cls, a) for a in attrs if not callable(getattr(cls, a))}

    @classmethod
    def units_dict(cls):
        return {
            "energy_units": cls.ENERGY_UNITS,
            "power_units": cls.POWER_UNITS,
            "units_system": cls.UNITS_SYSTEM,
            "rate_to_energy": cls.RATE_TO_ENERGY,
        }

    @classmethod
    def as_str(cls):
        s = "Current Settings:"
        for k, v in cls.attribute_dict().items():
            s += f"\n\t{k}: '{v}'"
        return s

    @classmethod
    def load_settings_from_json(cls, path: Optional[str] = None):
        """ Load application settings from JSON file. """
        if not path:
            if cls.SETTINGS_PATH.exists():
                path = cls.SETTINGS_PATH
            else:
                path = Path(cls.ROOT, "resources", "default.json")
        with open(path, "r") as f:
            settings = json.load(f)
            for k, v in settings.items():
                setattr(cls, k, v)

    @classmethod
    def save_settings_to_json(cls, path: Optional[str] = None):
        """ Save application settings into JSON file. """
        if not path:
            root = cls.SETTINGS_PATH.parent
            Path.mkdir(root, exist_ok=True)
            path = cls.SETTINGS_PATH
        attrs = {k: v for k, v in cls.attribute_dict().items() if k not in cls._EXCLUDE}
        with open(path, "w") as f:
            json.dump(attrs, f)
