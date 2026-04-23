"""
Statistics about the dataset.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .data import DataInconsistencyError, Match, Player, Ranking, Tournament
from .elo import EloRatings
from .enums import Surface
from .glicko2 import GlickoRatings


class Stats:
    """
    Statistics about the dataset.
    """

    def __init__(self):
        self.total_matches = 0
        self._match_date: date | None = None
        self._match_surface: Surface | None = None
        self._player_stats: dict[int, PlayerStats] = {}
        self._player_surface_stats: dict[tuple[int, Surface], PlayerSurfaceStats] = (
            defaultdict(lambda: PlayerSurfaceStats)
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

    def set_current_match(self, match_date: date, surface: Surface | None = None):
        assert match_date is not None and (
            self._match_date is None or match_date >= self._match_date
        )

        self._match_date = match_date
        self._match_surface = surface

        self.glicko.set_current_date(match_date)
        self.wglicko.set_current_date(match_date)
        if surface is not None:
            self.surface_glicko[surface].set_current_date(match_date)
            self.surface_wglicko[surface].set_current_date(match_date)

    def get_player_stats(self, player: Player) -> PlayerStats:
        if player.player_id not in self._player_stats:
            self._player_stats[player.player_id] = PlayerStats(
                player.get_ranking(self._match_date)
            )
        else:
            self._player_stats[player.player_id].update_ranking(
                player.get_ranking(self._match_date)
            )

        return self._player_stats[player.player_id]

    def get_player_surface_stats(
        self, player: Player, surface: Surface
    ) -> PlayerSurfaceStats:
        if (player.player_id, surface) not in self._player_surface_stats:
            self._player_surface_stats[(player.player_id, surface)] = (
                PlayerSurfaceStats()
            )
        return self._player_surface_stats[(player.player_id, surface)]

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

        self._player_stats[winner_id].add_win()
        self._player_stats[loser_id].add_loss()

        self.head2head_wins[(winner_id, loser_id)] += 1
        self.elo.add_result(winner_id, loser_id)
        self.welo.add_result(winner_id, loser_id, games_ratio)
        self.glicko.add_result(winner_id, loser_id)
        self.wglicko.add_result(winner_id, loser_id, games_ratio)

        if tournament.surface is not None:
            self._player_surface_stats[(winner_id, tournament.surface)].add_win()
            self._player_surface_stats[(loser_id, tournament.surface)].add_loss()

            self.head2head_surface_wins[(winner_id, loser_id, tournament.surface)] += 1
            self.surface_elo[tournament.surface].add_result(winner_id, loser_id)
            self.surface_welo[tournament.surface].add_result(
                winner_id, loser_id, games_ratio
            )
            self.surface_glicko[tournament.surface].add_result(winner_id, loser_id)
            self.surface_wglicko[tournament.surface].add_result(
                winner_id, loser_id, games_ratio
            )

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


class PlayerStats:
    """
    Statistics about a single player.
    """

    def __init__(self, ranking: Ranking | None = None):
        if ranking is not None:
            self.rank = ranking.position
            self.highest_rank = ranking.position
            self.points = ranking.points
        else:
            self.rank = None
            self.highest_rank = None
            self.points = None

        self._wins = 0
        self._losses = 0

    def update_ranking(self, new_ranking: Ranking | None = None):
        if new_ranking is None:
            new_rank = None
            new_points = None
        else:
            new_rank = new_ranking.position
            new_points = new_ranking.points

        self.rank = new_rank
        self.points = new_points

        if new_rank is not None and (
            self.highest_rank is None or self.highest_rank > new_rank
        ):
            self.highest_rank = new_rank

    def add_win(self):
        self._wins += 1

    def add_loss(self):
        self._losses += 1

    def get_total_matches(self) -> int:
        return self._wins + self._losses

    def get_win_rate(self) -> float | None:
        total_matches = self.get_total_matches()
        if total_matches == 0:
            return None
        return self._wins / total_matches


class PlayerSurfaceStats:
    """
    Statistics about a single player on a specific surface.
    """

    def __init__(self):
        self._wins = 0
        self._losses = 0

    def add_win(self):
        self._wins += 1

    def add_loss(self):
        self._losses += 1

    def get_total_matches(self) -> int:
        return self._wins + self._losses

    def get_win_rate(self) -> float | None:
        total_matches = self.get_total_matches()
        if total_matches == 0:
            return None
        return self._wins / total_matches
