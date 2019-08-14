import re
from collections import namedtuple
from esopie.icons import Pixmap

Color = namedtuple("Color", "r, g, b")


class Palette:
    """
    A class to define color set used for an application.

    Colors can be defined either using HEX or rgb string
    and rgb tuples.

    When an available kwarg is not populated, default color
    is used.

    Examples
    --------



    Arguments
    ---------
    default_color : tuple
        A default color which will be used when available
        kwarg is not specified.

    **kwargs
        primary_color, primary_variant_color, primary_text_color,
        primary_disabled_color, secondary_color, secondary_variant_color,
        secondary_text_color, secondary_disabled_color, background_color,
        surface_color, error_color, ok_color


    """
    colors = [
        "PRIMARY_COLOR",
        "PRIMARY_VARIANT_COLOR",
        "PRIMARY_TEXT_COLOR",
        "PRIMARY_DISABLED_COLOR",
        "SECONDARY_COLOR",
        "SECONDARY_VARIANT_COLOR",
        "SECONDARY_TEXT_COLOR",
        "SECONDARY_DISABLED_COLOR",
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

    def get_color(self, color_key, line=None, as_tuple=False):
        """ Get specified color as string. """
        try:
            rgb = self.colors_dct[color_key]

            if line:
                # check for opacity
                p = f"{color_key}#(\d\d)?"
                gr = re.findall(p, line)
                if gr:
                    # add opacity to rgb request
                    a = round((int(gr[0]) / 100), 2)
                    rgb = (*rgb, a)

            srgb = ",".join([str(i) for i in rgb])

            if as_tuple:
                return rgb

            return f"rgb({srgb})" if len(rgb) == 3 else f"rgba({srgb})"

        except KeyError:
            colors_str = ", ".join(self.colors)
            print(f"Cannot get color for color key '{color_key}' is it's not "
                  f"available, use one of: '{colors_str}'.")

    def set_color(self, color_key, color):
        """ Set specified color. """
        try:
            self.colors_dct[color_key] = color
        except KeyError:
            colors_str = ", ".join(self.colors)
            print(f"Cannot set color '{color}' color key '{color_key}' is not "
                  f"available, use one of: '{colors_str}'.")


class CssTheme:
    def __init__(self, palette):
        self.palette = palette

    def process_csss(self, *args):
        """ Process multiple css files. """
        all_css = ""
        for file in args:
            with open(file) as f:
                css = self.parse_css(f)
                all_css += css

        return all_css

    def parse_url(self, line):
        """ Parse a line with an url. """
        pattern = "(.*)URL\((.*?)\)#(.*);"
        try:
            prop, url, col = re.findall(pattern, line)[0]
            try:
                key = next(k for k in self.palette.colors if k in line)
                rgb = self.palette.get_color(key, line, as_tuple=True)
                # TODO handle pixmap
            except StopIteration:
                print(f"Failed to parse {line}")

            return f"prop({url});"
        except IndexError:
            # this is raised when there's no match
            print(f"Failed to parse {line}")
        except ValueError:
            # this is raised when there's unexpected output
            print(f"Failed to parse {line}")

        return line

    def parse_color(self, line):
        """ Parse a line with color. """
        key = next(k for k in self.palette.colors if k in line)
        color = self.palette.get_color(key, line)
        return line.replace(key, color)

    def parse_css(self, source_css):
        """ Parse given css files. """
        css = ""

        for line in source_css:
            if "URL" in line:
                line = self.parse_url(line)

            elif any(map(lambda x: x in line, self.palette.colors)):
                line = self.parse_color(line)

            css += line

        return css


default = {
    "PRIMARY_COLOR": "rgb(200,200,211)",
    "PRIMARY_VARIANT_COLOR": None,
    "PRIMARY_TEXT_COLOR": "rgb(112, 112, 112)",
    "PRIMARY_DISABLED_COLOR": (180, 180, 180),
    "SECONDARY_COLOR": None,
    "SECONDARY_VARIANT_COLOR": None,
    "SECONDARY_TEXT_COLOR": None,
    "SECONDARY_DISABLED_COLOR": None,
    "BACKGROUND_COLOR": "#eceff1",
    "SURFACE_COLOR": "",
    "ERROR_COLOR": "#e53935",
    "OK_COLOR": "#69f0ae",
}

p = Palette(**default)
th = CssTheme(p)

c = th.process_csss("../styles/app_style.css")
print(c)
