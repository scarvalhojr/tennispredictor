"""
Statistics about the dataset.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from .data import DataInconsistencyError, Match, Player, Ranking, Tournament
from .elo import EloRatings
from .enums import Surface
from .glicko2 import GlickoRatings

YEAR_DAYS = timedelta(days=365)


class Stats:
    """
    Statistics about the dataset.
    """

    def __init__(self):
        self.total_matches = 0
        self._match_date: date | None = None
        self._match_surface: Surface | None = None
        self._player_ranking_stats: dict[int, PlayerRankingStats] = {}
        self._player_overall_stats: dict[int, PlayerMatchStats] = {}
        self._player_surface_stats: dict[tuple[int, Surface], PlayerMatchStats] = (
            defaultdict(lambda: PlayerMatchStats)
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

        surface = tournament.surface
        match_date = tournament.start_date

        games_ratio = match.games_ratio()

        self._player_overall_stats[winner_id].add_win(match_date)
        self._player_overall_stats[loser_id].add_loss(match_date)

        self.head2head_wins[(winner_id, loser_id)] += 1
        self.elo.add_result(winner_id, loser_id)
        self.welo.add_result(winner_id, loser_id, games_ratio)
        self.glicko.add_result(winner_id, loser_id)
        self.wglicko.add_result(winner_id, loser_id, games_ratio)

        if tournament.surface is not None:
            self._player_surface_stats[(winner_id, surface)].add_win(match_date)
            self._player_surface_stats[(loser_id, surface)].add_loss(match_date)

            self.head2head_surface_wins[(winner_id, loser_id, surface)] += 1

            self.surface_elo[surface].add_result(winner_id, loser_id)
            self.surface_welo[surface].add_result(winner_id, loser_id, games_ratio)
            self.surface_glicko[surface].add_result(winner_id, loser_id)
            self.surface_wglicko[surface].add_result(winner_id, loser_id, games_ratio)

    def get_player_ranking_stats(self, player: Player) -> PlayerRankingStats:
        assert self._match_date is not None

        if player.player_id not in self._player_ranking_stats:
            self._player_ranking_stats[player.player_id] = PlayerRankingStats(
                player.get_ranking(self._match_date)
            )
        else:
            self._player_ranking_stats[player.player_id].update(
                player.get_ranking(self._match_date)
            )

        return self._player_ranking_stats[player.player_id]

    def get_player_overall_stats(self, player_id: int) -> PlayerMatchStats:
        if player_id not in self._player_overall_stats:
            self._player_overall_stats[player_id] = PlayerMatchStats()
        else:
            self._player_overall_stats[player_id].update(self._match_date)

        return self._player_overall_stats[player_id]

    def get_player_surface_stats(
        self, player_id: int, surface: Surface | None
    ) -> PlayerMatchStats:
        if surface is None:
            return self.get_player_overall_stats(player_id)

        if (player_id, surface) not in self._player_surface_stats:
            self._player_surface_stats[(player_id, surface)] = PlayerMatchStats()
        else:
            self._player_surface_stats[(player_id, surface)].update(self._match_date)

        return self._player_surface_stats[(player_id, surface)]

    def get_head2head_wins(self, player1_id: int, player2_id: int) -> int:
        return self.head2head_wins[(player1_id, player2_id)]

    def get_head2head_surface_wins(
        self, player1_id: int, player2_id: int, surface: Surface | None
    ) -> int | None:
        if surface is None:
            return self.head2head_wins[(player1_id, player2_id)]

        return self.head2head_surface_wins[(player1_id, player2_id, surface)]

    def get_elo(self, player_id: int) -> float:
        return self.elo.get_rating(player_id)

    def get_welo(self, player_id: int) -> float:
        return self.welo.get_rating(player_id)

    def get_surface_elo(self, player_id: int, surface: Surface) -> float:
        if surface is None:
            return self.get_elo(player_id)

        return self.surface_elo[surface].get_rating(player_id)

    def get_surface_welo(self, player_id: int, surface: Surface) -> float:
        if surface is None:
            return self.get_welo(player_id)

        return self.surface_welo[surface].get_rating(player_id)

    def get_glicko(self, player_id: int) -> float:
        return self.glicko.get_rating(player_id)

    def get_wglicko(self, player_id: int) -> float:
        return self.wglicko.get_rating(player_id)

    def get_surface_glicko(self, player_id: int, surface: Surface) -> float:
        if surface is None:
            return self.get_glicko(player_id)

        return self.surface_glicko[surface].get_rating(player_id)

    def get_surface_wglicko(self, player_id: int, surface: Surface) -> float:
        if surface is None:
            return self.get_wglicko(player_id)

        return self.surface_wglicko[surface].get_rating(player_id)


class PlayerRankingStats:
    """
    Statistics about a single player's ranking.
    """

    def __init__(self, current_ranking: Ranking | None = None):
        if current_ranking is not None:
            self.rank = current_ranking.position
            self.highest_rank = current_ranking.position
            self.points = current_ranking.points
        else:
            self.rank = None
            self.highest_rank = None
            self.points = None

    def update(self, new_ranking: Ranking | None = None):
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


class PlayerMatchStats:
    """
    Statistics about a single player's matches.
    """

    def __init__(self):
        self._career_wins: int = 0
        self._career_losses: int = 0
        self._year_win_dates: list[date] = []
        self._year_loss_dates: list[date] = []

    def update(self, current_date: date):
        a_year_ago = current_date - YEAR_DAYS
        self._year_win_dates = [d for d in self._year_win_dates if d >= a_year_ago]
        self._year_loss_dates = [d for d in self._year_loss_dates if d >= a_year_ago]

    def add_win(self, match_date: date):
        self._career_wins += 1
        self._year_win_dates.append(match_date)

    def add_loss(self, match_date: date):
        self._career_losses += 1
        self._year_loss_dates.append(match_date)

    def get_career_matches(self) -> int:
        return self._career_wins + self._career_losses

    def get_year_matches(self) -> int:
        return len(self._year_win_dates) + len(self._year_loss_dates)

    def get_career_win_rate(self) -> float | None:
        total_matches = self.get_career_matches()
        if total_matches == 0:
            return None
        return self._career_wins / total_matches

    def get_year_win_rate(self) -> float | None:
        year_matches = self.get_year_matches()
        if year_matches == 0:
            return None
        return len(self._year_win_dates) / year_matches
