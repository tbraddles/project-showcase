"""
evaluation.py

Contains functions to determine the outcome of a hand.
Includes win condition checks (e.g. only one player remaining) and showdown hand evaluation logic.
"""
from treys import Evaluator, Card as TreysCard

def check_for_win(players):
    """
    Checks if only one player remains in-hand (others folded).

    Args:
        players (list): List of players.
    Returns:
        bool: True if hand is over due to folding.
    """
    players_still_in = [p for p in players if p.in_hand]
    if len(players_still_in) == 1:
        return True
    else:
        return False

def evaluate_showdown(players, community_cards):
    """
    Determines winner(s) based on the best poker hand at showdown.

    Args:
        players (list): Players still in-hand.
        community_cards (list): Board cards.
    Returns:
        list: List of winning Player(s).
    """
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

def in_hand_reset(player):
    """
    Resets a player's in-hand status for the next hand.

    Args:
        player (Player): A player object.
    """
    if player.stack > 0:
        player.in_hand = True
    if player.stack == 0:
        player.in_hand = False # If they went All-In and lost previous hand