from PySide2.QtCore import QSettings


class Settings:
    ENERGY_UNITS = QSettings().value("Units/energyUnits", "kWh")
    POWER_UNITS = QSettings().value("Units/powerUnits", "kW")
    UNITS_SYSTEM = QSettings().value("Units/unitsSystem", "SI")
    RATE_TO_ENERGY = bool(QSettings().value("Units/rateToEnergy", 0))
    CUSTOM_UNITS = bool(QSettings().value("Units/customUnits", 1))

    INTERVAL = QSettings().value("interval", None)
    ALL_FILES = bool(QSettings().value("allFiles", 0))
    TOTALS = bool(QSettings().value("totals", 0))
    TREE_VIEW = bool(QSettings().value("treeView", 0))

    IP_ENERGY_UNITS = ["Btu", "kBtu", "MBtu"]
    IP_POWER_UNITS = ["Btu/h", "kBtu/h", "MBtu/h", "W"]
    SI_ENERGY_UNITS = ["Wh", "kWh", "MWh", "J", "MJ", "GJ"]
    SI_POWER_UNITS = ["W", "kW", "MW"]

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
    def write_settings(cls):
        """ Store toolbar settings. """
        QSettings().setValue("Units/energyUnits", cls.ENERGY_UNITS)
        QSettings().setValue("Units/powerUnits", cls.POWER_UNITS)
        QSettings().setValue("Units/unitsSystem", cls.UNITS_SYSTEM)
        QSettings().setValue("Units/customUnits", int(cls.CUSTOM_UNITS))
        QSettings().setValue("Units/rateToEnergy", int(cls.RATE_TO_ENERGY))
        QSettings().setValue("allFiles", int(cls.ALL_FILES))
        QSettings().setValue("treeView", int(cls.TREE_VIEW))
