"""
Process the tennis dataset.
"""

from __future__ import annotations

from collections.abc import Iterator

from databuilder.data import Match, TennisDataset, Tournament
from databuilder.enums import TournamentLevel


def iter_matches(
    dataset: TennisDataset, *, tournament_levels: set[TournamentLevel] = None
) -> Iterator[tuple[Tournament, Match]]:
    """
    Yield each match in global chronological order.

    Tournaments are ordered by start date, then tournament id (stable ordering
    when dates coincide). Within each tournament, matches are ordered by
    ``match_num``.

    If ``tournament_levels`` is provided, only matches from the specified
    tournament levels will be yielded.
    """
    if tournament_levels is None:
        tournaments = dataset.tournaments.values()
    else:
        tournaments = [
            t for t in dataset.tournaments.values() if t.level in tournament_levels
        ]

    sorted_tournaments = sorted(
        tournaments,
        key=lambda t: (t.start_date, t.tournament_id),
    )

    for tournament in sorted_tournaments:
        for match in sorted(
            tournament.matches.values(),
            key=lambda m: m.match_num,
        ):
            yield tournament, match
