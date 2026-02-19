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
    Combines matchup and synergy with configurable weights.
    """
    matchup = pairwise_score(team_a, team_b)
    synergy = synergy_score(team_a) - synergy_score(team_b)
    return W1_MATCHUP * matchup + W2_SYNERGY * synergy
