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


class Surface(StrEnum):
    """A tennis court surface."""

    CLAY = "Clay"
    GRASS = "Grass"
    HARD = "Hard"
    CARPET = "Carpet"


class TournamentLevel(StrEnum):
    """A tennis tournament level."""

    ATP = "A"
    DAVIS_CUP = "D"
    FINALS = "F"
    GRAND_SLAM = "G"
    MASTERS_1000 = "M"
    OLYMPICS = "O"
