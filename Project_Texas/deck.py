"""
deck.py

Provides functionality for creating a deck, shuffling, and dealing cards to players 
and to the community board during each stage of the game.
"""
from poker.card import Card

def build_deck():
    """
    Builds a standard 52-card deck.

    Returns:
        list: A list of Card objects representing the deck.
    """
    suits = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']  # 2 to Ace

    # Generates all 52 cards
    deck = [Card(rank + suit) for rank in ranks for suit in suits]
    return deck

def deal_to_players(deck, players):
    """
    Deals two cards to each player from the deck.

    Args:
        deck (list): The shuffled deck.
        players (list): List of Player objects.
    """
    for player in players:
        player.deal_cards([deck.pop(), deck.pop()])

def deal_community_cards(deck, stage, community_cards):
    """
    Deals community cards based on the stage of the hand.

    Args:
        deck (list): Current deck.
        stage (str): One of "flop", "turn", or "river".
        community_cards (list): Current list of community cards.
    """
    if stage == "flop":
        for _ in range(3):
            community_cards.append(deck.pop())
    elif stage in ["turn", "river"]:
        community_cards.append(deck.pop())