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
from .process import iter_matches


def export_matches(dataset: TennisDataset, path: Path) -> None:
    """
    Write every match in ``dataset`` to a single CSV at ``path``.

    Rows are ordered by tournament start date, then tournament id (for stable
    ordering when dates coincide), then match number.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = (
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
        "player2_id",
        "player2_name",
        "player2_hand",
        "player2_height_cm",
        "player2_age",
        "player2_rank",
        "player2_points",
        "winner",
    )

    levels = {
        TournamentLevel.ATP,
        TournamentLevel.FINALS,
        TournamentLevel.GRAND_SLAM,
        TournamentLevel.MASTERS_1000,
    }

    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tournament, match in iter_matches(dataset, tournament_levels=levels):
            writer.writerow(_match_row(dataset, tournament, match))
            count += 1

    info(f"Exported {count} matches to {path}")


def _to_string(value: Any | None) -> str:
    return str(value) if value is not None else ""


def _format_date(a_date: date | None) -> str:
    return a_date.strftime("%Y-%m-%d") if a_date else ""


def _match_row(
    dataset: TennisDataset, tournament: Tournament, match: Match
) -> dict[str, str | int | float | None]:
    player1 = dataset.get_player(match.player1_id)
    player2 = dataset.get_player(match.player2_id)
    if player1 is None or player2 is None:
        raise DataInconsistencyError(
            f"Player data not found for match {match} at {tournament}"
        )

    player1_ranking = player1.get_ranking(tournament.start_date)
    if player1_ranking is not None:
        player1_rank = player1_ranking.position
        player1_points = player1_ranking.points
    else:
        player1_rank = None
        player1_points = None

    player2_ranking = player2.get_ranking(tournament.start_date)
    if player2_ranking is not None:
        player2_rank = player2_ranking.position
        player2_points = player2_ranking.points
    else:
        player2_rank = None
        player2_points = None

    return {
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
        "player2_id": match.player2_id,
        "player2_name": player2.full_name(),
        "player2_hand": _to_string(player2.hand),
        "player2_height_cm": player2.height_cm,
        "player2_age": player2.age_at(tournament.start_date),
        "player2_rank": player2_rank,
        "player2_points": player2_points,
        "winner": match.winner,
    }
