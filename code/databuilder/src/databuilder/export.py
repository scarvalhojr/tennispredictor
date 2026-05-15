"""
Export dataset structures to flat files.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from logging import error, info
from pathlib import Path
from typing import Any

from .data import DataInconsistencyError, Match, TennisDataset, Tournament
from .enums import Surface, TournamentLevel
from .iter import iter_matches
from .stats import Stats


def export_matches(dataset: TennisDataset, path: Path) -> Stats:
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

        # TODO: add deltas for Elo and Glicko ratings
        # "elo_delta",
        # "welo_delta",
        # "surface_elo_delta",
        # "surface_welo_delta",
        # "glicko_delta",
        # "wglicko_delta",
        # "surface_glicko_delta",
        # "surface_wglicko_delta",

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

    return stats


def _to_string(value: Any | None) -> str:
    return str(value) if value is not None else ""


def _format_date(a_date: date | None) -> str:
    return a_date.strftime("%Y-%m-%d") if a_date else ""


def _match_data(
    dataset: TennisDataset, tournament: Tournament, match: Match, stats: Stats
) -> dict[str, str | int | float | object | None]:
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
        "player1_surface_elo": stats.get_elo(player1_id, surface),
        "player1_surface_welo": stats.get_welo(player1_id, surface),
        "player1_glicko": stats.get_glicko(player1_id),
        "player1_wglicko": stats.get_wglicko(player1_id),
        "player1_surface_glicko": stats.get_glicko(player1_id, surface),
        "player1_surface_wglicko": stats.get_wglicko(player1_id, surface),
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
        "player2_surface_elo": stats.get_elo(player2_id, surface),
        "player2_surface_welo": stats.get_welo(player2_id, surface),
        "player2_glicko": stats.get_glicko(player2_id),
        "player2_wglicko": stats.get_wglicko(player2_id),
        "player2_surface_glicko": stats.get_glicko(player2_id, surface),
        "player2_surface_wglicko": stats.get_wglicko(player2_id, surface),
        # TODO: add deltas for Elo and Glicko ratings
        # "elo_delta": stats.get_elo_delta(player1_id, player2_id),
        # "welo_delta": stats.get_welo_delta(player1_id, player2_id),
        # "surface_elo_delta": stats.get_surface_elo_delta(
        #     player1_id, player2_id, surface
        # ),
        # "surface_welo_delta": stats.get_surface_welo_delta(
        #     player1_id, player2_id, surface
        # ),
        # "glicko_delta": stats.get_glicko_delta(player1_id, player2_id),
        # "wglicko_delta": stats.get_wglicko_delta(player1_id, player2_id),
        # "surface_glicko_delta": stats.get_surface_glicko_delta(
        #     player1_id, player2_id, surface
        # ),
        # "surface_wglicko_delta": stats.get_surface_wglicko_delta(
        #     player1_id, player2_id, surface
        # ),
        "score": match.score,
        "winner": match.winner,
    }

    # Update stats after getting the values for the current match
    stats.add_match(tournament, match)

    return row


def export_ranking_comparison(dataset: TennisDataset, stats: Stats, path: Path) -> None:

    models = set(
        [
            ("elo", stats.get_elo),
            ("welo", stats.get_welo),
            ("glicko", stats.get_glicko),
            ("wglicko", stats.get_wglicko),
        ]
    )

    surfaces = set(
        [
            ("all", None),
            ("hard", Surface.HARD),
            ("clay", Surface.CLAY),
            ("grass", Surface.GRASS),
        ]
    )

    ratings = {
        f"{m}_{n}": (f"rank_{m}_{n}", f, s) for (m, f) in models for (n, s) in surfaces
    }

    fieldnames = tuple(
        [
            "atp_rank",
            "name",
            *ratings.keys(),
            *(rank_name for (rank_name, _, _) in ratings.values()),
        ]
    )

    last_match_date = stats.get_last_match_date()
    if last_match_date is None:
        error("No match data found to produce ranking comparisons: aborting")
        return

    # Get all ranked players 7 days after the last match
    # to make sure all results are accounted for
    ranked_players = dataset.get_ranked_players(last_match_date + timedelta(days=7))

    # Make sure we got exactly one ranking date
    ranking_dates = {ranking.ranking_date for ranking, _ in ranked_players}
    if not ranking_dates:
        error("No rankings found for comparison: aborting")
        return
    if len(ranking_dates) > 1:
        error("Rankings from multiple dates found for comparison: aborting")
        return

    info(f"Comparing rankings as of {ranking_dates.pop()}...")

    rows = []
    for ranking, player in ranked_players:
        if ranking.position is None:
            continue

        row: dict[str, str | int | float] = {
            "atp_rank": ranking.position,
            "name": player.full_name(),
        }

        for rating_name, (rank_name, func, surface) in ratings.items():
            row[rating_name] = func(player.player_id, surface)
            row[rank_name] = 0

        rows.append(row)

    # Now rank the players by each of the alternative rating scores
    for rating_name, (rank_name, func, surface) in ratings.items():
        _update_ranking(rows, rank_name, rating_name)

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    info(f"Exported {len(rows)} players to {path}")


def _update_ranking(rows, rank_name, rating_name):
    info(f"Ranking players by {rating_name}...")
    rows.sort(key=lambda row: row[rating_name], reverse=True)
    for i, row in enumerate(rows):
        row[rank_name] = i + 1
