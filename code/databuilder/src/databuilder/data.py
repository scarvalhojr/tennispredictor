"""
Data model classes for the tennis dataset.
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import warning

from .enums import Surface, TournamentLevel


class DataInconsistencyError(Exception):
    """Raised when data inconsistency is found."""

    def __init__(self, msg):
        super().__init__(f"Data inconsistency found: {msg}")


class TennisDataset:
    """A tennis dataset."""

    def __init__(self):
        self.players: dict[int, Player] = {}
        self.tournaments: dict[str, Tournament] = {}

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

    def add_tournament(
        self,
        tournament_id: str,
        *,
        tournament_name: str | None = None,
        surface: Surface | None = None,
        draw_size: int | None = None,
        tournament_level: TournamentLevel | None = None,
        tournament_date: date | None = None,
    ):
        tournament = self.tournaments.get(tournament_id)
        if tournament is None:
            tournament = Tournament(
                tournament_id,
                tournament_name=tournament_name,
                surface=surface,
                draw_size=draw_size,
                tournament_level=tournament_level,
                tournament_date=tournament_date,
            )
            self.tournaments[tournament_id] = tournament
        else:
            tournament.update_if_missing(
                tournament_name=tournament_name,
                surface=surface,
                draw_size=draw_size,
                tournament_level=tournament_level,
                tournament_date=tournament_date,
            )
        return tournament

    def get_tournament(self, tournament_id: str) -> Tournament | None:
        return self.tournaments.get(tournament_id)

    def count_tournaments(self) -> int:
        return len(self.tournaments)


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

    def get_ranking(self, ranking_date: date) -> Ranking | None:
        """Get the ranking for a given date, searching back up to 15 days."""

        for _ in range(15):
            ranking = self.ranking_history.get(ranking_date)
            if ranking is not None:
                return ranking
            ranking_date = ranking_date - timedelta(days=1)
        return None


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


class Tournament:
    """A tennis tournament."""

    def __init__(
        self,
        tournament_id: str,
        *,
        tournament_name: str | None = None,
        surface: Surface | None = None,
        draw_size: int | None = None,
        tournament_level: TournamentLevel | None = None,
        tournament_date: date | None = None,
    ):
        self.tournament_id = tournament_id
        self.tournament_name = tournament_name
        self.surface = surface
        self.draw_size = draw_size
        self.tournament_level = tournament_level
        self.tournament_date = tournament_date

    def __str__(self) -> str:
        return f"{self.tournament_name} ({self.tournament_id})"

    def update_if_missing(
        self,
        *,
        tournament_name: str | None = None,
        surface: Surface | None = None,
        draw_size: int | None = None,
        tournament_level: TournamentLevel | None = None,
        tournament_date: date | None = None,
    ):
        if self.tournament_name is None:
            self.tournament_name = tournament_name
        elif tournament_name is not None and self.tournament_name != tournament_name:
            raise DataInconsistencyError(
                f"Tournament name mismatch for {self} "
                f"({self.tournament_name} -> {tournament_name})"
            )

        if self.surface is None:
            self.surface = surface
        elif surface is not None and self.surface != surface:
            raise DataInconsistencyError(
                f"Surface mismatch for {self} ({self.surface} -> {surface})"
            )

        if self.draw_size is None:
            self.draw_size = draw_size
        elif draw_size is not None and self.draw_size != draw_size:
            raise DataInconsistencyError(
                f"Draw size mismatch for {self} ({self.draw_size} -> {draw_size})"
            )

        if self.tournament_level is None:
            self.tournament_level = tournament_level
        elif tournament_level is not None and self.tournament_level != tournament_level:
            raise DataInconsistencyError(
                f"Tournament level mismatch for {self} "
                f"({self.tournament_level} -> {tournament_level})"
            )

        if self.tournament_date is None:
            self.tournament_date = tournament_date
        elif tournament_date is not None and self.tournament_date != tournament_date:
            raise DataInconsistencyError(
                f"Tournament date mismatch for {self} "
                f"({self.tournament_date} -> {tournament_date})"
            )
