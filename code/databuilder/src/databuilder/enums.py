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
    NEXT_GEN_FINALS = "N"
    OLYMPICS = "O"

    def __str__(self) -> str:
        return {
            "A": "ATP",
            "D": "Davis Cup",
            "F": "ATP Finals",
            "G": "Grand Slam",
            "M": "Masters 1000",
            "N": "Next Gen Finals",
            "O": "Olympics",
        }[self.value]
