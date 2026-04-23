"""
Export dataset structures to flat files.
"""

from __future__ import annotations

import csv
from datetime import date
from logging import info
from pathlib import Path
from typing import Any

from .data import DataInconsistencyError, Match, TennisDataset, Tournament
from .enums import TournamentLevel
from .iter import iter_matches
from .stats import Stats


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
        "player1_career_matches",
        "player1_career_win_rate",
        "player1_year_matches",
        "player1_year_win_rate",
        "player1_surface_career_matches",
        "player1_surface_career_win_rate",
        "player1_surface_year_matches",
        "player1_surface_year_win_rate",
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
        "player2_career_matches",
        "player2_career_win_rate",
        "player2_year_matches",
        "player2_year_win_rate",
        "player2_surface_career_matches",
        "player2_surface_career_win_rate",
        "player2_surface_year_matches",
        "player2_surface_year_win_rate",
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
            writer.writerow(_match_data(dataset, tournament, match, stats))

    info(f"Exported {stats.total_matches} matches to {path}")


def _to_string(value: Any | None) -> str:
    return str(value) if value is not None else ""


def _format_date(a_date: date | None) -> str:
    return a_date.strftime("%Y-%m-%d") if a_date else ""


def _match_data(
    dataset: TennisDataset, tournament: Tournament, match: Match, stats: Stats
) -> dict[str, str | int | float | None]:
    player1_id, player2_id = (match.player1_id, match.player2_id)
    player1 = dataset.get_player(player1_id)
    player2 = dataset.get_player(player2_id)
    if player1 is None or player2 is None:
        raise DataInconsistencyError(
            f"Player data not found for match {match} at {tournament}"
        )

    surface = tournament.surface
    tournament_date = tournament.start_date

    stats.set_current_match(tournament_date, surface)
    player1_ranking = stats.get_player_ranking_stats(player1)
    player2_ranking = stats.get_player_ranking_stats(player2)
    player1_overall = stats.get_player_overall_stats(player1_id)
    player2_overall = stats.get_player_overall_stats(player2_id)
    player1_surface = stats.get_player_surface_stats(player1_id, surface)
    player2_surface = stats.get_player_surface_stats(player2_id, surface)

    row = {
        "year": tournament_date.year,
        "tournament_id": tournament.tournament_id,
        "tournament_start_date": _format_date(tournament_date),
        "tournament_name": tournament.name,
        "tournament_level": tournament.level.value,
        "surface": surface,
        "draw_size": tournament.draw_size,
        "match_num": match.match_num,
        "best_of": match.best_of,
        "player1_id": player1_id,
        "player1_name": player1.full_name(),
        "player1_hand": _to_string(player1.hand),
        "player1_height_cm": player1.height_cm,
        "player1_age": player1.age_at(tournament_date),
        "player1_rank": player1_ranking.rank,
        "player1_points": player1_ranking.points,
        "player1_highest_rank": player1_ranking.highest_rank,
        "player1_career_matches": player1_overall.get_career_matches(),
        "player1_career_win_rate": player1_overall.get_career_win_rate(),
        "player1_year_matches": player1_overall.get_year_matches(),
        "player1_year_win_rate": player1_overall.get_year_win_rate(),
        "player1_surface_career_matches": player1_surface.get_career_matches(),
        "player1_surface_career_win_rate": player1_surface.get_career_win_rate(),
        "player1_surface_year_matches": player1_surface.get_year_matches(),
        "player1_surface_year_win_rate": player1_surface.get_year_win_rate(),
        "player1_head2head_wins": stats.get_head2head_wins(player1_id, player2_id),
        "player1_head2head_surface_wins": stats.get_head2head_surface_wins(
            player1_id, player2_id, surface
        ),
        "player1_elo": stats.get_elo(player1_id),
        "player1_welo": stats.get_welo(player1_id),
        "player1_surface_elo": stats.get_surface_elo(player1_id, surface),
        "player1_surface_welo": stats.get_surface_welo(player1_id, surface),
        "player1_glicko": stats.get_glicko(player1_id),
        "player1_wglicko": stats.get_wglicko(player1_id),
        "player1_surface_glicko": stats.get_surface_glicko(player1_id, surface),
        "player1_surface_wglicko": stats.get_surface_wglicko(player1_id, surface),
        "player2_id": player2_id,
        "player2_name": player2.full_name(),
        "player2_hand": _to_string(player2.hand),
        "player2_height_cm": player2.height_cm,
        "player2_age": player2.age_at(tournament_date),
        "player2_rank": player2_ranking.rank,
        "player2_points": player2_ranking.points,
        "player2_highest_rank": player2_ranking.highest_rank,
        "player2_career_matches": player2_overall.get_career_matches(),
        "player2_career_win_rate": player2_overall.get_career_win_rate(),
        "player2_year_matches": player2_overall.get_year_matches(),
        "player2_year_win_rate": player2_overall.get_year_win_rate(),
        "player2_surface_career_matches": player2_surface.get_career_matches(),
        "player2_surface_career_win_rate": player2_surface.get_career_win_rate(),
        "player2_surface_year_matches": player2_surface.get_year_matches(),
        "player2_surface_year_win_rate": player2_surface.get_year_win_rate(),
        "player2_head2head_wins": stats.get_head2head_wins(player2_id, player1_id),
        "player2_head2head_surface_wins": stats.get_head2head_surface_wins(
            player2_id, player1_id, surface
        ),
        "player2_elo": stats.get_elo(player2_id),
        "player2_welo": stats.get_welo(player2_id),
        "player2_surface_elo": stats.get_surface_elo(player2_id, surface),
        "player2_surface_welo": stats.get_surface_welo(player2_id, surface),
        "player2_glicko": stats.get_glicko(player2_id),
        "player2_wglicko": stats.get_wglicko(player2_id),
        "player2_surface_glicko": stats.get_surface_glicko(player2_id, surface),
        "player2_surface_wglicko": stats.get_surface_wglicko(player2_id, surface),
        "score": match.score,
        "winner": match.winner,
    }

    # Update stats after getting the values for the current match
    stats.add_match(tournament, match)

    return row
