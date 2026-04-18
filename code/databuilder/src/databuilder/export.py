"""
Export dataset structures to flat files.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from logging import info
from pathlib import Path
from typing import Any

from .data import DataInconsistencyError, Match, Player, TennisDataset, Tournament
from .enums import Surface, TournamentLevel
from .process import iter_matches


class Stats:
    """
    Statistics about the dataset.
    """

    INITIAL_ELO_RATING = 1500

    def __init__(self):
        self.total_matches = 0
        self.highest_rank: dict[int, int] = {}
        self.total_wins: defaultdict[int, int] = defaultdict(lambda: 0)
        self.total_losses: defaultdict[int, int] = defaultdict(lambda: 0)
        self.total_surface_wins: defaultdict[tuple[int, Surface], int] = defaultdict(
            lambda: 0
        )
        self.total_surface_losses: defaultdict[tuple[int, Surface], int] = defaultdict(
            lambda: 0
        )
        self.head2head_wins: defaultdict[tuple[int, int], int] = defaultdict(lambda: 0)
        self.head2head_surface_wins: defaultdict[tuple[int, int, Surface], int] = (
            defaultdict(lambda: 0)
        )
        self.elo_rating: defaultdict[int, float] = defaultdict(
            lambda: self.INITIAL_ELO_RATING
        )
        self.surface_elo_rating: defaultdict[tuple[int, Surface], float] = defaultdict(
            lambda: self.INITIAL_ELO_RATING
        )

    def add_match(self, tournament: Tournament, match: Match):
        self.total_matches += 1

        if match.winner == 1:
            winner_id = match.player1_id
            loser_id = match.player2_id
        elif match.winner == 2:
            winner_id = match.player2_id
            loser_id = match.player1_id
        else:
            raise DataInconsistencyError(
                f"Invalid winner '{match.winner}' for match {match} at {tournament}"
            )

        self.total_wins[winner_id] += 1
        self.total_losses[loser_id] += 1
        self.head2head_wins[(winner_id, loser_id)] += 1
        self._update_elo(match.player1_id, match.player2_id, match.winner)

        if tournament.surface is not None:
            self.total_surface_wins[(winner_id, tournament.surface)] += 1
            self.total_surface_losses[(loser_id, tournament.surface)] += 1
            self.head2head_surface_wins[(winner_id, loser_id, tournament.surface)] += 1
            self._update_surface_elo(
                match.player1_id, match.player2_id, tournament.surface, match.winner
            )

    def _update_elo(self, player1_id: int, player2_id: int, winner: int):
        p1_elo = self.elo_rating[player1_id]
        p2_elo = self.elo_rating[player2_id]
        p1_matches = self.get_total_matches(player1_id)
        p2_matches = self.get_total_matches(player2_id)
        p1_win, p2_win = (1, 0) if winner == 1 else (0, 1)

        self.elo_rating[player1_id] = self._new_elo(p1_elo, p2_elo, p1_matches, p1_win)
        self.elo_rating[player2_id] = self._new_elo(p2_elo, p1_elo, p2_matches, p2_win)

    def _update_surface_elo(
        self, player1_id: int, player2_id: int, surface: Surface, winner: int
    ):
        p1_elo = self.surface_elo_rating[(player1_id, surface)]
        p2_elo = self.surface_elo_rating[(player2_id, surface)]
        p1_matches = self.get_total_surface_matches(player1_id, surface)
        p2_matches = self.get_total_surface_matches(player2_id, surface)
        p1_win, p2_win = (1, 0) if winner == 1 else (0, 1)

        self.surface_elo_rating[(player1_id, surface)] = self._new_elo(
            p1_elo, p2_elo, p1_matches, p1_win
        )
        self.surface_elo_rating[(player2_id, surface)] = self._new_elo(
            p2_elo, p1_elo, p2_matches, p2_win
        )

    def _new_elo(
        self,
        player_elo: float,
        opponent_elo: float,
        num_matches: int,
        winner_indicator: float,
    ) -> float:
        expected = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))

        # The increment is based on the number of matches the player has played,
        # according to a formula suggested by Kovalchik in a paper from 2016
        increment = 250 / (num_matches + 5) ** 0.4

        return player_elo + increment * (winner_indicator - expected)

    def update_highest_rank(self, player_id: int, rank: int | None):
        if rank is None:
            return
        if player_id not in self.highest_rank or self.highest_rank[player_id] > rank:
            self.highest_rank[player_id] = rank

    def get_highest_rank(self, player_id: int) -> int | None:
        return self.highest_rank.get(player_id)

    def get_total_matches(self, player_id: int) -> int:
        return self.total_wins[player_id] + self.total_losses[player_id]

    def get_total_surface_matches(self, player_id: int, surface: Surface) -> int:
        return (
            self.total_surface_wins[(player_id, surface)]
            + self.total_surface_losses[(player_id, surface)]
        )

    def get_win_rate(self, player_id: int) -> float | None:
        total_matches = self.get_total_matches(player_id)
        if total_matches == 0:
            return None
        return self.total_wins[player_id] / total_matches

    def get_surface_win_rate(self, player_id: int, surface: Surface) -> float | None:
        total_matches = self.get_total_surface_matches(player_id, surface)
        if total_matches == 0:
            return None
        return self.total_surface_wins[(player_id, surface)] / total_matches

    def get_head2head_wins(self, player1_id: int, player2_id: int) -> int:
        return self.head2head_wins[(player1_id, player2_id)]

    def get_head2head_surface_wins(
        self, player1_id: int, player2_id: int, surface: Surface | None
    ) -> int | None:
        if surface is None:
            return None
        return self.head2head_surface_wins[(player1_id, player2_id, surface)]

    def get_elo_rating(self, player_id: int) -> float | None:
        return self.elo_rating[player_id]

    def get_surface_elo_rating(self, player_id: int, surface: Surface) -> float | None:
        return self.surface_elo_rating[(player_id, surface)]


def export_matches(dataset: TennisDataset, path: Path) -> None:
    """
    Write every match in ``dataset`` to a single CSV at ``path``.

    Rows are ordered by tournament start date, then tournament id (for stable
    ordering when dates coincide), then match number.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = (
        "year",
        "tournament_id",
        "tournament_start_date",
        "tournament_name",
        "tournament_level",
        "surface",
        "draw_size",
        "match_num",
        "best_of",
        "player1_id",
        "player1_name",
        "player1_hand",
        "player1_height_cm",
        "player1_age",
        "player1_rank",
        "player1_points",
        "player1_highest_rank",
        "player1_total_matches",
        "player1_win_rate",
        "player1_surface_matches",
        "player1_surface_win_rate",
        "player1_head2head_wins",
        "player1_head2head_surface_wins",
        "player1_elo",
        "player1_surface_elo",
        "player2_id",
        "player2_name",
        "player2_hand",
        "player2_height_cm",
        "player2_age",
        "player2_rank",
        "player2_points",
        "player2_highest_rank",
        "player2_total_matches",
        "player2_win_rate",
        "player2_surface_matches",
        "player2_surface_win_rate",
        "player2_head2head_wins",
        "player2_head2head_surface_wins",
        "player2_elo",
        "player2_surface_elo",
        "winner",
    )

    # Ignore NextGen Finals as they use a different format
    levels = {
        TournamentLevel.ATP,
        TournamentLevel.DAVIS_CUP,
        TournamentLevel.FINALS,
        TournamentLevel.GRAND_SLAM,
        TournamentLevel.MASTERS_1000,
        TournamentLevel.OLYMPICS,
    }

    stats = Stats()

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tournament, match in iter_matches(dataset, tournament_levels=levels):
            writer.writerow(_match_row(dataset, tournament, match, stats))

    info(f"Exported {stats.total_matches} matches to {path}")


def _to_string(value: Any | None) -> str:
    return str(value) if value is not None else ""


def _format_date(a_date: date | None) -> str:
    return a_date.strftime("%Y-%m-%d") if a_date else ""


def _get_ranking(player: Player, match_date: date) -> tuple[int | None, int | None]:
    ranking = player.get_ranking(match_date)
    if ranking is not None:
        return ranking.position, ranking.points
    return None, None


def _match_row(
    dataset: TennisDataset, tournament: Tournament, match: Match, stats: Stats
) -> dict[str, str | int | float | None]:
    player1 = dataset.get_player(match.player1_id)
    player2 = dataset.get_player(match.player2_id)
    if player1 is None or player2 is None:
        raise DataInconsistencyError(
            f"Player data not found for match {match} at {tournament}"
        )

    player1_rank, player1_points = _get_ranking(player1, tournament.start_date)
    player2_rank, player2_points = _get_ranking(player2, tournament.start_date)

    # Update highest rank before outputting the values for the current match
    stats.update_highest_rank(match.player1_id, player1_rank)
    stats.update_highest_rank(match.player2_id, player2_rank)

    player1_head2head_wins = stats.get_head2head_wins(
        match.player1_id, match.player2_id
    )
    player2_head2head_wins = stats.get_head2head_wins(
        match.player2_id, match.player1_id
    )

    player1_head2head_surface_wins = stats.get_head2head_surface_wins(
        match.player1_id, match.player2_id, tournament.surface
    )
    player2_head2head_surface_wins = stats.get_head2head_surface_wins(
        match.player2_id, match.player1_id, tournament.surface
    )

    row = {
        "year": tournament.start_date.year,
        "tournament_id": tournament.tournament_id,
        "tournament_start_date": _format_date(tournament.start_date),
        "tournament_name": tournament.name,
        "tournament_level": tournament.level.value,
        "surface": tournament.surface,
        "draw_size": tournament.draw_size,
        "match_num": match.match_num,
        "best_of": match.best_of,
        "player1_id": match.player1_id,
        "player1_name": player1.full_name(),
        "player1_hand": _to_string(player1.hand),
        "player1_height_cm": player1.height_cm,
        "player1_age": player1.age_at(tournament.start_date),
        "player1_rank": player1_rank,
        "player1_points": player1_points,
        "player1_highest_rank": stats.get_highest_rank(match.player1_id),
        "player1_total_matches": stats.get_total_matches(match.player1_id),
        "player1_win_rate": stats.get_win_rate(match.player1_id),
        "player1_surface_matches": stats.get_total_surface_matches(
            match.player1_id, tournament.surface
        ),
        "player1_surface_win_rate": stats.get_surface_win_rate(
            match.player1_id, tournament.surface
        ),
        "player1_head2head_wins": player1_head2head_wins,
        "player1_head2head_surface_wins": player1_head2head_surface_wins,
        "player1_elo": stats.get_elo_rating(match.player1_id),
        "player1_surface_elo": stats.get_surface_elo_rating(
            match.player1_id, tournament.surface
        ),
        "player2_id": match.player2_id,
        "player2_name": player2.full_name(),
        "player2_hand": _to_string(player2.hand),
        "player2_height_cm": player2.height_cm,
        "player2_age": player2.age_at(tournament.start_date),
        "player2_rank": player2_rank,
        "player2_points": player2_points,
        "player2_highest_rank": stats.get_highest_rank(match.player2_id),
        "player2_total_matches": stats.get_total_matches(match.player2_id),
        "player2_win_rate": stats.get_win_rate(match.player2_id),
        "player2_surface_matches": stats.get_total_surface_matches(
            match.player2_id, tournament.surface
        ),
        "player2_surface_win_rate": stats.get_surface_win_rate(
            match.player2_id, tournament.surface
        ),
        "player2_head2head_wins": player2_head2head_wins,
        "player2_head2head_surface_wins": player2_head2head_surface_wins,
        "player2_elo": stats.get_elo_rating(match.player2_id),
        "player2_surface_elo": stats.get_surface_elo_rating(
            match.player2_id, tournament.surface
        ),
        "winner": match.winner,
    }

    # Update stats after getting the values for the current match
    stats.add_match(tournament, match)

    return row
