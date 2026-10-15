"""Shared, versioned pedestrian category conventions; never round input counts."""

import math

import numpy as np

CATEGORY_RULE = "positive_upper_bound_v1"
UPPER_BOUNDS = (5, 25, 50, 100, 200, 300, 400, 500, 900)
RECOUNT = {1: 0, 2: 3, 3: 15, 4: 38, 5: 75, 6: 150, 7: 250, 8: 350, 9: 450}
WORD_CODES = {
    "None": 1, "1 pedestrian": 2, "2 to 3 pedestrians": 3,
    "4 to 5 pedestrians": 4, "6 to 7 pedestrians": 5, "8+ pedestrians": 6,
}
# Reference manual's printed integer endpoints. None is an unbounded upper end.
BANDS = {
    1: (0, 0), 2: (1, 5), 3: (6, 25), 4: (26, 50), 5: (51, 100),
    6: (101, 200), 7: (201, 300), 8: (301, 400), 9: (401, 500),
    10: (501, 900), 11: (900, None),
}


def flow_category(value):
    """Project continuous extension of the reference bands, not an official algorithm."""
    if isinstance(value, (bool, np.bool_)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    if number == 0:
        return 1
    return int(np.searchsorted(UPPER_BOUNDS, number, side="left")) + 2


def format_band(bounds):
    """Display derived endpoints, distinguishing missing and open-ended intervals."""
    if bounds is None:
        return None
    lower, upper = bounds
    def display(value):
        return f"{value:.2f}".rstrip("0").rstrip(".")

    if upper is None:
        return f"{display(lower)}+"
    return display(lower) if lower == upper else f"{display(lower)}–{display(upper)}"
