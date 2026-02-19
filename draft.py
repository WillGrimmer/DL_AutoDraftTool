"""Draft loop: run_draft(), get_human_pick(), main."""
from data_loader import full_hero_pool
from hero_mappings import HERO_ID_MAPPINGS
from minimax import TURN_ORDER, TEAM_A, TEAM_B, computer_pick
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


def run_draft():
    print("Welcome to the draft!")
    """Run the full 12-pick draft: computer Team A, human Team B."""
    team_a_picks = []
    team_b_picks = []
    available_heroes = set(full_hero_pool)

    for turn_index in range(NUM_PICKS):
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
