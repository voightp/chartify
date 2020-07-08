import json
import re
import traceback
from pathlib import Path
from typing import Tuple, Dict, Union, Iterable

from PySide2.QtCore import QTemporaryFile

from chartify.settings import Settings
from chartify.utils.icon_painter import Pixmap


class InvalidRangeError(Exception):
    """ Exception raised when input does not fin in given range. """

    pass


class InvalidUrlLine(Exception):
    """ Exception raised for unexpected URL line syntax. """

    pass


def parse_color(color: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """ Get standard plain rgb tuple. """
    if isinstance(color, tuple) and len(color) == 3:
        rgb = color
    elif isinstance(color, str):
        if color.startswith("rgb") and not color.startswith("rgba"):
            srgb = re.sub("[rgb() ]", "", color)
            rgb = tuple([int(i) for i in srgb.split(",")])
        elif color.startswith("#") and len(color) == 7:
            rgb = tuple([int(color[i : i + 2], 16) for i in range(1, 7, 2)])
        else:
            raise TypeError(f"Cannot parse color {color}!")
    else:
        raise TypeError(f"Cannot parse color {color}!")
    return rgb


def perc_to_float(perc: Union[str, int]) -> float:
    """ Convert decimal percentage to float. """
    if isinstance(perc, str):
        perc = int(perc)
    return round(int(perc) / 100, 2) if perc else None


def string_rgb(rgb: Tuple[int, int, int], opacity: float = None) -> str:
    """ Create rgb string. """
    if opacity:
        srgb = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})"
    else:
        srgb = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    return srgb


class Palette:
    """ A class to define color set used for an application.

    Colors can be defined either using HEX or rgb string
    and rgb tuples.

    When an available kwarg is not populated, default color
    is used.

    Arguments
    ---------
    default_color : tuple
        A default color which will be used when available
        kwarg is not specified.

    **kwargs
        primary_color, primary_text_color, secondary_color, error_color,
        secondary_text_color, background_color, surface_color, ok_color

    """

    COLORS = [
        "PRIMARY_COLOR",
        "PRIMARY_TEXT_COLOR",
        "SECONDARY_COLOR",
        "SECONDARY_TEXT_COLOR",
        "BACKGROUND_COLOR",
        "SURFACE_COLOR",
        "ERROR_COLOR",
        "OK_COLOR",
    ]

    def __init__(
        self,
        name: str,
        default_color: Tuple[int, int, int] = (255, 255, 255),
        **kwargs: Union[str, Tuple[int, int, int]],
    ):
        self.name = name
        dct = {}
        for c in self.COLORS:
            try:
                color = kwargs[c.upper()]
                rgb = parse_color(color)
            except KeyError:
                print(f"'{c}' has not been provided assigning default")
                rgb = default_color
            dct[c] = rgb
        self.colors_dct = dct

    @classmethod
    def parse_palettes(
        cls, pth: str, default_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Dict[str, "Palette"]:
        """ Extract palette dictionary from json file. """
        palettes = {}
        with open(pth) as f:
            ps = json.load(f)
            for name, p in ps.items():
                palettes[name] = cls(name, default_color=default_color, **p)
        return palettes

    def get_color(
        self, color_key: str, opacity: float = None, as_tuple: bool = False
    ) -> Union[Tuple[int, int, int], Tuple[int, int, int, float], str]:
        """ Get specified color as string. """
        try:
            rgb = self.colors_dct[color_key]
            if opacity:
                # add opacity to rgb request
                if opacity < 0 or opacity > 1:
                    raise InvalidRangeError("Opacity must be a float in range 0.0-1.0")
            return (
                ((*rgb, opacity) if opacity else rgb)
                if as_tuple
                else string_rgb(rgb, opacity=opacity)
            )
        except KeyError:
            colors_str = ", ".join(self.colors_dct.keys())
            raise KeyError(
                f"Cannot get color for color key '{color_key}' is it's not "
                f"available, use one of: '{colors_str}'."
            )

    def get_all_colors(
        self, as_tuple: bool = False
    ) -> Dict[str, Union[Tuple[int, int, int], str]]:
        """ Get all colors key, color dict (color as string). """
        dct = {}
        for k in self.colors_dct.keys():
            dct[k] = self.get_color(k, as_tuple=as_tuple)
        return dct


class CssTheme:
    """ A class used to parse input css.

    Lines containing 'palette' color keys or
    images with URL annotation will be parsed.

    Icons defined as: URL(some/path)#PRIMARY_COLOR#20
    will be repainted using given 'palette' color.

    Note that 'populate_content' needs to be called
    to process given css files.

    Arguments
    ---------
    palette : Palette
        Defines color theme.
    *args
        Css file paths.

    """

    def __init__(self, *args):
        self.css_paths = list(args)
        self.content = ""
        self._temp = []

    @staticmethod
    def parse_line(line: str, color_key: str, rgb: Tuple[int, int, int]) -> str:
        """ Get a color string or tuple. """
        pattern = f"(.*){color_key}\s?#?(\d\d)?;?"
        prop, opacity = re.findall(pattern, line)[0]
        srgb = string_rgb(rgb, opacity=perc_to_float(opacity) if opacity else None)
        return f"{prop}{srgb};\n"

    @staticmethod
    def parse_url(
        line: str, color_key: str, rgb: Tuple[int, int, int]
    ) -> Tuple[str, QTemporaryFile]:
        """ Parse a line with an url. """
        pattern = f"(.*)URL\((.*?)\)\s?#{color_key}\s?#?(\d\d)?;"
        try:
            tup = re.findall(pattern, line)
            prop, url, opacity = tup[0]
            rgb = rgb if not opacity else (*rgb, perc_to_float(opacity) if opacity else None)
            # a temporary file is required to store repainted pixmap
            path = Path(Settings.ROOT, Path(url))
            if not path.exists():
                raise FileNotFoundError(f"Cannot find url: '{path}'!")
            p = Pixmap(str(path), *rgb)
            tf = p.as_temp()
            line = f"{prop}url({tf.fileName()});\n"
        except IndexError:
            # this is raised when there's no match or unexpected output
            raise InvalidUrlLine(f"Failed to parse {line}.\n{traceback.format_exc()}")
        return line, tf

    def parse_css(self, source_css: Iterable[str], palette: Palette) -> str:
        """ Parse given css file. """
        css = ""
        for line in source_css:
            if any(map(lambda x: x in line, palette.COLORS)):
                color_key = next(k for k in palette.COLORS if k in line)
                rgb = palette.get_color(color_key, as_tuple=True)
                if "URL" in line:
                    line, tf = self.parse_url(line, color_key, rgb)
                    self._temp.append(tf)
                else:
                    line = self.parse_line(line, color_key, rgb)
            css += line
        return css

    def populate_content(self, palette: Palette) -> None:
        """ Update palette. """
        self._temp.clear()  # temp icons will be created again
        content = ""
        for file in self.css_paths:
            with open(file, "r") as f:
                css = self.parse_css(f, palette)
                content += css
        self.content = content
