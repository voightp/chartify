import json
import re
import traceback
from pathlib import Path
from typing import Tuple, Dict, Union, Iterable, Optional, List

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


def string_rgb(rgb: Union[Tuple[int, int, int], Tuple[int, int, int, float]]) -> str:
    """ Create rgb string. """
    if len(rgb) == 4:
        srgb = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {rgb[3]})"
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

    def get_color_tuple(
        self, color_key: str, opacity: float = None
    ) -> Union[Tuple[int, int, int], Tuple[int, int, int, float]]:
        try:
            rgb = self.colors_dct[color_key]
            if opacity:
                # add opacity to rgb request
                if opacity < 0 or opacity > 1:
                    raise InvalidRangeError("Opacity must be a float in range 0.0-1.0")
            return (*rgb, opacity) if opacity else rgb
        except KeyError:
            colors_str = ", ".join(self.colors_dct.keys())
            raise KeyError(
                f"Cannot get color for color key '{color_key}' is it's not "
                f"available, use one of: '{colors_str}'."
            )

    def get_color(self, color_key: str, opacity: float = None) -> str:
        """ Get specified color as string. """
        color_tuple = self.get_color_tuple(color_key, opacity)
        return string_rgb(color_tuple)

    def get_all_colors(self) -> Dict[str, str]:
        """ Get all colors key, color dict (color as string). """
        dct = {}
        for k in self.colors_dct.keys():
            dct[k] = self.get_color(k)
        return dct

    def get_all_color_tuples(self) -> Dict[str, Tuple[int, int, int]]:
        """ Get all colors key, color dict (color as string). """
        dct = {}
        for k in self.colors_dct.keys():
            dct[k] = self.get_color_tuple(k)
        return dct


class CssParser:
    """ A class used to parse input css.

    Lines containing 'palette' color keys or
    images with URL annotation will be parsed.

    Icons defined as: URL(some/path)#PRIMARY_COLOR#20
    will be repainted using given 'palette' color.

    Note that 'parse_css_files' needs to be called
    to process given css files.

    """

    @classmethod
    def parse_line(cls, line: str, color_key: str, rgb: Tuple[int, int, int]) -> str:
        """ Get a color string or tuple. """
        pattern = rf"(.*){color_key}\s?#?(\d\d)?;?"
        prop, opacity = re.findall(pattern, line)[0]
        rgb = rgb if not opacity else (*rgb, perc_to_float(opacity))
        return f"{prop}{string_rgb(rgb)};\n"

    @classmethod
    def parse_url(cls, line: str, color_key: str) -> Tuple[str, str, Optional[float]]:
        """ Parse a line with an url. """
        pattern = rf"(.*)URL\((.*?)\)\s?#{color_key}\s?#?(\d\d)?;"
        try:
            tup = re.findall(pattern, line)
            prop, url, opacity = tup[0]
            opacity = perc_to_float(opacity) if opacity else None
        except IndexError:
            # this is raised when there's no match or unexpected output
            raise InvalidUrlLine(f"Failed to parse {line}.\n{traceback.format_exc()}")
        return prop, url, opacity

    @classmethod
    def parse_url_line(
        cls,
        line: str,
        color_key: str,
        rgb: Tuple[int, int, int],
        source_icons_dir: Path,
        dest_icons_dir: Path,
    ) -> Tuple[str, str]:
        """ Create a new icon based on css line.  """
        prop, url, opacity = cls.parse_url(line, color_key)
        source_path = Path(source_icons_dir, url)
        rgb = (*rgb, opacity) if opacity else rgb
        dest_path = Pixmap.repaint_icon(source_path, dest_icons_dir, *rgb)
        return f"{prop}url({dest_path});\n", dest_path

    @classmethod
    def parse_css(
        cls,
        source_css: Iterable[str],
        palette: Palette,
        source_icons_dir: Path,
        dest_icons_dir: Path,
    ) -> Tuple[str, List[str]]:
        """ Parse given css file. """
        css = ""
        icon_paths = []
        for line in source_css:
            if any(map(lambda x: x in line, palette.COLORS)):
                color_key = next(k for k in palette.COLORS if k in line)
                rgb = palette.get_color_tuple(color_key)
                if "URL" in line or "url" in line:
                    line, icon_path = cls.parse_url_line(
                        line, color_key, rgb, source_icons_dir, dest_icons_dir
                    )
                    icon_paths.append(icon_path)
                else:
                    line = cls.parse_line(line, color_key, rgb)
            css += line
        return css, icon_paths

    @classmethod
    def parse_css_files(
        cls,
        css_paths_or_dir: Union[Path, List[Path]],
        palette: Palette,
        source_icons_dir: Path,
        dest_icons_dir: Path,
    ) -> Tuple[str, List[str]]:
        """ Read and parse given css paths. """
        if isinstance(css_paths_or_dir, list):
            css_paths = css_paths_or_dir
        else:
            css_paths = [path for path in css_paths_or_dir.iterdir() if path.suffix == ".css"]
        css_paths.sort()
        all_css = ""
        all_icon_paths = []
        for path in css_paths:
            with open(path, "r") as f:
                css, icon_paths = cls.parse_css(f, palette, source_icons_dir, dest_icons_dir)
                all_css += css
                all_icon_paths.extend(icon_paths)
        return all_css, all_icon_paths
