"""
player.py

Defines the Player class used to represent a participant in the Texas Hold'em game.
Also includes utility functions for managing player state between hands.
"""

class Player:
    """
    Represents a player in a Texas Hold'em poker game.
    
    Attributes:
        name (str): The name of the player.
        stack (int): The number of chips the player has.
        hand (list): The player's hole cards.
        in_hand (bool): Whether the player is currently in the hand.
        amount_in_pot (int): Total amount the player has committed this hand.
        is_dealer (bool): Whether this player is the dealer.
        is_smallblind (bool): Whether this player is the small blind.
        is_bigblind (bool): Whether this player is the big blind.
    """
    def __init__(self, name, stack=1000):
        """
        Initializes a new Player object.
        
        Args:
            name (str): Player name.
            stack (int, optional): Starting chip stack. Defaults to 1000.
        """
        self.name = name
        self.stack = stack
        self.hand = []
        self.in_hand = True
        self.amount_in_pot = 0
        self.is_dealer = False
        self.is_smallblind = False
        self.is_bigblind = False

    def deal_cards(self, cards):
        """
        Assigns two cards to the player's hand.

        Args:
            cards (list): A list of two Card objects.
        """
        self.hand = cards

    def check(self):
        """
        Placeholder for 'check' action. No chips are bet.
        """
        pass

    def call(self, amount):
        """
        Calls the current bet amount or goes all-in if insufficient chips.

        Args:
            amount (int): Amount to call.
        """
        if amount >= self.stack:
            self.all_in()
        else:
            self.stack -= amount

    def bet(self, amount):
        """
        Bets a specified amount, subtracting from stack.

        Args:
            amount (int): The number of chips to bet.
        Returns:
            int: The amount bet.
        Raises:
            ValueError: If the bet exceeds the player's stack.
        """
        if amount > self.stack:
            raise ValueError(f"{self.name} doesn't have enough chips to bet {amount}")
        self.stack -= amount
        return amount
    
    def fold(self):
        """
        Folds the player's hand, removing them from the round.
        """
        self.in_hand = False

    def all_in(self):
        """
        Goes all-in, betting all remaining chips.
        """
        self.stack -= self.stack
        
    def option(self, current_bet):
        """
        Presents betting options to the player based on game state.

        Args:
            current_bet (int): The amount the player must call to stay in.
        Returns:
            tuple: (amount_contributed (int), is_raise (bool))
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
        """
        Returns a readable string representation of the player.

        Returns:
            str: Player name, hand, and stack.
        """
        return f"{self.name} | Hand: {self.hand} | Stack: {self.stack}"