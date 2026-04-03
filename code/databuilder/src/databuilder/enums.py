"""
Enums for the tennis dataset.
"""

from __future__ import annotations

from enum import StrEnum


class Hand(StrEnum):
    """A tennis player's hand."""

    LEFT = "L"
    RIGHT = "R"
    AMBIDEXTROUS = "A"
