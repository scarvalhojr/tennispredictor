"""
Data model classes for the tennis dataset.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from logging import warning

from .enums import Hand, Surface, TournamentLevel


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
        start_date: date,
        level: TournamentLevel,
        *,
        name: str | None = None,
        surface: Surface | None = None,
        draw_size: int | None = None,
    ):
        tournament = self.tournaments.get(tournament_id)
        if tournament is None:
            tournament = Tournament(
                tournament_id,
                start_date,
                level,
                name=name,
                surface=surface,
                draw_size=draw_size,
            )
            self.tournaments[tournament_id] = tournament
        else:
            tournament.update_if_missing(
                start_date,
                level,
                name=name,
                surface=surface,
                draw_size=draw_size,
            )
        return tournament

    def get_tournament(self, tournament_id: str) -> Tournament | None:
        return self.tournaments.get(tournament_id)

    def count_tournaments(self) -> int:
        return len(self.tournaments)

    def get_ranked_players(
        self, ranking_date: date, max_lookback: int = 7
    ) -> list[tuple[Ranking, Player]]:
        ranked_players = []
        for player in self.players.values():
            rank = player.get_ranking(ranking_date, max_lookback)
            if rank is not None:
                ranked_players.append((rank, player))

        return ranked_players


class Player:
    """A tennis player."""

    def __init__(
        self,
        player_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        hand: Hand | None = None,
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
        return f"{self.full_name()} ({self.player_id})"

    def full_name(self) -> str:
        return " ".join((self.first_name or "", self.last_name or "")).strip()

    def age_at(self, a_date: date) -> float | None:
        if self.birth_date is None:
            return None
        return round((a_date - self.birth_date).days / 365.25, 2)

    def check_match_data(
        self,
        tournament: Tournament,
        *,
        name: str | None,
        hand: Hand | None,
        height: int | None,
        country: str | None,
        age: float | None,
        rank: int | None,
        rank_points: int | None,
    ):
        full_name = " ".join([self.first_name or "", self.last_name or ""]).strip()
        if name is not None and name != full_name:
            warning(f"Ignoring name mismatch for {self} ({full_name} -> {name})")

        if hand is not None and self.hand != hand:
            warning(f"Ignoring hand mismatch for {self} ({self.hand} -> {hand})")

        if height is not None and self.height_cm != height:
            warning(
                f"Ignoring height mismatch for {self} ({self.height_cm} -> {height})"
            )

        if country is not None and self.country_code != country:
            warning(
                f"Ignoring country mismatch for {self} ({self.country_code} "
                f"-> {country})"
            )

        age_at_tournament = self.age_at(tournament.start_date)
        if age_at_tournament is not None and age is not None:
            age_gap = age - age_at_tournament
            if abs(age_gap) > 0.2:
                warning(
                    f"Ignoring age mismatch for {self} at {tournament.level} match on "
                    f"{tournament.start_date} ({age_gap:.1f} years)"
                )

        ranking = self.get_ranking(tournament.start_date)
        rank_at_tournament = ranking.position if ranking else None
        points_at_tournament = ranking.points if ranking else None
        if not rank_at_tournament or not points_at_tournament:
            warning(
                f"Missing ranking data for {self} at {tournament.level} event on "
                f"{tournament.start_date} (position: {rank_at_tournament}, points: "
                f"{points_at_tournament}) vs match data (position: {rank}, points: "
                f"{rank_points})"
            )
        else:
            if rank is not None and rank_at_tournament != rank:
                warning(
                    f"Ignoring match ranking position mismatch for {self} at "
                    f"{tournament.level} event on {tournament.start_date} "
                    f"({rank_at_tournament}) vs match data ({rank})"
                )
            if rank_points is not None and points_at_tournament != rank_points:
                warning(
                    f"Ignoring match ranking points mismatch for {self} at "
                    f"{tournament.level} event on {tournament.start_date} "
                    f"({points_at_tournament}) vs match data ({rank_points})"
                )

    def add_ranking(self, ranking_date: date, position: int | None, points: int | None):
        ranking = self.ranking_history.get(ranking_date)
        if ranking is None:
            self.ranking_history[ranking_date] = Ranking(ranking_date, position, points)
        else:
            ranking.update_if_missing(position, points, self)

    def get_ranking(self, ranking_date: date, max_lookback: int = 15) -> Ranking | None:
        """Get the ranking for a given date, searching back up to 15 days by default."""

        for _ in range(max_lookback):
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
        start_date: date,
        level: TournamentLevel,
        *,
        name: str | None = None,
        surface: Surface | None = None,
        draw_size: int | None = None,
    ):
        self.tournament_id = tournament_id
        self.start_date = start_date
        self.level = level
        self.name = name
        self.surface = surface
        self.draw_size = draw_size
        self.matches: dict[int, Match] = {}

    def __str__(self) -> str:
        return f"{self.name} ({self.tournament_id})"

    def update_if_missing(
        self,
        start_date: date,
        level: TournamentLevel,
        *,
        name: str | None = None,
        surface: Surface | None = None,
        draw_size: int | None = None,
    ):
        if self.start_date != start_date:
            raise DataInconsistencyError(
                f"Tournament start date mismatch for {self} "
                f"({self.start_date} -> {start_date})"
            )

        if self.level != level:
            raise DataInconsistencyError(
                f"Tournament level mismatch for {self} ({self.level} -> {level})"
            )

        if self.name is None:
            self.name = name
        elif name is not None and self.name != name:
            raise DataInconsistencyError(
                f"Tournament name mismatch for {self} ({self.name} -> {name})"
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

    def add_match(
        self,
        match_num: int,
        player1_id: int,
        player2_id: int,
        winner: int,
        *,
        score: str,
        best_of: int,
    ):
        if match_num in self.matches:
            raise DataInconsistencyError(
                f"Match number {match_num} already exists for {self}"
            )
        self.matches[match_num] = Match(
            match_num,
            player1_id,
            player2_id,
            winner,
            score=score,
            best_of=best_of,
        )


class Match:
    """A tennis match."""

    def __init__(
        self,
        match_num: int,
        player1_id: int,
        player2_id: int,
        winner: int,
        *,
        score: str,
        best_of: int,
    ):
        self.match_num = match_num
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.winner = winner
        self.score = score
        self.best_of = best_of
        self.winner_sets = 0
        self.loser_sets = 0
        self.winner_games = 0
        self.loser_games = 0

        if best_of not in (3, 5):
            raise DataInconsistencyError(
                f"Invalid format (best of {best_of}) for match {match_num}"
            )

        try:
            for set_score in score.split(" "):
                tie_break = re.match(r"^\[(.*)\]$", set_score)
                if tie_break:
                    winner_pts, loser_pts = map(int, tie_break.group(1).split("-"))
                    assert winner_pts != loser_pts
                    if winner_pts > loser_pts:
                        self.winner_sets += 1
                    elif winner_pts < loser_pts:
                        self.loser_sets += 1
                    else:
                        raise DataInconsistencyError(
                            f"Invalid tie break score for match {match_num}: "
                            f"{set_score}"
                        )
                else:
                    winner_games, loser_games = map(
                        int, re.sub(r"\(\d+\)", "", set_score).split("-")
                    )
                    if winner_games > loser_games:
                        self.winner_sets += 1
                    elif winner_games < loser_games:
                        self.loser_sets += 1
                    else:
                        raise DataInconsistencyError(
                            f"Invalid set score for match {match_num}: {set_score}"
                        )
                    self.winner_games += winner_games
                    self.loser_games += loser_games
        except ValueError as exc:
            raise DataInconsistencyError(
                f"Invalid score format for match {match_num}: {score}"
            ) from exc

        set_diff = self.winner_sets - self.loser_sets
        if (
            set_diff < 1
            or (best_of == 3 and set_diff > 2)
            or (best_of == 5 and set_diff > 3)
        ):
            warning(
                f"Match {match_num} has an inconsistent set difference "
                f"({set_diff}) for a best of {best_of} match with score {score}"
            )

    def __str__(self) -> str:
        return f"{self.match_num} {self.player1_id} vs {self.player2_id}"

    def games_ratio(self) -> float:
        return self.winner_games / (self.winner_games + self.loser_games)
