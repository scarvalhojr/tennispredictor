"""
Statistics about the dataset.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .data import DataInconsistencyError, Match, Tournament
from .elo import EloRatings
from .enums import Surface
from .glicko2 import GlickoRatings


class Stats:
    """
    Statistics about the dataset.
    """

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
        self.elo: EloRatings = EloRatings()
        self.welo: EloRatings = EloRatings()
        self.surface_elo: defaultdict[Surface, EloRatings] = defaultdict(EloRatings)
        self.surface_welo: defaultdict[Surface, EloRatings] = defaultdict(EloRatings)
        self.glicko: GlickoRatings = GlickoRatings()
        self.wglicko: GlickoRatings = GlickoRatings()
        self.surface_glicko: defaultdict[Surface, GlickoRatings] = defaultdict(
            GlickoRatings
        )
        self.surface_wglicko: defaultdict[Surface, GlickoRatings] = defaultdict(
            GlickoRatings
        )

    def set_current_date(self, current_date: date, surface: Surface | None = None):
        self.glicko.set_current_date(current_date)
        self.wglicko.set_current_date(current_date)
        if surface is not None:
            self.surface_glicko[surface].set_current_date(current_date)
            self.surface_wglicko[surface].set_current_date(current_date)

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
        self.elo.add_result(winner_id, loser_id)
        self.welo.add_result(winner_id, loser_id, games_ratio)
        self.glicko.add_result(winner_id, loser_id)
        self.wglicko.add_result(winner_id, loser_id, games_ratio)

        if tournament.surface is not None:
            self.total_surface_wins[(winner_id, tournament.surface)] += 1
            self.total_surface_losses[(loser_id, tournament.surface)] += 1
            self.head2head_surface_wins[(winner_id, loser_id, tournament.surface)] += 1
            self.surface_elo[tournament.surface].add_result(winner_id, loser_id)
            self.surface_welo[tournament.surface].add_result(
                winner_id, loser_id, games_ratio
            )
            self.surface_glicko[tournament.surface].add_result(winner_id, loser_id)
            self.surface_wglicko[tournament.surface].add_result(
                winner_id, loser_id, games_ratio
            )

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
        return self.elo.get_rating(player_id)

    def get_welo(self, player_id: int) -> float:
        return self.welo.get_rating(player_id)

    def get_surface_elo(self, player_id: int, surface: Surface) -> float:
        return self.surface_elo[surface].get_rating(player_id)

    def get_surface_welo(self, player_id: int, surface: Surface) -> float:
        return self.surface_welo[surface].get_rating(player_id)

    def get_glicko(self, player_id: int) -> float:
        return self.glicko.get_rating(player_id)

    def get_wglicko(self, player_id: int) -> float:
        return self.wglicko.get_rating(player_id)

    def get_surface_glicko(self, player_id: int, surface: Surface) -> float:
        return self.surface_glicko[surface].get_rating(player_id)

    def get_surface_wglicko(self, player_id: int, surface: Surface) -> float:
        return self.surface_wglicko[surface].get_rating(player_id)
