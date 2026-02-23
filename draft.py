"""Draft loop: run_draft(), get_human_pick(), main."""
from data_loader import full_hero_pool
from hero_mappings import HERO_ID_MAPPINGS
from minimax import TURN_ORDER, TEAM_A, TEAM_B, computer_pick, computer_ban
from evaluator import evaluate

NUM_PICKS = 12


def _format_team(picks):
    return [HERO_ID_MAPPINGS.get(h, str(h)) for h in picks]


def get_human_pick(available_heroes):
    """Show available heroes and prompt until valid choice."""
    available = sorted(available_heroes)
    names = [f"{hid}: {HERO_ID_MAPPINGS.get(hid, str(hid))}" for hid in available]
    print("\nAvailable heroes:")
    for line in names:
        print(f"  {line}")
    while True:
        raw = input("Enter hero ID or name for Team B: ").strip()
        # Try as ID first
        try:
            choice_id = int(raw)
            if choice_id in available_heroes:
                return choice_id
        except ValueError:
            pass
        # Try match by name (case-insensitive)
        raw_lower = raw.lower()
        for hid in available_heroes:
            if HERO_ID_MAPPINGS.get(hid, "").lower() == raw_lower:
                return hid
        print("Invalid pick; choose from the available list (ID or name).")


def get_human_ban(available_heroes):
    """Show available heroes and prompt until valid ban choice."""
    available = sorted(available_heroes)
    names = [f"{hid}: {HERO_ID_MAPPINGS.get(hid, str(hid))}" for hid in available]
    print("\nAvailable heroes to ban:")
    for line in names:
        print(f"  {line}")
    while True:
        raw = input("Enter hero ID or name for Team B to ban: ").strip()
        try:
            choice_id = int(raw)
            if choice_id in available_heroes:
                return choice_id
        except ValueError:
            pass
        raw_lower = raw.lower()
        for hid in available_heroes:
            if HERO_ID_MAPPINGS.get(hid, "").lower() == raw_lower:
                return hid
        print("Invalid ban; choose from the available list (ID or name).")


def run_draft():
    """Run the full 12-pick draft with bans: computer Team A, human Team B."""
    print("Welcome to the draft!")
    team_a_picks = []
    team_b_picks = []
    available_heroes = set(full_hero_pool)

    # --- Phase 1 bans: one ban per team before any picks ---
    print("\n--- Phase 1 bans (before picks) ---")
    print("Team A bans first, then Team B.")
    ban_a1 = computer_ban(team_a_picks, team_b_picks, available_heroes, phase=1)
    print(f"Team A bans {HERO_ID_MAPPINGS.get(ban_a1, ban_a1)}.")
    available_heroes.discard(ban_a1)
    print("Team B's turn to ban.")
    ban_b1 = get_human_ban(available_heroes)
    print(f"Team B bans {HERO_ID_MAPPINGS.get(ban_b1, ban_b1)}.")
    available_heroes.discard(ban_b1)

    # --- Picks 1–6 (same order: A, B, B, A, A, B) ---
    for turn_index in range(6):
        current_team = TURN_ORDER[turn_index]

        if current_team == TEAM_A:
            hero = computer_pick(team_a_picks, team_b_picks, available_heroes, turn_index)
            print(f"\nComputer picks {HERO_ID_MAPPINGS.get(hero, hero)} for Team A.")
            team_a_picks.append(hero)
        else:
            print("\n--- Current draft ---")
            print("Team A:", _format_team(team_a_picks))
            print("Team B:", _format_team(team_b_picks))
            print("Team B's turn to pick.")
            hero = get_human_pick(available_heroes)
            print(f"Human picks {HERO_ID_MAPPINGS.get(hero, hero)} for Team B.")
            team_b_picks.append(hero)

        available_heroes.discard(hero)
        print("Team A:", _format_team(team_a_picks))
        print("Team B:", _format_team(team_b_picks))

    # --- Phase 2 bans: one ban per team after both have 3 heroes ---
    print("\n--- Phase 2 bans (after 3 picks each) ---")
    print("Team B bans first, then Team A.")
    print("Team B's turn to ban.")
    ban_b2 = get_human_ban(available_heroes)
    print(f"Team B bans {HERO_ID_MAPPINGS.get(ban_b2, ban_b2)}.")
    available_heroes.discard(ban_b2)
    ban_a2 = computer_ban(team_a_picks, team_b_picks, available_heroes, phase=2)
    print(f"Team A bans {HERO_ID_MAPPINGS.get(ban_a2, ban_a2)}.")
    available_heroes.discard(ban_a2)

    # --- Picks 7–12 (same order: B, A, A, B, B, A) ---
    for turn_index in range(6, NUM_PICKS):
        current_team = TURN_ORDER[turn_index]

        if current_team == TEAM_A:
            hero = computer_pick(team_a_picks, team_b_picks, available_heroes, turn_index)
            print(f"\nComputer picks {HERO_ID_MAPPINGS.get(hero, hero)} for Team A.")
            team_a_picks.append(hero)
        else:
            print("\n--- Current draft ---")
            print("Team A:", _format_team(team_a_picks))
            print("Team B:", _format_team(team_b_picks))
            print("Team B's turn to pick.")
            hero = get_human_pick(available_heroes)
            print(f"Human picks {HERO_ID_MAPPINGS.get(hero, hero)} for Team B.")
            team_b_picks.append(hero)

        available_heroes.discard(hero)
        print("Team A:", _format_team(team_a_picks))
        print("Team B:", _format_team(team_b_picks))

    print("\n========== Final draft ==========")
    print("Team A:", _format_team(team_a_picks))
    print("Team B:", _format_team(team_b_picks))
    final_score = evaluate(team_a_picks, team_b_picks)
    print(f"Final evaluation score (positive = favorable to Team A): {final_score:.2f}")


if __name__ == "__main__":
    run_draft()
