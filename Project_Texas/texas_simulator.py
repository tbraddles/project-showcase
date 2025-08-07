"""
Simulates a Texas Holdem game.
"""
# Initialising
import os
import sys
import pandas as pd
import numpy as np
import poker
import random
from poker import card
from poker.card import Card
from poker.hand import Combo, Hand
from itertools import combinations
from treys import Evaluator, Card as TreysCard

# Player class
class Player:
    def __init__(self, name, stack=1000):
        self.name = name
        self.stack = stack
        self.hand = []
        self.in_hand = True
        self.amount_in_pot = 0
        self.is_dealer = False
        self.is_smallblind = False
        self.is_bigblind = False

    def deal_cards(self, cards):
        self.hand = cards

    def check(self):
        pass

    def call(self, amount):
        if amount >= self.stack:
            self.all_in()
        else:
            self.stack -= amount

    def bet(self, amount):
        if amount > self.stack:
            raise ValueError(f"{self.name} doesn't have enough chips to bet {amount}")
        self.stack -= amount
        return amount
    
    def fold(self):
        self.in_hand = False

    def all_in(self):
        self.stack -= self.stack
        
    def option(self, current_bet):
        """
        Returns the current bet and whether this player has raised.
        """
        # Checks if player has already folded
        if not self.in_hand:
            return 0, False

        if current_bet == 0:
            print(f"{self.name}'s options: Check, Bet, Fold, All-In")
            player_choice = input("Player option: ")
            if player_choice == "Check":
                self.check()
                return 0, False
            elif player_choice == "Bet":
                amount = int(input("Bet size: "))
                self.bet(amount)
                return amount, True
            elif player_choice == "Fold":
                self.fold()
                return 0, False
            elif player_choice == "All-In":
                amount = self.stack
                self.all_in()
                return amount, True
        else:
            print(f"{self.name}'s options: Call ({current_bet}), Raise, Fold, All-In")
            player_choice = input("Player option: ")
            if player_choice == "Call":
                self.call(current_bet)
                return current_bet, False
            elif player_choice == "Raise":
                amount = int(input("Raise size: "))
                self.bet(amount)
                return amount, True
            elif player_choice == "Fold":
                self.fold()
                return 0, False
            elif player_choice == "All-In":
                amount = self.stack
                self.all_in()
                return amount, True

    def __str__(self):
        return f"{self.name} | Hand: {self.hand} | Stack: {self.stack}"

# Create a deck of cards
def build_deck():
    suits = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']  # 2 to Ace

    # Use a list comprehension to generate all 52 cards
    deck = [Card(rank + suit) for rank in ranks for suit in suits]
    return deck

# Deal hands to players
def deal_to_players(deck, players):
    for player in players:
        player.deal_cards([deck.pop(), deck.pop()])

# Allows players in a hand to bet pre flop
def betting_round_preflop(players, bb_index, total_pot, bb_amount):
    current_bet = bb_amount
    num_players = len(players)
    action_index = (bb_index + 1) % num_players  # UTG acts first
    last_raiser_index = action_index  # First to act is effectively last raiser at start

    players_still_in = [p for p in players if p.in_hand]

    while True:
        player = players[action_index]

        if player.in_hand and player.stack > 0:
            to_call = current_bet - player.amount_in_pot
            print(f"\n{player.name}'s turn. Current bet: {current_bet}. Pot: {total_pot}. You need to call: {to_call}")
            contribution, is_raise = player.option(to_call)

            player.amount_in_pot += contribution
            total_pot += contribution

            if is_raise and player.amount_in_pot > current_bet:
                current_bet = player.amount_in_pot
                last_raiser_index = action_index

        # Move to next player
        action_index = (action_index + 1) % num_players
        players_still_in = [p for p in players if p.in_hand]

        # If action returns to last raiser and everyone else is caught up, end betting
        if action_index == last_raiser_index and all(
            p.amount_in_pot == current_bet or not p.in_hand or p.stack == 0 for p in players_still_in
        ):
            break

    return total_pot

# Allows players in a hand to bet post flop
def betting_round_postflop(players, dealer_position, total_pot):
    current_bet = 0
    num_players = len(players)

    # Reset amount_in_pot for post-flop rounds
    for p in players:
        p.amount_in_pot = 0

    action_index = (dealer_position + 1) % num_players  # First to act post-flop
    last_raiser_index = action_index

    players_still_in = [p for p in players if p.in_hand]

    while True:
        player = players[action_index]

        if player.in_hand and player.stack > 0:
            to_call = current_bet - player.amount_in_pot
            print(f"\n{player.name}'s turn. Current bet: {current_bet}. Pot: {total_pot}. You need to call: {to_call}")
            contribution, is_raise = player.option(to_call)

            player.amount_in_pot += contribution
            total_pot += contribution

            if is_raise and player.amount_in_pot > current_bet:
                current_bet = player.amount_in_pot
                last_raiser_index = action_index

        # Move to next player
        action_index = (action_index + 1) % num_players
        players_still_in = [p for p in players if p.in_hand]

        # End betting when action returns to last raiser and all players are caught up
        if action_index == last_raiser_index and all(
            p.amount_in_pot == current_bet or not p.in_hand or p.stack == 0
            for p in players_still_in
        ):
            break

    return total_pot

# Deals community cards
def deal_community_cards(deck, stage, community_cards):
    if stage == "flop":
        for _ in range(3):
            community_cards.append(deck.pop())
    elif stage in ["turn", "river"]:
        community_cards.append(deck.pop())

def print_community_cards(community_cards):
    print("\nCommunity Cards: ", ' '.join(str(card) for card in community_cards))

# Reset in hand status for each new hand
def in_hand_reset(player):
    if player.stack > 0:
        player.in_hand = True
    if player.stack == 0:
        player.in_hand = False # If they went All-In and lost previous hand

# Checking for a player winning a hand (if everyone has folded)
def check_for_win(players):
    players_still_in = [p for p in players if p.in_hand]
    if len(players_still_in) == 1:
        return True
    else:
        return False

# Checking if hand is the best
def evaluate_showdown(players, community_cards):
    evaluator = Evaluator()
    best_score = None
    winners = []

    suit_map = {
        '♣': 'c',
        '♦': 'd',
        '♥': 'h',
        '♠': 's'
    }

    def convert_card(card):
        card_str = str(card)
        rank = card_str[:-1].upper()
        suit_unicode = card_str[-1]
        suit = suit_map.get(suit_unicode)
        return (rank + suit)

    board = [TreysCard.new(convert_card(str(c))) for c in community_cards]

    for player in players:
        if not player.in_hand:
            continue

        # Evaluates best 5-card hand for a player (lower score better)
        hand = [TreysCard.new(convert_card(str(c))) for c in player.hand]
        score = evaluator.evaluate(board, hand)  

        if best_score is None or score < best_score:
            best_score = score
            winners = [player]  # New best hand
        elif score == best_score:
            winners.append(player)  # Tie (chopped pot)

    return winners  # Returns a list of winning players (length 1 = clear winner; >1 = chopped)

# Assigning blinds based on dealer positioning
def assign_blinds(players, dealer_position, sb_amount, bb_amount):
    
    # Resetting player statuses
    for player in players:
        player.is_dealer = False
        player.is_smallblind = False
        player.is_bigblind = False

    sb_index = (dealer_position + 1) % len(players)
    bb_index = (dealer_position + 2) % len(players)

    dealer = players[dealer_position]
    dealer.is_dealer = True
    sb_player = players[sb_index]
    sb_player.is_smallblind = True
    bb_player = players[bb_index]
    bb_player.is_bigblind = True

    sb_contribution = min(sb_amount, sb_player.stack)
    bb_contribution = min(bb_amount, bb_player.stack)

    sb_player.stack -= sb_contribution
    sb_player.current_bet = sb_contribution
    sb_player.amount_in_pot = sb_contribution

    bb_player.stack -= bb_contribution
    bb_player.current_bet = bb_contribution
    bb_player.amount_in_pot = bb_contribution

    pot = sb_contribution + bb_contribution
    return sb_index, bb_index, pot

# Prints the board state
def print_board_state(players, community_cards, pot):
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

# Main function to set up and play
def main():
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

        # Step 1: Build and shuffle the deck
        deck = build_deck()
        random.shuffle(deck)

        # Step 2: Deal hands to created players
        deal_to_players(deck, players)

        # Step 3: Display each player's hand and stack
        for i, player in enumerate(players):
            role = ""
            if i == dealer_position:
                role += " (BTN)"
            if i == sb_index:
                role += " (SB)"
            if i == bb_index:
                role += " (BB)"
            print(f"{player}{role}")

        # Step 4: Simulate a betting sequence
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

        # Step 5: Allocating winnings to the winner(s) of a showdown
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