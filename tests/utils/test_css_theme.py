import io
import json
from pathlib import Path

import pytest

from chartify.utils.css_theme import (
    parse_color,
    Palette,
    CssParser,
    InvalidRangeError,
    perc_to_float,
    string_rgb,
    InvalidUrlLine,
)
from tests.fixtures import ROOT


def test_parse_color_tuple():
    color = (100, 100, 100)
    assert parse_color(color) == color


def test_perc_to_float():
    assert perc_to_float(70) == 0.7
    assert perc_to_float("70") == 0.7


@pytest.mark.parametrize(
    "rgb,expected",
    [
        ((100, 100, 100), "rgb(100, 100, 100)"),
        ((100, 100, 100, 0.7), "rgba(100, 100, 100, 0.7)"),
    ],
)
def test_string_rgb(rgb, expected):
    assert string_rgb(rgb) == expected


@pytest.mark.parametrize(
    "color,expected",
    [
        ("rgb(100,100,100)", (100, 100, 100)),
        ("rgb(100, 100, 100)", (100, 100, 100)),
        ("rgb( 100, 100 , 100 )", (100, 100, 100)),
    ],
)
def test_parse_color_rgb_string(color, expected):
    assert parse_color(color) == expected


def test_parse_color_invalid_string():
    with pytest.raises(TypeError):
        parse_color("HEX123456")


@pytest.mark.parametrize(
    "color,expected",
    [("#646464", (100, 100, 100)), ("#656667", (101, 102, 103)), ("#000000", (0, 0, 0))],
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
    ],
)
def test_parse_color_invalid(color):
    with pytest.raises(TypeError):
        rgb = parse_color(color)
        assert rgb is None


@pytest.fixture(scope="module")
def palette():
    # reduce colors for test purposes
    old_colors = Palette.COLORS
    Palette.COLORS = [
        "PRIMARY_COLOR",
        "PRIMARY_TEXT_COLOR",
        "SECONDARY_COLOR",
        "SECONDARY_TEXT_COLOR",
    ]
    yield Palette(
        "test palette",
        default_color=(100, 100, 100),
        PRIMARY_COLOR=(255, 255, 255),
        PRIMARY_TEXT_COLOR=(0, 0, 0),
    )
    Palette.COLORS = old_colors


class TestPalette:
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
                        },
                    },
                    f,
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
        assert palette.get_color("PRIMARY_COLOR") == "rgb(255, 255, 255)"

    def test_get_color_opacity(self, palette: Palette):
        assert palette.get_color("PRIMARY_COLOR", opacity=0.5) == "rgba(255, 255, 255, 0.5)"

    def test_get_color_opacity_out_of_range(self, palette: Palette):
        with pytest.raises(InvalidRangeError):
            palette.get_color("PRIMARY_COLOR", opacity=1.1)

    def test_get_color_as_tuple(self, palette: Palette):
        assert palette.get_color_tuple("PRIMARY_COLOR") == (255, 255, 255)

    def test_get_color_opacity_as_tuple(self, palette: Palette):
        c = palette.get_color_tuple("PRIMARY_COLOR", opacity=0.5)
        assert c == (255, 255, 255, 0.5)

    def test_get_invalid_color(self, palette: Palette):
        with pytest.raises(KeyError):
            palette.get_color("FOO")

    def test_get_all_colors(self, palette: Palette):
        assert palette.get_all_colors() == {
            "PRIMARY_COLOR": "rgb(255, 255, 255)",
            "PRIMARY_TEXT_COLOR": "rgb(0, 0, 0)",
            "SECONDARY_COLOR": "rgb(100, 100, 100)",
            "SECONDARY_TEXT_COLOR": "rgb(100, 100, 100)",
        }

    def test_get_all_colors_as_tuple(self, palette: Palette):
        assert palette.get_all_color_tuples() == {
            "PRIMARY_COLOR": (255, 255, 255),
            "PRIMARY_TEXT_COLOR": (0, 0, 0),
            "SECONDARY_COLOR": (100, 100, 100),
            "SECONDARY_TEXT_COLOR": (100, 100, 100),
        }


class TestCssTheme:
    @pytest.fixture(scope="class")
    def css(self):
        # reduce colors for test purposes
        return CssParser()

    @pytest.mark.parametrize(
        "line,color_key,rgb,expected",
        [
            (
                "  border: 1px solid PRIMARY_COLOR;",
                "PRIMARY_COLOR",
                (255, 255, 255),
                "  border: 1px solid rgb(255, 255, 255);\n",
            ),
            (
                "  color: SECONDARY_COLOR #70;",
                "SECONDARY_COLOR",
                (100, 100, 100),
                "  color: rgba(100, 100, 100, 0.7);\n",
            ),
        ],
    )
    def test_parse_line(self, line: str, color_key: str, rgb: tuple, expected: str):
        css = CssParser()
        assert css.parse_line(line, color_key, rgb) == expected

    @pytest.mark.parametrize(
        "line,color_key,rgb",
        [
            (
                "  image: URL(./resources/icons/test.png) #PRIMARY_COLOR;",
                "PRIMARY_COLOR",
                (255, 255, 255),
            ),
            (
                "  image: URL(./resources/icons/test.png) #PRIMARY_COLOR#70;",
                "PRIMARY_COLOR",
                (255, 255, 255),
            ),
        ],
    )
    def test_parse_url(self, line: str, color_key: str, rgb: tuple, qtbot, tmpdir):
        css = CssParser()
        line, dest_path = css.parse_url_line(line, color_key, rgb, ROOT, tmpdir)
        assert line == f"  image: url({dest_path});\n"

    def test_parse_url_index_error(self):
        line = "URL #WRONGCOLOR"
        with pytest.raises(InvalidUrlLine):
            _ = CssParser.parse_url(line, "PRIMARY_COLOR")

    def test_parse_url_invalid_path(self, tmpdir):
        line = "image: URL(./invalid/test.png) #PRIMARY_COLOR#70;"
        with pytest.raises(FileNotFoundError):
            _ = CssParser.parse_url_line(line, "PRIMARY_COLOR", (10, 10, 10), ROOT, tmpdir)

    def test_parse_css(self, palette: Palette, qtbot, tmpdir):
        s = """
TitledButton {
    font-size: 13px;
    image: url(./resources/icons/test.png);
}

TitledButton::menu-indicator {
    image: URL(./resources/icons/test.png) #PRIMARY_COLOR;
    margin: 1px;
}

TitledButton:checked {
    background-color: transparent;
    border-color: PRIMARY_COLOR;
    color: PRIMARY_TEXT_COLOR;
}"""
        sio = io.StringIO(s)
        parsed, temp_icons = CssParser.parse_css(sio.readlines(), palette, ROOT, tmpdir)
        assert (
            parsed
            == f"""
TitledButton {{
    font-size: 13px;
    image: url(./resources/icons/test.png);
}}

TitledButton::menu-indicator {{
    image: url({temp_icons[0]});
    margin: 1px;
}}

TitledButton:checked {{
    background-color: transparent;
    border-color: rgb(255, 255, 255);
    color: rgb(0, 0, 0);
}}"""
        )
