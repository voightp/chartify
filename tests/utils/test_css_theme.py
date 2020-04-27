import json
from pathlib import Path

import pytest

from chartify.utils.css_theme import parse_color, Palette, InvalidRangeError


def test_parse_color_tuple():
    color = (100, 100, 100)
    assert parse_color(color) == color


@pytest.mark.parametrize(
    "color,expected",
    [
        ("rgb(100,100,100)", (100, 100, 100)),
        ("rgb(100, 100, 100)", (100, 100, 100)),
        ("rgb( 100, 100 , 100 )", (100, 100, 100))
    ]
)
def test_parse_color_rgb_string(color, expected):
    assert parse_color(color) == expected


@pytest.mark.parametrize(
    "color,expected",
    [
        ("#646464", (100, 100, 100)),
        ("#656667", (101, 102, 103)),
        ("#000000", (0, 0, 0))
    ]
)
def test_parse_color_hex_string(color, expected):
    assert parse_color(color) == expected


@pytest.mark.parametrize(
    "color",
    [
        ("646464",),
        ("#6566671",),
        ((100, 100, 102, 0.2),),
        (True,),
        (0,),
        ("rgba(100,100,100,0.2)",),
    ]
)
def test_parse_color_invalid(color):
    with pytest.raises(TypeError):
        rgb = parse_color(color)
        assert rgb is None


class TestPalette:
    @pytest.fixture(scope="class")
    def palette(self):
        # reduce colors for test purposes
        Palette.COLORS = [
            "PRIMARY_COLOR",
            "PRIMARY_TEXT_COLOR",
            "SECONDARY_COLOR",
            "SECONDARY_TEXT_COLOR",
        ]
        return Palette(
            "test palette",
            default_color=(100, 100, 100),
            PRIMARY_COLOR=(255, 255, 255),
            PRIMARY_TEXT_COLOR=(0, 0, 0)
        )

    def test_palette_init(self, palette: Palette):
        assert palette.name == "test palette"
        assert palette.colors_dct == {
            "PRIMARY_COLOR": (255, 255, 255),
            "PRIMARY_TEXT_COLOR": (0, 0, 0),
            "SECONDARY_COLOR": (100, 100, 100),
            "SECONDARY_TEXT_COLOR": (100, 100, 100),
        }

    def test_parse_palette(self):
        p = Path("test.json")
        try:
            with open(p, "w") as f:
                json.dump(
                    {
                        "default": {
                            "PRIMARY_COLOR": "rgb(174,174,174)",
                            "PRIMARY_TEXT_COLOR": "rgb(112,112,112)",
                        },
                        "monochrome": {
                            "PRIMARY_COLOR": "rgb(174,174,174)",
                            "PRIMARY_TEXT_COLOR": "rgb(112,112,112)",
                        },
                        "dark": {
                            "PRIMARY_COLOR": "rgb(180,180,180)",
                            "PRIMARY_TEXT_COLOR": "rgb(180,180,180)",
                        }
                    },
                    f
                )
            palettes = Palette.parse_palettes(str(p), default_color=(100, 100, 100))

            assert list(palettes.keys()) == ["default", "monochrome", "dark"]
            assert palettes["default"].colors_dct == {
                "PRIMARY_COLOR": (174, 174, 174),
                "PRIMARY_TEXT_COLOR": (112, 112, 112),
                "SECONDARY_COLOR": (100, 100, 100),
                "SECONDARY_TEXT_COLOR": (100, 100, 100),
            }
            assert palettes["monochrome"].colors_dct == {
                "PRIMARY_COLOR": (174, 174, 174),
                "PRIMARY_TEXT_COLOR": (112, 112, 112),
                "SECONDARY_COLOR": (100, 100, 100),
                "SECONDARY_TEXT_COLOR": (100, 100, 100),
            }
            assert palettes["dark"].colors_dct == {
                "PRIMARY_COLOR": (180, 180, 180),
                "PRIMARY_TEXT_COLOR": (180, 180, 180),
                "SECONDARY_COLOR": (100, 100, 100),
                "SECONDARY_TEXT_COLOR": (100, 100, 100),
            }
        finally:
            p.unlink()

    def test_get_color(self, palette: Palette):
        assert palette.get_color("PRIMARY_COLOR") == "rgb(255,255,255)"

    def test_get_color_opacity(self, palette: Palette):
        assert palette.get_color("PRIMARY_COLOR", opacity=0.5) == "rgba(255,255,255,0.5)"

    def test_get_color_opacity_out_of_range(self, palette: Palette):
        with pytest.raises(InvalidRangeError):
            palette.get_color("PRIMARY_COLOR", opacity=1.1)

    def test_get_color_as_tuple(self, palette: Palette):
        assert palette.get_color("PRIMARY_COLOR", as_tuple=True) == (255, 255, 255)

    def test_get_color_opacity_as_tuple(self, palette: Palette):
        c = palette.get_color("PRIMARY_COLOR", opacity=0.5, as_tuple=True)
        assert c == (255, 255, 255, 0.5)

    def test_get_invalid_color(self, palette: Palette):
        with pytest.raises(KeyError):
            palette.get_color("FOO")

    def test_get_all_colors(self, palette: Palette):
        assert palette.get_all_colors() == {
            "PRIMARY_COLOR": "rgb(255,255,255)",
            "PRIMARY_TEXT_COLOR": "rgb(0,0,0)",
            "SECONDARY_COLOR": "rgb(100,100,100)",
            "SECONDARY_TEXT_COLOR": "rgb(100,100,100)",
        }

    def test_get_all_colors_as_tuple(self, palette: Palette):
        assert palette.get_all_colors(as_tuple=True) == {
            "PRIMARY_COLOR": (255, 255, 255),
            "PRIMARY_TEXT_COLOR": (0, 0, 0),
            "SECONDARY_COLOR": (100, 100, 100),
            "SECONDARY_TEXT_COLOR": (100, 100, 100),
        }


class TestCssTheme:
    def test_parse_line(self):
        assert False

    def test_parse_url(self):
        assert False

    def test_parse_css(self):
        assert False

    def test_populate_content(self):
        assert False
