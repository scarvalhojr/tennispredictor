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
from .glicko2 import GlickoRatings
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
        self.elo: defaultdict[int, float] = defaultdict(lambda: self.INITIAL_ELO_RATING)
        self.welo: defaultdict[int, float] = defaultdict(
            lambda: self.INITIAL_ELO_RATING
        )
        self.surface_elo: defaultdict[tuple[int, Surface], float] = defaultdict(
            lambda: self.INITIAL_ELO_RATING
        )
        self.surface_welo: defaultdict[tuple[int, Surface], float] = defaultdict(
            lambda: self.INITIAL_ELO_RATING
        )
        self.glicko: GlickoRatings = GlickoRatings()
        self.wglicko: GlickoRatings = GlickoRatings()
        self.surface_glicko: defaultdict[Surface, GlickoRatings] = defaultdict(
            GlickoRatings
        )
        self.surface_wglicko: defaultdict[Surface, GlickoRatings] = defaultdict(
            GlickoRatings
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

        games_ratio = match.games_ratio()

        self.total_wins[winner_id] += 1
        self.total_losses[loser_id] += 1
        self.head2head_wins[(winner_id, loser_id)] += 1
        self._update_elos(match)
        self.glicko.add_result(winner_id, loser_id)
        self.wglicko.add_result(winner_id, loser_id, games_ratio)

        if tournament.surface is not None:
            self.total_surface_wins[(winner_id, tournament.surface)] += 1
            self.total_surface_losses[(loser_id, tournament.surface)] += 1
            self.head2head_surface_wins[(winner_id, loser_id, tournament.surface)] += 1
            self._update_surface_elos(match, tournament.surface)
            self.surface_glicko[tournament.surface].add_result(winner_id, loser_id)
            self.surface_wglicko[tournament.surface].add_result(
                winner_id, loser_id, games_ratio
            )

    def _update_elos(self, match: Match):
        p1_id = match.player1_id
        p2_id = match.player2_id

        p1_win, p2_win = self._winner_indicators(match)
        games_ratio = match.games_ratio()

        p1_matches = self.get_total_matches(p1_id)
        p2_matches = self.get_total_matches(p2_id)

        p1_elo = self.elo[p1_id]
        p2_elo = self.elo[p2_id]
        self.elo[p1_id] = self._new_elo(p1_elo, p2_elo, p1_matches, p1_win)
        self.elo[p2_id] = self._new_elo(p2_elo, p1_elo, p2_matches, p2_win)

        p1_welo = self.welo[p1_id]
        p2_welo = self.welo[p2_id]
        self.welo[p1_id] = self._new_welo(
            p1_welo, p2_welo, p1_matches, p1_win, games_ratio=games_ratio
        )
        self.welo[p2_id] = self._new_welo(
            p2_welo, p1_welo, p2_matches, p2_win, games_ratio=games_ratio
        )

    def _update_surface_elos(self, match: Match, surface: Surface):
        p1_id = match.player1_id
        p2_id = match.player2_id

        p1_win, p2_win = self._winner_indicators(match)
        games_ratio = match.games_ratio()

        p1_matches = self.get_total_surface_matches(p1_id, surface)
        p2_matches = self.get_total_surface_matches(p2_id, surface)

        p1_elo = self.surface_elo[(p1_id, surface)]
        p2_elo = self.surface_elo[(p2_id, surface)]
        self.surface_elo[(p1_id, surface)] = self._new_elo(
            p1_elo, p2_elo, p1_matches, p1_win
        )
        self.surface_elo[(p2_id, surface)] = self._new_elo(
            p2_elo, p1_elo, p2_matches, p2_win
        )

        p1_welo = self.surface_welo[(p1_id, surface)]
        p2_welo = self.surface_welo[(p2_id, surface)]
        self.surface_welo[(p1_id, surface)] = self._new_welo(
            p1_welo, p2_welo, p1_matches, p1_win, games_ratio=games_ratio
        )
        self.surface_welo[(p2_id, surface)] = self._new_welo(
            p2_welo, p1_welo, p2_matches, p2_win, games_ratio=games_ratio
        )

    def _winner_indicators(self, match: Match) -> tuple[float, float]:
        if match.winner == 1:
            p1_win, p2_win = (1, 0)
        elif match.winner == 2:
            p1_win, p2_win = (0, 1)
        else:
            raise DataInconsistencyError(
                f"Invalid winner '{match.winner}' for match {match}"
            )

        return p1_win, p2_win

    def _new_elo(
        self,
        player_elo: float,
        opponent_elo: float,
        num_matches: int,
        winner_indicator: float,
    ) -> float:
        win_prob = self._win_probability(player_elo, opponent_elo)
        scale_factor = self._scale_factor(num_matches)

        return player_elo + scale_factor * (winner_indicator - win_prob)

    def _new_welo(
        self,
        player_welo: float,
        opponent_welo: float,
        num_matches: int,
        winner_indicator: float,
        *,
        games_ratio: float,
    ) -> float:
        win_prob = self._win_probability(player_welo, opponent_welo)
        scale_factor = self._scale_factor(num_matches)

        return player_welo + scale_factor * (winner_indicator - win_prob) * games_ratio

    def _win_probability(self, player_elo: float, opponent_elo: float) -> float:
        return 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))

    def _scale_factor(self, num_matches: int) -> float:
        """
        The scale factor is based on the number of matches the player has played,
        according to a formula suggested by Kovalchik in a paper from 2016
        """
        return 250 / (num_matches + 5) ** 0.4

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

    def get_elo(self, player_id: int) -> float:
        return self.elo[player_id]

    def get_welo(self, player_id: int) -> float:
        return self.welo[player_id]

    def get_surface_elo(self, player_id: int, surface: Surface) -> float:
        return self.surface_elo[(player_id, surface)]

    def get_surface_welo(self, player_id: int, surface: Surface) -> float:
        return self.surface_welo[(player_id, surface)]

    def get_glicko(self, player_id: int) -> float:
        return self.glicko.get_rating(player_id)

    def get_wglicko(self, player_id: int) -> float:
        return self.wglicko.get_rating(player_id)

    def get_surface_glicko(self, player_id: int, surface: Surface) -> float:
        return self.surface_glicko[surface].get_rating(player_id)

    def get_surface_wglicko(self, player_id: int, surface: Surface) -> float:
        return self.surface_wglicko[surface].get_rating(player_id)


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
        "player1_welo",
        "player1_surface_elo",
        "player1_surface_welo",
        "player1_glicko",
        "player1_wglicko",
        "player1_surface_glicko",
        "player1_surface_wglicko",
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
        "player2_welo",
        "player2_surface_elo",
        "player2_surface_welo",
        "player2_glicko",
        "player2_wglicko",
        "player2_surface_glicko",
        "player2_surface_wglicko",
        "score",
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
            stats.glicko.set_current_date(tournament.start_date)
            stats.wglicko.set_current_date(tournament.start_date)
            if tournament.surface is not None:
                stats.surface_glicko[tournament.surface].set_current_date(
                    tournament.start_date
                )
                stats.surface_wglicko[tournament.surface].set_current_date(
                    tournament.start_date
                )
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
        "player1_elo": stats.get_elo(match.player1_id),
        "player1_welo": stats.get_welo(match.player1_id),
        "player1_surface_elo": stats.get_surface_elo(
            match.player1_id, tournament.surface
        ),
        "player1_surface_welo": stats.get_surface_welo(
            match.player1_id, tournament.surface
        ),
        "player1_glicko": stats.get_glicko(match.player1_id),
        "player1_wglicko": stats.get_wglicko(match.player1_id),
        "player1_surface_glicko": stats.get_surface_glicko(
            match.player1_id, tournament.surface
        ),
        "player1_surface_wglicko": stats.get_surface_wglicko(
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
        "player2_elo": stats.get_elo(match.player2_id),
        "player2_welo": stats.get_welo(match.player2_id),
        "player2_surface_elo": stats.get_surface_elo(
            match.player2_id, tournament.surface
        ),
        "player2_surface_welo": stats.get_surface_welo(
            match.player2_id, tournament.surface
        ),
        "player2_glicko": stats.get_glicko(match.player2_id),
        "player2_wglicko": stats.get_wglicko(match.player2_id),
        "player2_surface_glicko": stats.get_surface_glicko(
            match.player2_id, tournament.surface
        ),
        "player2_surface_wglicko": stats.get_surface_wglicko(
            match.player2_id, tournament.surface
        ),
        "score": match.score,
        "winner": match.winner,
    }

    # Update stats after getting the values for the current match
    stats.add_match(tournament, match)

    return row
