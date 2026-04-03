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


class DataInconsistencyError(Exception):
    """Raised when data inconsistency is found."""

    def __init__(self, msg):
        super().__init__(f"Data inconsistency found: {msg}")


class TennisDataset:
    """A tennis dataset."""

    def __init__(self):
        self.players: dict[int, Player] = {}

    def add_player(self, player: Player):
        if player.player_id in self.players:
            raise DataInconsistencyError(
                f"Player with ID {player.player_id} already exists"
            )
        self.players[player.player_id] = player

    def count_players(self) -> int:
        return len(self.players)

    def get_player(self, player_id: int) -> Player | None:
        return self.players.get(player_id)


# pylint: disable=too-many-instance-attributes
class Player:
    """A tennis player."""

    def __init__(
        self,
        player_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        hand: str | None = None,
        birth_date: date | None = None,
        country_code: str | None = None,
        height_cm: int | None,
    ):
        self.player_id = player_id
        self.first_name = first_name
        self.last_name = last_name
        self.hand = hand
        self.birth_date = birth_date
        self.country_code = country_code
        self.height_cm = height_cm
        self.ranking_history: dict[date, Ranking] = {}

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.player_id})"

    def add_ranking(self, ranking_date: date, position: int | None, points: int | None):
        ranking = self.ranking_history.get(ranking_date)
        if ranking is None:
            self.ranking_history[ranking_date] = Ranking(ranking_date, position, points)
        else:
            ranking.update_if_missing(position, points, self)


class Ranking:
    """A tennis ranking."""

    def __init__(self, ranking_date: date, position: int | None, points: int | None):
        self.ranking_date = ranking_date
        self.position = position
        self.points = points

    def __str__(self) -> str:
        return f"{self.position} - {self.points}"

    def update_if_missing(
        self, position: int | None, points: int | None, player: Player
    ):
        if self.position is None:
            self.position = position
        elif position is not None and self.position != position:
            warning(
                f"Ignoring ranking position mismatch for {player} "
                f"on {self.ranking_date} ({self.position} -> {position})"
            )

        if self.points is None:
            self.points = points
        elif points is not None and self.points != points:
            warning(
                f"Ignoring ranking points mismatch for {player} "
                f"on {self.ranking_date} ({self.points} -> {points})"
            )


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


def parse_name(name: str | None) -> str | None:
    return (name or "").strip() or None


def parse_hand(raw: str | None, line_no: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip().upper()
    if value in ("L", "R", "A"):
        return value
    if value != "U" and len(value) > 0:
        warning(f"Ignoring invalid hand: '{value}' at line number {line_no}")
    return None


def parse_date(raw: str | None, line_no: int) -> date | None:
    """YYYYMMDD -> date object; empty or invalid -> None."""
    if raw is None:
        return None

    s = str(raw).strip()
    if len(s) != 8 or not s.isdigit():
        if len(s) > 0:
            warning(f"Ignoring invalid date: '{s}' at line number {line_no}")
        return None

    year, month, day = int(s[:4]), int(s[4:6]), int(s[6:8])
    try:
        return date(year, month, day)
    except ValueError:
        warning(f"Ignoring invalid date: '{s}' at line number {line_no}")
        return None


def parse_height(raw: str | None, line_no: int) -> int | None:
    if raw is None:
        return None

    s = str(raw).strip()
    if not s:
        return None

    try:
        return int(float(s))
    except ValueError:
        warning(f"Ignoring invalid height: '{s}' at line number {line_no}")
        return None


def parse_country_code(raw: str | None, line_no: int) -> str | None:
    if raw is None:
        return None

    s = str(raw).strip().upper()
    if len(s) == 3:
        return s

    if len(s) > 0:
        warning(f"Ignoring invalid country code: '{s}' at line number {line_no}")
    return None


def parse_position(raw: str | None, line_no: int) -> int | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DataInconsistencyError(
            f"Invalid ranking position ('{value}') at line number {line_no}"
        ) from exc


def parse_points(raw: str | None, line_no: int) -> int | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DataInconsistencyError(
            f"Invalid ranking points ('{value}') at line number {line_no}"
        ) from exc


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
                first_name=parse_name(row.get("name_first")),
                last_name=parse_name(row.get("name_last")),
                hand=parse_hand(row.get("hand"), line_no),
                birth_date=parse_date(row.get("dob"), line_no),
                country_code=parse_country_code(row.get("ioc"), line_no),
                height_cm=parse_height(row.get("height"), line_no),
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
    info(f"Loading rankings from {file}")
    with file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"ranking_date", "rank", "player", "points"}

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

            position = parse_position(row.get("rank"), line_no=line_no)
            points = parse_points(row.get("points"), line_no=line_no)
            player.add_ranking(ranking_date, position, points)

        info(f"Loaded {reader.line_num - 1} ranking rows from {file}")


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
    except DataInconsistencyError as exc:
        error(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
