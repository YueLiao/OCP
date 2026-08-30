"""Unit tests for the pure helpers in visualisations/visualisations.py: adjust_lightness
and find_function_index_from_x_coord. generate_figure is a matplotlib figure builder,
exercised only as a smoke test in the gated test/implementations/ suite, not here.
"""
import pytest

from visualisations.visualisations import adjust_lightness, find_function_index_from_x_coord


def test_adjust_lightness_scales_lightness_and_clamps():
    assert adjust_lightness("red", 1.0) == pytest.approx((1.0, 0.0, 0.0))  # amount 1 -> unchanged
    assert adjust_lightness("red", 0.0) == pytest.approx((0.0, 0.0, 0.0))  # lightness -> 0 -> black
    assert adjust_lightness("red", 2.0) == pytest.approx((1.0, 1.0, 1.0))  # lightness clamped to 1 -> white


def test_adjust_lightness_accepts_a_non_name_color():
    # an unknown color name falls through to matplotlib.to_rgb, so an RGB tuple works too
    assert adjust_lightness((0.0, 0.0, 1.0), 1.0) == pytest.approx((0.0, 0.0, 1.0))


@pytest.mark.parametrize("x,expected", [(5, 0), (15, 1), (25, 2), (10, 0)])
def test_find_function_index_returns_first_limit_not_exceeded(x, expected):
    # first index whose limit is >= x; a coordinate exactly on a limit stays at that index
    # (NB: x beyond every limit currently IndexErrors - a known unhardened edge, left as-is)
    assert find_function_index_from_x_coord(x, [10, 20, 30]) == expected
