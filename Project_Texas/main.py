"""
main.py

Main entry point for running a single hand of Texas Hold'em using the core game modules.
Orchestrates game setup, card dealing, betting rounds, evaluation, and final result output.
"""
import random
from player import Player
from deck import build_deck, deal_to_players, deal_community_cards
from betting import assign_blinds, betting_round_preflop, betting_round_postflop
from evaluation import check_for_win, evaluate_showdown, in_hand_reset
from ui import print_board_state, print_community_cards

def main():
    """
    Main entry point for the Texas Hold'em game loop.
    Handles player creation, dealing, betting rounds, and showdowns.
    """
    # Create 2-9 player objects
    num_players = int(input("Enter the number of players (2-9): "))
    players = [Player(f"Player {i+1}") for i in range(num_players)]

    # For a given hand within the game
    hand_no = 1 
    dealer_position = 0
    while len(players) > 1:
        # If there is only 1 player left end the game
        if len(players) == 1:
            break

        # Start of new hand
        print("+++++++++++++")
        print("Hand: ", hand_no)
        print("+++++++++++++")
        hand_no += 1

        # Blinds 
        sb_amount = 10
        bb_amount = 20
        sb_index, bb_index, total_pot = assign_blinds(players, dealer_position, sb_amount, bb_amount)

        # Build and shuffle the deck
        deck = build_deck()
        random.shuffle(deck)

        # Deal hands to created players
        deal_to_players(deck, players)

        # Display each player's hand and stack
        for i, player in enumerate(players):
            role = ""
            if i == dealer_position:
                role += " (BTN)"
            if i == sb_index:
                role += " (SB)"
            if i == bb_index:
                role += " (BB)"
            print(f"{player}{role}")

        # Simulate a betting sequence
        community_cards = []

        print("\n--- Pre-Flop Betting ---")
        print_board_state(players, community_cards, total_pot)
        total_pot = betting_round_preflop(players, bb_index, total_pot, bb_amount)
        print(f"Pot after pre-flop: {total_pot}")
        if check_for_win(players):
            continue

        print("\n--- Flop ---")
        deal_community_cards(deck, "flop", community_cards)
        print_board_state(players, community_cards, total_pot)
        print_community_cards(community_cards)
        total_pot = betting_round_postflop(players, dealer_position, total_pot)
        print(f"Pot after flop: {total_pot}")
        if check_for_win(players):
            continue

        print("\n--- Turn ---")
        deal_community_cards(deck, "turn", community_cards)
        print_board_state(players, community_cards, total_pot)
        print_community_cards(community_cards)
        total_pot = betting_round_postflop(players, dealer_position, total_pot)
        print(f"Pot after turn: {total_pot}")
        if check_for_win(players):
            continue

        print("\n--- River ---")
        deal_community_cards(deck, "river", community_cards)
        print_board_state(players, community_cards, total_pot)
        print_community_cards(community_cards)
        total_pot = betting_round_postflop(players, dealer_position, total_pot)
        print(f"Pot after river: {total_pot}")
        if check_for_win(players):
            continue

        print(f"\nTotal pot: {total_pot}")

        # Allocating winnings to the winner(s) of a showdown
        winners = evaluate_showdown(players, community_cards)
        if len(winners) == 1:
            print(f"Winner is {winners[0].name}")
            winners[0].stack += total_pot
        else:
            print(f"Chopped pot between: {', '.join(w.name for w in winners)}")
            for w in winners:
                w.stack += total_pot // len(winners)

        # Updating players for those with a non-zero stack (who's in the next hand)
        for player in players:
            in_hand_reset(player)
        players = [p for p in players if p.in_hand]

        # Updating dealer position based on players left
        dealer_position = (dealer_position + 1) % len(players)

# Run the game setup
if __name__ == "__main__":
    main()