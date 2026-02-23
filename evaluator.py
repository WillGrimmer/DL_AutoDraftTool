"""Leaf evaluator: pairwise matchups + synergy, combined into one scalar for the maximizing player."""
from data_loader import (
    pairwise_matrix,
    combo_matrix,
    get_pairwise_winrate,
    get_combo_winrate,
)

# Tuning: how much to trust matchup vs synergy data. Must sum to 1.0 (or scale as you like).
# Valuing combos more: synergy has higher weight.
W1_MATCHUP = 0.4
W2_SYNERGY = 0.6


def pairwise_score(team_a, team_b):
    """Expected win rate of team A vs team B, averaging across all cross-team matchups."""
    if not team_a or not team_b:
        return 0.5
    total = 0.0
    for a in team_a:
        for b in team_b:
            total += get_pairwise_winrate(pairwise_matrix, a, b)
    return total / (len(team_a) * len(team_b))


def synergy_score(team):
    """Average pairwise synergy (win rate when these heroes are together) for all pairs on the team."""
    if len(team) < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for i in range(len(team)):
        for j in range(i + 1, len(team)):
            total += get_combo_winrate(combo_matrix, team[i], team[j])
            pairs += 1
    return total / pairs if pairs > 0 else 0.0


def evaluate(team_a, team_b):
    """
    Single scalar score from the perspective of the maximizing player (Team A).
    Zero = even; positive = Team A favored, negative = Team B favored.
    Combines matchup (centered so 0.5 = even) and synergy difference.
    Matchup term is scaled by 2 so that clear imbalances (e.g. 0.3 vs 0.7) produce
    a noticeable score instead of clustering near zero.
    """
    matchup = pairwise_score(team_a, team_b)  # A's win rate vs B, in [0, 1]
    synergy = synergy_score(team_a) - synergy_score(team_b)
    # Center and scale: 2 * (matchup - 0.5) is in [-1, 1], so term in [-W1, W1]
    return W1_MATCHUP * 2 * (matchup - 0.5) + W2_SYNERGY * synergy
