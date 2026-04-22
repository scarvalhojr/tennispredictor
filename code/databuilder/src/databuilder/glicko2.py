"""
Glicko2 ratings for a set of players using the glicko2-py library.
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import debug, warning

from glicko2 import MatchResult, RatingEngine, RatingPeriod
from glicko2.math.conversions import mu_to_rating

DEFAULT_PERIOD_LENGTH_DAYS = 60


class GlickPeriodNotStartedError(Exception):
    """
    Raised when a period is not started.
    """

    def __init__(self):
        self.message = "Glicko period not started"

    def __str__(self):
        return self.message


class GlickoRatings:
    """
    Glicko2 ratings for a set of players.
    """

    def __init__(self, period_length_days: int = DEFAULT_PERIOD_LENGTH_DAYS):
        self._engine = RatingEngine(tau=0.5)
        self._period_length = timedelta(days=period_length_days)
        self._period_start = None
        self._period_end = None
        self._current_period = None

    def get_rating(self, player_id: int) -> float:
        return mu_to_rating(self._engine.pool.get_or_create(player_id).mu)

    def _start_new_period(self, start_date: date | None = None):
        if start_date is None:
            self._period_start = self._period_end
        else:
            self._period_start = start_date

        self._period_end = self._period_start + self._period_length
        self._current_period = RatingPeriod(None)
        debug(
            f"Started new Glicko period from {self._period_start} to {self._period_end}"
        )

    def set_current_date(self, current_date: date):
        if self._period_end is not None and current_date < self._period_end:
            return

        if self._period_end is None:
            # Start the very first period
            self._start_new_period(current_date)
            return

        # Process pending updates for the current period
        self._engine.process_period(self._current_period)

        inactive_periods = int((current_date - self._period_end) / self._period_length)
        if inactive_periods >= 1:
            warning(
                f"Adjusting rating deviations following {inactive_periods} "
                f"inactive periods since the last period ended on {self._period_end} "
                f"before starting a new period from {current_date}"
            )

            # Create a new empty period and process it once for each inactive period
            empty_period = RatingPeriod(None)
            for _ in range(inactive_periods):
                self._engine.process_period(empty_period)

            # Start a new period from the current date
            self._start_new_period(current_date)
        else:
            # Start a new period immediately after the current one
            self._start_new_period()

    def add_result(self, winner_id: int, loser_id: int, games_ratio: float = 1.0):
        if self._current_period is None:
            raise GlickPeriodNotStartedError()

        # The library expects a score between 0 and 1 representing the match score
        # from the perspective of the first player, where 0 means the first player
        # lost, 0.5 means a draw, and 1 means the first player won. The formula
        # below converts the games ratio to a number > 0.5 and <= 1. For instance,
        # a 6-0 6-0 win gets a score of 1, whereas a 0-6 0-6 7-6 7-6 7-6 match
        # (with games ratio = 0.411) gets a score of 0.7055.
        score = 0.5 * games_ratio + 0.5

        self._current_period.add_match(MatchResult(winner_id, loser_id, score))
