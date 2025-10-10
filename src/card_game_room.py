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
import card_game_storage
import card_game_player

# -----------------------------
# Game & Room
# -----------------------------



class Room:
    """Represents a lobby/room that can hold up to 15 players."""
    MAX_PLAYERS = 15

    def __init__(self, host_player_id: str, room_code: Optional[str] = None, max_players: int = MAX_PLAYERS):
        self.room_code = room_code or card_game.gen_room_code()
        self.host_player_id = host_player_id
        self.max_players = min(max_players, self.MAX_PLAYERS)
        self.players: Dict[str, card_game_player.Player] = {}  # player_id -> Player
        self.game: Optional[Game] = None
        self.points_rules: Dict = {}  # customizable points settings
        print(f"[Room] Created room {self.room_code} (host={host_player_id})")

    def add_player(self, player: card_game_player.Player) -> bool:
        if len(self.players) >= self.max_players:
            print("[Room] Add player failed: room full")
            return False
        if player.player_id in self.players:
            print("[Room] Player already in room")
            return False
        self.players[player.player_id] = player
        print(f"[Room] Player {player.player_id} joined ({len(self.players)}/{self.max_players})")
        return True

    def remove_player(self, player_id: str) -> bool:
        if player_id in self.players:
            del self.players[player_id]
            print(f"[Room] Player {player_id} removed")
            return True
        return False

    def list_players(self) -> List[card_game_player.Player]:
        return list(self.players.values())

    def set_points_rules(self, rules: Dict):
        """Example rules: {"points_per_penalty_card": 1} or more complex rules"""
        self.points_rules = rules
        print(f"[Room] Points rules set: {rules}")

    