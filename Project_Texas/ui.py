"""
ui.py

Handles all text-based output to the console, including displaying community cards,
player states, and the pot during gameplay.
Designed to be swapped out later for a GUI or web frontend if needed.
"""

def print_board_state(players, community_cards, pot):
    """
    Displays the current state of the game board with player info.

    Args:
        players (list): All players.
        community_cards (list): Cards on the board.
        pot (int): Current pot value.
    """
    # Define fixed positions for up to 9 players
    seat_positions = [
        4, 0, 1,
        3,   8,  # Mid level
        2, 7, 6, 5
    ]

    display_slots = [''] * 9
    for i, player in enumerate(players):
        display = f"{player.name} (${player.stack})"
        if player.is_dealer:
            display += " [D]"
        if player.is_smallblind:
            display += " [SB]"
        if player.is_bigblind:
            display += " [BB]"
        if not player.in_hand:
            display += " (Folded)"
        display_slots[seat_positions[i]] = display

    def format_center(text):
        return f"{text:^60}"

    # Convert community cards to display string
    community_str = ' '.join(str(card) for card in community_cards) if community_cards else "---"

    print("=" * 60)
    print(format_center(display_slots[0]))
    print(f"{display_slots[1]:<25}{' ' * 10}{display_slots[2]:>25}")
    print()
    print(f"{display_slots[3]:<15}{' ' * 30}{display_slots[4]:>15}")
    print(format_center("╭" + "─" * 38 + "╮"))
    print(format_center("│" + f"  Board: {community_str}".ljust(38) + "│"))
    print(format_center("│" + f"  Pot: ${pot}".ljust(38) + "│"))
    print(format_center("╰" + "─" * 38 + "╯"))
    print(f"{display_slots[5]:<15}{' ' * 30}{display_slots[6]:>15}")
    print()
    print(f"{display_slots[7]:<25}{' ' * 10}{display_slots[8]:>25}")
    print(format_center(""))
    print("=" * 60)

def print_community_cards(community_cards):
    """
    Displays the community cards in the terminal.

    Args:
        community_cards (list): Community cards to show.
    """
    print("\nCommunity Cards: ", ' '.join(str(card) for card in community_cards))