"""
Export dataset structures to flat files.
"""

from __future__ import annotations

import csv
from logging import info
from pathlib import Path

from .data import Match, TennisDataset, Tournament
from .enums import TournamentLevel


def export_matches(dataset: TennisDataset, path: Path) -> int:
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
        "player1_id",
        "player2_id",
        "winner",
        "score",
        "best_of",
    )

    levels = {
        TournamentLevel.ATP,
        TournamentLevel.FINALS,
        TournamentLevel.GRAND_SLAM,
        TournamentLevel.MASTERS_1000,
    }

    tournaments = [t for t in dataset.tournaments.values() if t.level in levels]

    tournaments.sort(key=lambda t: (t.start_date, t.tournament_id))

    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tournament in tournaments:
            matches = sorted(
                tournament.matches.values(),
                key=lambda m: m.match_num,
            )
            for match in matches:
                writer.writerow(_match_row(tournament, match))
                count += 1

    info(f"Exported {count} matches to {path}")
    return count


def _match_row(tournament: Tournament, match: Match) -> dict[str, str | int]:
    surface = tournament.surface
    draw = tournament.draw_size
    return {
        "tournament_id": tournament.tournament_id,
        "tournament_start_date": tournament.start_date.strftime("%Y%m%d"),
        "tournament_name": tournament.name or "",
        "tournament_level": tournament.level.value,
        "surface": str(surface) if surface is not None else "",
        "draw_size": draw if draw is not None else "",
        "match_num": match.match_num,
        "player1_id": match.player1_id,
        "player2_id": match.player2_id,
        "winner": match.winner,
        "best_of": match.best_of,
    }
