import re
from collections import namedtuple
from esopie.icons import Pixmap
from eso_reader.performance import perf
from PySide2.QtCore import QTemporaryFile

Color = namedtuple("Color", "r, g, b")


class Palette:
    """
    A class to define color set used for an application.

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
        primary_color, primary_variant_color, primary_text_color,
        secondary_color, secondary_variant_color, secondary_text_color,
        background_color, surface_color, error_color, ok_color


    """
    colors = [
        "PRIMARY_COLOR",
        "PRIMARY_VARIANT_COLOR",
        "PRIMARY_TEXT_COLOR",
        "SECONDARY_COLOR",
        "SECONDARY_VARIANT_COLOR",
        "SECONDARY_TEXT_COLOR",
        "BACKGROUND_COLOR",
        "SURFACE_COLOR",
        "ERROR_COLOR",
        "OK_COLOR",
    ]

    def __init__(self, default_color=(255, 255, 255), **kwargs):
        self.colors_dct = self.parse_inst_kwargs(default_color, **kwargs)

    @staticmethod
    def parse_color(color):
        """ Get standard plain rgb tuple. """
        rgb = None
        if not color:
            print("Color not specified.")
            rgb = None
        elif isinstance(color, tuple) and len(color) == 3:
            rgb = color
        elif color.startswith("rgb"):
            srgb = re.sub('[rgb() ]', '', color)
            rgb = tuple(srgb.split(","))
        elif color.startswith("#") and len(color) == 7:
            rgb = tuple([int(color[i: i + 2], 16) for i in range(1, 7, 2)])
        else:
            s = color
            if not isinstance(s, (int, str, float)):
                #  this is just a basic test
                s = "".join(s)
            print(f"Failed to parse color: '{s}'")

        return rgb

    def parse_inst_kwargs(self, default_color, **kwargs):
        """ Process input kwargs. """
        dct = {}

        for c in self.colors:
            try:
                color = kwargs[c.upper()]
                rgb = self.parse_color(color)
                if not rgb:
                    print(f"'{c}' assigned as default.")
                    rgb = default_color

            except KeyError:
                print(f"'{c}' has not been provided, "
                      f"assigning default")
                rgb = default_color

            dct[c] = rgb

        return dct

    def get_color(self, color_key, opacity=None, as_tuple=False):
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
            colors_str = ", ".join(self.colors)
            print(f"Cannot get color for color key '{color_key}' is it's not "
                  f"available, use one of: '{colors_str}'.")

    def set_color(self, **kwargs):
        """ Set specified colors as 'color_key : color' pairs. """
        try:
            for k, v in kwargs.items():
                self.colors_dct[k] = v
        except KeyError:
            colors_str = ", ".join(self.colors)
            print(f"Cannot set color '{v}', color key '{k}' is not "
                  f"available, use one of: '{colors_str}'.")


class CssTheme:
    """
    A class used to parse input css.

    Lines containing 'palette' color keys or
    images with URL annotation will be parsed.

    Icons defined as: URL(some/path)#PRIMARY_COLOR#20
    will be repainted using given 'palette' color.

    Arguments
    ---------
    palette : Palette
        Defines color theme.

    """

    def __init__(self, palette):
        self.palette = palette
        self._temp = []

    @perf
    def process_csss(self, *args):
        """ Process multiple css files. """
        all_css = ""
        for file in args:
            with open(file, "r") as f:
                css = self.parse_css(f)
                all_css += css

        return all_css

    def parse_url(self, line):
        """ Parse a line with an url. """
        pattern = "(.*)URL\((.*?)\)#(.*);"
        try:
            tup = re.findall(pattern, line)
            prop, url, col = tup[0]
            rgb = self.parse_color(col, as_tuple=True)
            if rgb:
                p = Pixmap(url, *rgb)
                tf = p.as_temp()
                print(tf.fileName())
                self._temp.append(tf)
                line = f"{prop}url({tf.fileName()});\n"

        except IndexError:
            # this is raised when there's no match
            print(f"Failed to parse {line}")
        except ValueError:
            # this is raised when there's unexpected output
            print(f"Failed to parse {line}")

        return line

    def parse_color(self, line, as_tuple=False):
        """ Parse a line with color. """
        key = next(k for k in self.palette.colors if k in line)
        pattern = f"(.*){key}#?(\d\d)?;?"
        prop, opacity = re.findall(pattern, line)[0]

        if opacity:
            opacity = round((int(opacity) / 100), 2)

        rgb = self.palette.get_color(key, opacity, as_tuple=as_tuple)

        if as_tuple:
            return rgb

        return f"{prop}{rgb};\n"

    def parse_css(self, source_css):
        """ Parse given css files. """
        css = ""

        for line in source_css:
            if "URL" in line:
                line = self.parse_url(line)

            elif any(map(lambda x: x in line, self.palette.colors)):
                line = self.parse_color(line)

            css += line
            print(line, end="")

        return css
