class Palette:

    def __init__(self, primary_color=None, primary_variant_color=None,
                 primary_text_color=None, primary_disabled_color=None,
                 secondary_color=None, secondary_variant_color=None,
                 secondary_text_color=None, secondary_disabled_color=None,
                 background_color=None, surface_color=None, error_color=None,
                 ok_color=None):
        self.colors_dct = {
            "PRIMARY_COLOR": primary_color,
            "PRIMARY_VARIANT_COLOR": primary_variant_color,
            "PRIMARY_TEXT_COLOR": primary_text_color,
            "PRIMARY_DISABLED_COLOR": primary_disabled_color,
            "SECONDARY_COLOR": secondary_color,
            "SECONDARY_VARIANT_COLOR": secondary_variant_color,
            "SECONDARY_TEXT_COLOR": secondary_text_color,
            "SECONDARY_DISABLED_COLOR": secondary_disabled_color,
            "BACKGROUND_COLOR": background_color,
            "SURFACE_COLOR": surface_color,
            "ERROR_COLOR": error_color,
            "OK_COLOR": ok_color,
        }

    @property
    def color_keys(self):
        """ Get all color keys. """
        return list(self.colors_dct.keys())

    def get_color(self, color_key):
        """ Get specified color. """
        try:
            return self.colors_dct[color_key]
        except KeyError:
            colors_str = ", ".join(self.color_keys)
            print(f"Cannot get color for color key '{color_key}' is it's not "
                  f"available, use one of: '{colors_str}'.")

    def set_color(self, color_key, color):
        """ Set specified color. """
        try:
            self.colors_dct[color_key] = color
        except KeyError:
            colors_str = ", ".join(self.color_keys)
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

    def parse_css(self, source_css):
        """ Parse given css files. """
        keys = self.palette.color_keys
        css = ""

        for line in source_css:
            try:
                key = next(k for k in keys if k in line)
                color = self.palette.get_color(key)
                line = line.replace(key, color)
            except StopIteration:
                pass
            finally:
                css += line

        return css


p = Palette()
th = CssTheme(p)

c = th.process_csss("../styles/app_style.css")
print(c)
