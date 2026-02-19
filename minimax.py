"""Minimax with alpha-beta pruning; computer_pick for Team A."""
import math
import sys

from evaluator import evaluate

# Team A = computer (maximizing), Team B = human (minimizing)
TEAM_A = "A"
TEAM_B = "B"

# 12 picks: A, B, B, A, A, B, B, A, A, B, B, A
TURN_ORDER = [TEAM_A, TEAM_B, TEAM_B, TEAM_A, TEAM_A, TEAM_B, TEAM_B, TEAM_A, TEAM_A, TEAM_B, TEAM_B, TEAM_A]
NUM_PICKS = 12

# Depth limit: stop expanding after this many plies (1 ply = 1 pick). Start with 3 to keep it fast.
MAX_DEPTH = 5

# Debug: node visit counter (increments every minimax call)
_minimax_nodes = 0
_DEBUG_PRINT_EVERY = 50_000  # print progress every N nodes


def minimax(team_a_picks, team_b_picks, available_heroes, turn_index, alpha, beta, depth):
    """
    Minimax with alpha-beta. Returns evaluation score from Team A's perspective.
    Stops at depth=0 or when turn_index==12 (game over).
    """
    global _minimax_nodes
    _minimax_nodes += 1
    if _minimax_nodes % _DEBUG_PRINT_EVERY == 0:
        print(f"  [minimax] nodes={_minimax_nodes}, turn={turn_index}, depth={depth}", flush=True)
        sys.stdout.flush()

    if depth == 0 or turn_index == NUM_PICKS:
        return evaluate(team_a_picks, team_b_picks)

    current_team = TURN_ORDER[turn_index]
    available = list(available_heroes)

    if current_team == TEAM_A:
        best = -math.inf
        for hero in available:
            new_a = team_a_picks + [hero]
            new_available = available_heroes - {hero}
            score = minimax(new_a, team_b_picks, new_available, turn_index + 1, alpha, beta, depth - 1)
            best = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = math.inf
        for hero in available:
            new_b = team_b_picks + [hero]
            new_available = available_heroes - {hero}
            score = minimax(team_a_picks, new_b, new_available, turn_index + 1, alpha, beta, depth - 1)
            best = min(best, score)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best


def computer_pick(team_a_picks, team_b_picks, available_heroes, turn_index):
    """Choose best hero for Team A at this turn."""
    global _minimax_nodes
    _minimax_nodes = 0
    available_list = sorted(available_heroes)
    n = len(available_list)
    print(f"[computer_pick] evaluating {n} heroes (turn {turn_index + 1}/{NUM_PICKS})...", flush=True)
    best_score = -math.inf
    best_hero = None
    for i, hero in enumerate(available_list):
        print(f"  trying hero {i + 1}/{n} (id={hero})...", flush=True)
        sys.stdout.flush()
        new_a = team_a_picks + [hero]
        new_available = available_heroes - {hero}
        score = minimax(new_a, team_b_picks, new_available, turn_index + 1, -math.inf, math.inf, MAX_DEPTH)
        if score > best_score:
            best_score = score
            best_hero = hero
    print(f"[computer_pick] done. nodes={_minimax_nodes}, best_hero={best_hero}", flush=True)
    return best_hero
