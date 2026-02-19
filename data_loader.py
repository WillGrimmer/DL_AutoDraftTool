"""Load hero matchups and combos JSONs; build pairwise matrix and combo lookup."""
import json
from itertools import combinations
from pathlib import Path

from hero_mappings import HERO_ID_MAPPINGS

DATA_DIR = Path(__file__).resolve().parent / "data"
HERO_MATCHUPS_PATH = DATA_DIR / "hero_matchups.json"
COMBOS_PATH = DATA_DIR / "combos.json"

# Default winrate when no matchup data exists (neutral)
DEFAULT_WINRATE = 0.5


def load_pairwise_matrix():
    """Build pairwise_matrix[hero_a][hero_b] = wins / matches_played from hero_matchups.json."""
    with open(HERO_MATCHUPS_PATH, encoding="utf-8") as f:
        rows = json.load(f)
    matrix = {}
    for r in rows:
        hero_a = r["hero_id"]
        hero_b = r["enemy_hero_id"]
        wins = r["wins"]
        matches = r["matches_played"]
        if matches <= 0:
            continue
        if hero_a not in matrix:
            matrix[hero_a] = {}
        matrix[hero_a][hero_b] = wins / matches
    return matrix


def load_combo_lookup():
    """Build combo_lookup[frozenset(hero_ids)] = wins / matches from combos.json."""
    with open(COMBOS_PATH, encoding="utf-8") as f:
        rows = json.load(f)
    lookup = {}
    for r in rows:
        hero_ids = tuple(sorted(r["hero_ids"]))
        wins = r["wins"]
        matches = r["matches"]
        if matches <= 0:
            continue
        lookup[frozenset(hero_ids)] = wins / matches
    return lookup


def get_pairwise_winrate(matrix, hero_a, hero_b):
    """Return winrate of hero_a vs hero_b; DEFAULT_WINRATE if missing."""
    if hero_a not in matrix or hero_b not in matrix[hero_a]:
        return DEFAULT_WINRATE
    return matrix[hero_a][hero_b]


def build_combo_matrix(combo_lookup):
    """
    Build combo_matrix[i][j] = average win rate when heroes i and j are on the same team.
    Derived from 6-hero combo data: for each pair (i,j), average winrate of all combos
    containing both. Missing pairs use DEFAULT_WINRATE (0.5) so scale is comparable.
    """
    pair_sums = {}
    pair_counts = {}
    for key in combo_lookup:
        wr = combo_lookup[key]
        for i, j in combinations(key, 2):
            p = (min(i, j), max(i, j))
            pair_sums[p] = pair_sums.get(p, 0) + wr
            pair_counts[p] = pair_counts.get(p, 0) + 1
    matrix = {}
    for (i, j), s in pair_sums.items():
        avg = s / pair_counts[(i, j)]
        if i not in matrix:
            matrix[i] = {}
        if j not in matrix:
            matrix[j] = {}
        matrix[i][j] = matrix[j][i] = avg
    return matrix


def get_combo_winrate(matrix, hero_i, hero_j):
    """Return win rate when hero_i and hero_j are on the same team; 0.5 if missing."""
    if hero_i not in matrix or hero_j not in matrix[hero_i]:
        return DEFAULT_WINRATE
    return matrix[hero_i][hero_j]


def get_full_hero_pool():
    """Return the set of hero IDs that have data (matchups and/or combos)."""
    pool = set()
    for hero_a in pairwise_matrix:
        pool.add(hero_a)
        pool.update(pairwise_matrix[hero_a].keys())
    for key in combo_lookup:
        pool.update(key)
    # If no data loaded yet, use all mapped heroes
    if not pool:
        pool = set(HERO_ID_MAPPINGS.keys())
    return pool


# Load once at import for use by evaluator and minimax
pairwise_matrix = load_pairwise_matrix()
combo_lookup = load_combo_lookup()
combo_matrix = build_combo_matrix(combo_lookup)
full_hero_pool = get_full_hero_pool()
