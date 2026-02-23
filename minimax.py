"""Minimax with alpha-beta pruning; computer_pick for Team A.

Optimizations over baseline:
  1. Move ordering  — sort candidates by fast heuristic before recursing,
                      so alpha-beta prunes much more aggressively.
  2. Transposition table — cache (frozenset_a, frozenset_b, turn_index) -> score
                           so identical states reached via different pick orders
                           are not re-evaluated.
  3. Beam search fallback — at wide early turns, only keep the top-K candidates
                            instead of all remaining heroes (trades optimality for speed).
  4. Correct depth budget in computer_pick — the root expansion counts as 1 ply,
                                              so sub-calls get MAX_DEPTH-1.
"""
import math
import sys
from functools import lru_cache

from evaluator import evaluate, pairwise_score, synergy_score

# Team A = computer (maximizing), Team B = human (minimizing)
TEAM_A = "A"
TEAM_B = "B"

# 12 picks: A, B, B, A, A, B, B, A, A, B, B, A
TURN_ORDER = [TEAM_A, TEAM_B, TEAM_B, TEAM_A, TEAM_A, TEAM_B, TEAM_B, TEAM_A, TEAM_A, TEAM_B, TEAM_B, TEAM_A]
NUM_PICKS = 12

# --- Depth / beam tuning ---
# At depth 12 with 38 heroes this is intractable without beam search.
# MAX_DEPTH=6 + BEAM_WIDTH=8 gives a good balance of quality and speed.
# Set BEAM_WIDTH=None to disable beam search (exact alpha-beta only).
MAX_DEPTH = 8
BEAM_WIDTH = 12   # only explore the top-K heroes at each node; None = no beam

# Debug counters
_minimax_nodes = 0
_DEBUG_PRINT_EVERY = 100_000

# Transposition table: maps (a_tuple, b_tuple, turn_index) -> score
# Using sorted tuples so different insertion orders hash the same.
_trans_table: dict = {}
_trans_hits = 0


# ---------------------------------------------------------------------------
# Move ordering heuristic  (fast, no recursion)
# ---------------------------------------------------------------------------

def _hero_quick_score(hero, team_a, team_b, is_maximizing):
    """
    Cheap single-hero score used only to ORDER moves before recursing.
    Does NOT need to be accurate — just good enough to put promising
    heroes near the front so alpha-beta prunes more.
    """
    if is_maximizing:
        # How well does hero counter enemy + synergize with own team?
        matchup = pairwise_score([hero], team_b) if team_b else 0.5
        syn     = synergy_score(team_a + [hero]) if team_a else 0.0
        return matchup + syn
    else:
        # Minimizing: enemy wants hero that counters team_a and synergizes with team_b
        matchup = pairwise_score(team_a, [hero]) if team_a else 0.5
        syn     = synergy_score(team_b + [hero]) if team_b else 0.0
        return -(matchup + syn)   # negate so sort descending works uniformly


def _order_moves(heroes, team_a, team_b, is_maximizing):
    """Return heroes sorted best-first for the current player."""
    scored = [(h, _hero_quick_score(h, team_a, team_b, is_maximizing)) for h in heroes]
    scored.sort(key=lambda x: x[1], reverse=True)   # descending = best first
    candidates = [h for h, _ in scored]
    if BEAM_WIDTH is not None:
        candidates = candidates[:BEAM_WIDTH]
    return candidates


# ---------------------------------------------------------------------------
# Core minimax
# ---------------------------------------------------------------------------

def minimax(team_a_picks, team_b_picks, available_heroes, turn_index, alpha, beta, depth):
    """
    Minimax with alpha-beta + transposition table + move ordering.
    Returns evaluation score from Team A's perspective.
    """
    global _minimax_nodes, _trans_hits
    _minimax_nodes += 1
    if _minimax_nodes % _DEBUG_PRINT_EVERY == 0:
        print(f"  [minimax] nodes={_minimax_nodes}, turn={turn_index}, depth={depth}, "
              f"trans_hits={_trans_hits}", flush=True)

    # Terminal / depth-limit
    if depth == 0 or turn_index == NUM_PICKS:
        return evaluate(team_a_picks, team_b_picks)

    # Transposition lookup (use sorted tuples so order doesn't matter)
    t_key = (tuple(sorted(team_a_picks)), tuple(sorted(team_b_picks)), turn_index)
    if t_key in _trans_table:
        _trans_hits += 1
        return _trans_table[t_key]

    current_team = TURN_ORDER[turn_index]
    is_max = current_team == TEAM_A

    # Order moves (and optionally beam-prune)
    ordered = _order_moves(list(available_heroes), team_a_picks, team_b_picks, is_max)

    if is_max:
        best = -math.inf
        for hero in ordered:
            new_a = team_a_picks + [hero]
            score = minimax(new_a, team_b_picks, available_heroes - {hero},
                            turn_index + 1, alpha, beta, depth - 1)
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if beta <= alpha:
                break
    else:
        best = math.inf
        for hero in ordered:
            new_b = team_b_picks + [hero]
            score = minimax(team_a_picks, new_b, available_heroes - {hero},
                            turn_index + 1, alpha, beta, depth - 1)
            if score < best:
                best = score
            if best < beta:
                beta = best
            if beta <= alpha:
                break

    _trans_table[t_key] = best
    return best


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def computer_pick(team_a_picks, team_b_picks, available_heroes, turn_index, pick_for_team_a=True):
    """
    Choose best hero for the given team at this turn using minimax.
    pick_for_team_a=True: pick for Team A (first picker, maximizing).
    pick_for_team_a=False: pick for Team B (second picker, minimizing).
    """
    global _minimax_nodes, _trans_hits
    _minimax_nodes = 0
    _trans_hits = 0
    _trans_table.clear()

    available_list = sorted(available_heroes)
    n = len(available_list)
    side = "A" if pick_for_team_a else "B"
    print(f"[computer_pick] Team {side}, evaluating {n} heroes (turn {turn_index + 1}/{NUM_PICKS}), "
          f"MAX_DEPTH={MAX_DEPTH}, BEAM_WIDTH={BEAM_WIDTH}...", flush=True)

    root_candidates = _order_moves(available_list, team_a_picks, team_b_picks, is_maximizing=pick_for_team_a)

    if pick_for_team_a:
        best_score = -math.inf
        best_hero = None
        alpha = -math.inf
        for i, hero in enumerate(root_candidates):
            print(f"  trying hero {i + 1}/{len(root_candidates)} (id={hero})...", flush=True)
            sys.stdout.flush()
            new_a = team_a_picks + [hero]
            score = minimax(new_a, team_b_picks, available_heroes - {hero},
                            turn_index + 1, alpha, math.inf, MAX_DEPTH - 1)
            if score > best_score:
                best_score = score
                best_hero = hero
            if best_score > alpha:
                alpha = best_score
    else:
        best_score = math.inf
        best_hero = None
        beta = math.inf
        for i, hero in enumerate(root_candidates):
            print(f"  trying hero {i + 1}/{len(root_candidates)} (id={hero})...", flush=True)
            sys.stdout.flush()
            new_b = team_b_picks + [hero]
            score = minimax(team_a_picks, new_b, available_heroes - {hero},
                            turn_index + 1, -math.inf, beta, MAX_DEPTH - 1)
            if score < best_score:
                best_score = score
                best_hero = hero
            if best_score < beta:
                beta = best_score

    print(f"[computer_pick] done. nodes={_minimax_nodes}, trans_hits={_trans_hits}, "
          f"best_hero={best_hero}, score={best_score:.4f}", flush=True)
    return best_hero


# ---------------------------------------------------------------------------
# Ban logic (Team A chooses which hero to ban)
# ---------------------------------------------------------------------------

def computer_ban(team_a_picks, team_b_picks, available_heroes, phase, ban_for_team_a=True):
    """
    Choose one hero for the given team to ban.
    ban_for_team_a=True: ban for Team A (first picker). Phase 1: ban 2nd best for us. Phase 2: ban what helps B most.
    ban_for_team_a=False: ban for Team B (second picker). Phase 1: ban what helps A most. Phase 2: ban what helps A most.
    """
    available_list = sorted(available_heroes)
    if not available_list:
        return None
    if ban_for_team_a:
        if phase == 1:
            scored = [(hero, evaluate([hero], [])) for hero in available_list]
            scored.sort(key=lambda x: x[1], reverse=True)
            if len(scored) < 2:
                return scored[0][0] if scored else None
            return scored[1][0]
        else:
            best_ban = None
            worst_score = math.inf
            for hero in available_list:
                score = evaluate(team_a_picks, team_b_picks + [hero])
                if score < worst_score:
                    worst_score = score
                    best_ban = hero
            return best_ban
    else:
        # Ban for Team B: remove what would help A most
        if phase == 1:
            best_ban = None
            best_score = -math.inf
            for hero in available_list:
                score = evaluate([hero], [])  # how good for A if A had this hero
                if score > best_score:
                    best_score = score
                    best_ban = hero
            return best_ban
        else:
            best_ban = None
            best_score = -math.inf
            for hero in available_list:
                score = evaluate(team_a_picks + [hero], team_b_picks)
                if score > best_score:
                    best_score = score
                    best_ban = hero
            return best_ban