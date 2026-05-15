#!/usr/bin/env python3
"""
Build the dataset with ATP data from a set of CSV files.
"""

from __future__ import annotations

import argparse
from logging import DEBUG, INFO, basicConfig, error
from pathlib import Path

from .data import DataInconsistencyError, TennisDataset
from .export import export_matches, export_ranking_comparison
from .load import load_matches, load_players, load_rankings


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
    parser.add_argument(
        "-r",
        "--ranking-file",
        type=Path,
        help="Ranking comparison output file",
    )

    return parser.parse_args()


def main() -> None:

    args = parse_args()
    csv_dir: Path = args.csv_dir
    dataset_file: Path = args.dataset_file

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
        stats = export_matches(dataset, dataset_file)
        if args.ranking_file:
            export_ranking_comparison(dataset, stats, args.ranking_file)
    except DataInconsistencyError as exc:
        error(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
