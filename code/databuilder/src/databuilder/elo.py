"""

Elo ratings for a set of players.
"""

from __future__ import annotations

from collections import defaultdict

INITIAL_ELO_RATING = 1500
ELO_SCALE_CONSTANT = 400


class InvalidScoreFactorError(Exception):
    """
    Raised when the score factor is not between 0 and 1.
    """

    def __init__(self, score_factor: float):
        self.score_factor = score_factor

    def __str__(self):
        return f"Invalid score factor: {self.score_factor}"


class EloRatings:
    """
    Elo ratings for a set of players.
    """

    def __init__(self):
        self._player: defaultdict[int, Player] = defaultdict(Player)

    def get_rating(self, player_id: int) -> float:
        return self._player[player_id].elo

    def add_result(self, winner_id: int, loser_id: int, score_factor: float = 1.0):
        winner = self._player[winner_id]
        loser = self._player[loser_id]

        winner_elo = winner.elo
        loser_elo = loser.elo

        winner.add_win(loser_elo, score_factor)
        loser.add_loss(winner_elo, score_factor)


class Player:
    """
    A tennis player.
    """

    def __init__(self):
        self.elo = INITIAL_ELO_RATING
        self._num_matches = 0

    def add_win(self, opponent_elo: float, score_factor: float = 1.0):
        self._update_elo(opponent_elo, 1, score_factor)

    def add_loss(self, opponent_elo: float, score_factor: float = 1.0):
        self._update_elo(opponent_elo, 0, score_factor)

    def _update_elo(
        self,
        opponent_elo: float,
        winner_indicator: float,
        score_factor: float = 1.0,
    ):
        if score_factor < 0 or score_factor > 1:
            raise InvalidScoreFactorError(score_factor)

        self._num_matches += 1

        win_prob = 1 / (1 + 10 ** ((opponent_elo - self.elo) / ELO_SCALE_CONSTANT))

        # The scale factor is based on the number of matches the player has played,
        # according to a formula suggested by Kovalchik in a paper from 2016
        scale_factor = 250 / (self._num_matches + 5) ** 0.4

        self.elo += scale_factor * (winner_indicator - win_prob) * score_factor
