"""
betting.py

Implements the logic for assigning blinds and managing betting rounds (pre-flop and post-flop).
Handles chip deductions, turn order, fold/call/raise actions, and pot tracking.
"""

def assign_blinds(players, dealer_position, sb_amount, bb_amount):
    """
    Assigns dealer, small blind, and big blind positions. Deducts chips.

    Args:
        players (list): List of players.
        dealer_position (int): Index of the dealer.
        sb_amount (int): Small blind value.
        bb_amount (int): Big blind value.
    Returns:
        tuple: (sb_index, bb_index, pot) after blind contributions.
    """
    
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

def betting_round_preflop(players, bb_index, total_pot, bb_amount):
    """
    Conducts the pre-flop betting round.

    Args:
        players (list): List of Player objects.
        bb_index (int): Index of big blind.
        total_pot (int): Current total pot value.
        bb_amount (int): Big blind amount.
    Returns:
        int: Updated pot size after betting.
    """
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

def betting_round_postflop(players, dealer_position, total_pot):
    """
    Conducts betting for flop, turn, or river rounds.

    Args:
        players (list): List of Player objects.
        dealer_position (int): Index of current dealer.
        total_pot (int): Current total pot.
    Returns:
        int: Updated pot size after betting.
    """
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