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
            writer.writerow(_match_data(dataset, tournament, match, stats))

    info(f"Exported {stats.total_matches} matches to {path}")


def _to_string(value: Any | None) -> str:
    return str(value) if value is not None else ""


def _format_date(a_date: date | None) -> str:
    return a_date.strftime("%Y-%m-%d") if a_date else ""


def _match_data(
    dataset: TennisDataset, tournament: Tournament, match: Match, stats: Stats
) -> dict[str, str | int | float | None]:
    player1 = dataset.get_player(match.player1_id)
    player2 = dataset.get_player(match.player2_id)
    if player1 is None or player2 is None:
        raise DataInconsistencyError(
            f"Player data not found for match {match} at {tournament}"
        )

    stats.set_current_match(tournament.start_date, tournament.surface)
    player1_stats = stats.get_player_stats(player1)
    player2_stats = stats.get_player_stats(player2)
    player1_surface_stats = stats.get_player_surface_stats(player1, tournament.surface)
    player2_surface_stats = stats.get_player_surface_stats(player2, tournament.surface)

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
        "player1_rank": player1_stats.rank,
        "player1_points": player1_stats.points,
        "player1_highest_rank": player1_stats.highest_rank,
        "player1_total_matches": player1_stats.get_total_matches(),
        "player1_win_rate": player1_stats.get_win_rate(),
        "player1_surface_matches": player1_surface_stats.get_total_matches(),
        "player1_surface_win_rate": player1_surface_stats.get_win_rate(),
        "player1_head2head_wins": stats.get_head2head_wins(
            match.player1_id, match.player2_id
        ),
        "player1_head2head_surface_wins": stats.get_head2head_surface_wins(
            match.player1_id, match.player2_id, tournament.surface
        ),
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
        "player2_rank": player2_stats.rank,
        "player2_points": player2_stats.points,
        "player2_highest_rank": player2_stats.highest_rank,
        "player2_total_matches": player2_stats.get_total_matches(),
        "player2_win_rate": player2_stats.get_win_rate(),
        "player2_surface_matches": player2_surface_stats.get_total_matches(),
        "player2_surface_win_rate": player2_surface_stats.get_win_rate(),
        "player2_head2head_wins": stats.get_head2head_wins(
            match.player2_id, match.player1_id
        ),
        "player2_head2head_surface_wins": stats.get_head2head_surface_wins(
            match.player2_id, match.player1_id, tournament.surface
        ),
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
