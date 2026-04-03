"""
Data model classes for the tennis dataset.
"""

from __future__ import annotations

from datetime import date
from logging import warning


class DataInconsistencyError(Exception):
    """Raised when data inconsistency is found."""

    def __init__(self, msg):
        super().__init__(f"Data inconsistency found: {msg}")


class TennisDataset:
    """A tennis dataset."""

    def __init__(self):
        self.players: dict[int, Player] = {}

    def add_player(self, player: Player):
        if player.player_id in self.players:
            raise DataInconsistencyError(
                f"Player with ID {player.player_id} already exists"
            )
        self.players[player.player_id] = player

    def count_players(self) -> int:
        return len(self.players)

    def get_player(self, player_id: int) -> Player | None:
        return self.players.get(player_id)


# pylint: disable=too-many-instance-attributes
class Player:
    """A tennis player."""

    def __init__(
        self,
        player_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        hand: str | None = None,
        birth_date: date | None = None,
        country_code: str | None = None,
        height_cm: int | None,
    ):
        self.player_id = player_id
        self.first_name = first_name
        self.last_name = last_name
        self.hand = hand
        self.birth_date = birth_date
        self.country_code = country_code
        self.height_cm = height_cm
        self.ranking_history: dict[date, Ranking] = {}

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.player_id})"

    def add_ranking(self, ranking_date: date, position: int | None, points: int | None):
        ranking = self.ranking_history.get(ranking_date)
        if ranking is None:
            self.ranking_history[ranking_date] = Ranking(ranking_date, position, points)
        else:
            ranking.update_if_missing(position, points, self)


class Ranking:
    """A tennis ranking."""

    def __init__(self, ranking_date: date, position: int | None, points: int | None):
        self.ranking_date = ranking_date
        self.position = position
        self.points = points

    def __str__(self) -> str:
        return f"{self.position} - {self.points}"

    def update_if_missing(
        self, position: int | None, points: int | None, player: Player
    ):
        if self.position is None:
            self.position = position
        elif position is not None and self.position != position:
            warning(
                f"Ignoring ranking position mismatch for {player} "
                f"on {self.ranking_date} ({self.position} -> {position})"
            )

        if self.points is None:
            self.points = points
        elif points is not None and self.points != points:
            warning(
                f"Ignoring ranking points mismatch for {player} "
                f"on {self.ranking_date} ({self.points} -> {points})"
            )
