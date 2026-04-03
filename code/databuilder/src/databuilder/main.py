#!/usr/bin/env python3
"""
Build the dataset with ATP data from a set of CSV files.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from logging import DEBUG, INFO, basicConfig, error, info, warning
from pathlib import Path

from .data import DataInconsistencyError, Player, TennisDataset
from .enums import Hand, Surface, TournamentLevel


def parse_player_id(raw: str | None, line_no: int) -> int | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DataInconsistencyError(
            f"Invalid player ID ('{value}') at line number {line_no}"
        ) from exc


def parse_string(s: str | None) -> str | None:
    return (s or "").strip() or None


def parse_hand(raw: str | None, line_no: int) -> Hand | None:
    if raw is None:
        return None
    value = str(raw).strip().upper()
    if not value or value == "U":
        return None
    try:
        return Hand(value)
    except ValueError:
        warning(f"Ignoring invalid hand '{raw}' at line number {line_no}")
        return None


def parse_date(raw: str | None, line_no: int) -> date | None:
    """YYYYMMDD -> date object; empty or invalid -> None."""
    if raw is None:
        return None

    s = str(raw).strip()
    if len(s) != 8 or not s.isdigit():
        if len(s) > 0:
            warning(f"Ignoring invalid date '{raw}' at line number {line_no}")
        return None

    year, month, day = int(s[:4]), int(s[4:6]), int(s[6:8])
    try:
        return date(year, month, day)
    except ValueError:
        warning(f"Ignoring invalid date '{raw}' at line number {line_no}")
        return None


def parse_country_code(raw: str | None, line_no: int) -> str | None:
    if raw is None:
        return None

    s = str(raw).strip().upper()
    if len(s) == 3:
        return s

    if len(s) > 0:
        warning(f"Ignoring invalid country code '{raw}' at line number {line_no}")
    return None


def parse_integer(raw: str | None, line_no: int) -> int | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DataInconsistencyError(
            f"Invalid integer '{raw}' at line number {line_no}"
        ) from exc


def parse_surface(raw: str | None, line_no: int) -> Surface | None:
    if raw is None:
        return None
    initial = str(raw).strip().capitalize()
    if not initial:
        return None
    try:
        return Surface(initial)
    except ValueError:
        warning(f"Ignoring invalid surface '{raw}' at line number {line_no}")
        return None


def parse_tournament_level(raw: str | None, line_no: int) -> TournamentLevel | None:
    if raw is None:
        return None
    value = str(raw).strip().upper()
    if not value:
        return None
    try:
        return TournamentLevel(value)
    except ValueError:
        warning(f"Ignoring invalid tournament level '{raw}' at line number {line_no}")
        return None


def load_players(csv_dir: Path, dataset: TennisDataset) -> None:
    csv_path = csv_dir / "atp_players.csv"
    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    info(f"Loading players from {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "player_id",
            "name_first",
            "name_last",
            "hand",
            "dob",
            "ioc",
            "height",
            "wikidata_id",
        }
        if reader.fieldnames is None:
            raise SystemExit("CSV has no header row.")
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"CSV missing columns: {sorted(missing)}")

        for line_no, row in enumerate(reader, start=2):
            player_id = parse_player_id(row.get("player_id"), line_no=line_no)
            if not player_id:
                raise DataInconsistencyError(
                    f"Player with missing ID at row number {line_no}"
                )

            player = Player(
                player_id=player_id,
                first_name=parse_string(row.get("name_first")),
                last_name=parse_string(row.get("name_last")),
                hand=parse_hand(row.get("hand"), line_no),
                birth_date=parse_date(row.get("dob"), line_no),
                country_code=parse_country_code(row.get("ioc"), line_no),
                height_cm=parse_integer(row.get("height"), line_no),
            )
            dataset.add_player(player)

    info(f"Loaded {dataset.count_players()} players from {csv_path}")


def load_rankings(csv_dir: Path, dataset: TennisDataset) -> None:
    # Decade files are named atp_rankings_00s.csv, atp_rankings_10s.csv, etc.
    decade = sorted(csv_dir.glob("atp_rankings_??s.csv"))
    current = csv_dir / "atp_rankings_current.csv"
    files = list(decade)
    if current.is_file():
        files.append(current)

    if not files:
        raise SystemExit(
            f"No ranking CSV files found under {csv_dir} "
            "(expected atp_rankings_??s.csv and atp_rankings_current.csv)."
        )

    for file in files:
        load_rankings_file(file, dataset)


def load_rankings_file(file: Path, dataset: TennisDataset) -> None:
    required = {"ranking_date", "rank", "player", "points"}

    info(f"Loading rankings from {file}")
    with file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise SystemExit(f"{file}: CSV has no header row.")
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"{file}: missing columns: {sorted(missing)}")

        for line_no, row in enumerate(reader, start=2):
            player_id_str = row.get("player")
            player_id = parse_player_id(player_id_str, line_no=line_no)
            if player_id:
                player = dataset.get_player(player_id)
            else:
                player = None
            if not player:
                warning(
                    "Ignoring ranking for player with missing, invalid or unknown "
                    f"ID ({player_id_str}) at line number {line_no}"
                )
                continue

            ranking_date_str = row.get("ranking_date")
            ranking_date = parse_date(ranking_date_str, line_no=line_no)
            if ranking_date is None:
                warning(
                    f"Ignoring ranking for player {player} with missing or "
                    f"invalid date ({ranking_date_str}) at line number {line_no}"
                )
                continue

            position = parse_integer(row.get("rank"), line_no=line_no)
            points = parse_integer(row.get("points"), line_no=line_no)
            player.add_ranking(ranking_date, position, points)

        info(f"Loaded {reader.line_num - 1} ranking rows from {file}")


def load_matches(csv_dir: Path, dataset: TennisDataset) -> None:
    # Match files from the main ATP tour events are named atp_matches_????.csv
    files = sorted(csv_dir.glob("atp_matches_????.csv"))

    if not files:
        raise SystemExit(
            f"No match CSV files found under {csv_dir} "
            "(expected atp_matches_????.csv)."
        )

    for file in files:
        load_matches_file(file, dataset)


def load_matches_file(file: Path, dataset: TennisDataset) -> None:
    required = {
        "tourney_id",
        "tourney_name",
        "surface",
        "draw_size",
        "tourney_level",
        "tourney_date",
    }

    info(f"Loading matches from {file}")
    with file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise SystemExit(f"{file}: CSV has no header row.")
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"{file}: missing columns: {sorted(missing)}")

        for line_no, row in enumerate(reader, start=2):
            tournament_id = parse_string(row.get("tourney_id"))
            if not tournament_id:
                raise DataInconsistencyError(
                    f"Tournament ID is missing at line number {line_no}"
                )

            _tournament = dataset.add_tournament(
                tournament_id,
                tournament_name=parse_string(row.get("tourney_name")),
                surface=parse_surface(row.get("surface"), line_no=line_no),
                draw_size=parse_integer(row.get("draw_size"), line_no=line_no),
                tournament_level=parse_tournament_level(
                    row.get("tourney_level"), line_no=line_no
                ),
                tournament_date=parse_date(row.get("tourney_date"), line_no=line_no),
            )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create ATP dataset from a set of CSV files.",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "-c",
        "--csv-dir",
        type=Path,
        default=Path.cwd(),
        help="Path to CSV files (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--dataset-file",
        type=Path,
        default=Path.cwd() / "atp_matches.csv",
        help="Final dataset file (default: atp_matches.csv)",
    )

    return parser.parse_args()


def main() -> None:

    args = parse_args()
    csv_dir: Path = args.csv_dir
    # dataset_file: Path = args.dataset_file

    # Setup logging
    if args.debug:
        level = DEBUG
    else:
        level = INFO
    basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)

    dataset = TennisDataset()

    try:
        load_players(csv_dir, dataset)
        load_rankings(csv_dir, dataset)
        load_matches(csv_dir, dataset)
    except DataInconsistencyError as exc:
        error(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
