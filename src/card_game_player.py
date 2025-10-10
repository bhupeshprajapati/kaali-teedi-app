
#!/usr/bin/env python3
"""
kali_teedi.py
Prototype OOP implementation for a turn-based Kali Teedi style card game.
- Max players: 15
- One or more decks supported via Deck(num_decks=...)
- Room codes: unique 6-character alphanumeric
- Scores saved to JSON by default; MySQL storage class provided as a stub
- CLI flow: create room -> join players -> set points -> play rounds -> scoreboard
"""

import random
import string
import json
import os
from typing import List, Dict, Optional, Tuple
import card_game

# -----------------------------
# Player
# -----------------------------

class Player:
    def __init__(self, player_id: str, display_name: Optional[str] = None):
        self.player_id = player_id
        self.display_name = display_name or player_id
        self.hand: List[card_game.Card] = []
        self.score: int = 0  # cumulative across rounds in a game
        self.in_round: bool = True  # used for round flow

    def take_cards(self, cards: List[card_game.Card]):
        self.hand.extend(cards)

    def play_card(self) -> Optional[card_game.Card]:
        """Pop and return one card from hand (simple behavior). Replace with UI/choice logic later."""
        if not self.hand:
            return None
        return self.hand.pop(0)

    def reset_for_round(self):
        self.hand = []
        self.in_round = True

    def __repr__(self):
        return f"<Player {self.display_name} ({self.player_id}) score={self.score} cards={len(self.hand)}>"
