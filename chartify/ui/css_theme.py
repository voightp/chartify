import json
import re
import traceback
from collections import namedtuple
from typing import Tuple, Dict, Union, Iterable

from chartify.settings import Settings
from chartify.ui.icons import Pixmap

Color = namedtuple("Color", "r, g, b")


def parse_color(color: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """ Get standard plain rgb tuple. """
    if isinstance(color, tuple) and len(color) == 3:
        rgb = color
    elif color.startswith("rgb"):
        srgb = re.sub("[rgb() ]", "", color)
        rgb = tuple([int(i) for i in srgb.split(",")])
    elif color.startswith("#") and len(color) == 7:
        rgb = tuple([int(color[i: i + 2], 16) for i in range(1, 7, 2)])
    else:
        raise TypeError(f"Cannot parse color {color}!")
    return rgb


def parse_palette(pth: str) -> Dict[str, "Palette"]:
    """ Return a list of palette instances. """
    palettes = {}
    with open(pth) as f:
        ps = json.load(f)
        for name, p in ps.items():
            palettes[name] = Palette(name, **p)
    return palettes


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
            **kwargs: Union[str, Tuple[int, int, int]]
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

    def get_color(
            self, color_key: str, opacity: float = None, as_tuple: bool = False
    ) -> Union[Tuple[int, int, int], Tuple[int, int, int, float], str]:
        """ Get specified color as string. """
        try:
            rgb = self.colors_dct[color_key]
            if opacity:
                # add opacity to rgb request
                rgb = (*rgb, opacity)
            srgb = ",".join([str(i) for i in rgb])
            if as_tuple:
                # this can be rgba
                return rgb
            return f"rgb({srgb})" if len(rgb) == 3 else f"rgba({srgb})"
        except KeyError:
            colors_str = ", ".join(self.COLORS)
            print(
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
    def parse_line(
            line: str, palette: Palette, as_tuple: bool = False
    ) -> Union[Tuple[int, int, int], Tuple[int, int, int, float], str]:
        """ Parse a line with color. """
        key = next(k for k in palette.COLORS if k in line)
        pattern = f"(.*){key}\s?#?(\d\d)?;?"
        prop, opacity = re.findall(pattern, line)[0]
        if opacity:
            opacity = round((int(opacity) / 100), 2)
        rgb = palette.get_color(key, opacity, as_tuple=as_tuple)
        return rgb if as_tuple else f"{prop}{rgb};\n"

    def parse_url(self, line: str, palette: Palette) -> str:
        """ Parse a line with an url. """
        pattern = "(.*)URL\((.*?)\)\s?#(.*);"
        try:
            tup = re.findall(pattern, line)
            prop, url, col = tup[0]
            rgb = self.parse_line(col, palette, as_tuple=True)
            if rgb:
                # a temporary file is required to store repainted pixmap
                p = Pixmap(str(Settings.ROOT) + url, *rgb)
                tf = p.as_temp()
                self._temp.append(tf)
                line = f"{prop}url({tf.fileName()});\n"
        except (IndexError, ValueError):
            # this is raised when there's no match or unexpected output
            print(f"Failed to parse {line}.\n{traceback.format_exc()}")
        return line

    def parse_css(self, source_css: Iterable[str], palette: Palette) -> str:
        """ Parse given css files. """
        css = ""
        for line in source_css:
            if "URL" in line:
                line = self.parse_url(line, palette)
            elif any(map(lambda x: x in line, palette.COLORS)):
                line = self.parse_line(line, palette)
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
