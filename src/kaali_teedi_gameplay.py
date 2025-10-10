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

    def start_game(self, deck_count: int = 1) -> 'Game':
            if self.game and not self.game.finished:
                raise RuntimeError("Game already in progress in this room.")
            if len(self.players) < 2:
                raise RuntimeError("Need at least 2 players to start.")
            self.game = Game(room=self, deck_count=deck_count, points_rules=self.points_rules)
            print(f"[Room] Game started in room {self.room_code} with {len(self.players)} players.")
            return self.game
    

class Game:
    """
    Game orchestrates multiple rounds. Each round deals cards and plays until all players have no cards.
    Scoring is computed per-round and accumulated.
    """

    def __init__(self, room: Room, deck_count: int = 1, points_rules: Optional[Dict] = None):
        self.room = room
        self.deck_count = max(1, deck_count)
        self.deck = card_game.Deck(num_decks=self.deck_count)
        self.points_rules = points_rules or {"points_per_remaining_card": 1}
        self.round_number = 0
        self.finished: bool = False
        self.round_history: List[Dict] = []  # store per-round results
        # Copy players into game context
        self.players: List[card_game_player.Player] = list(room.players.values())

    def _deal_all_cards_equally(self):
        """Distribute deck cards equally to all players (leftover cards remain undistributed)."""
        n_players = len(self.players)
        cards_each = self.deck.remaining() // n_players if n_players else 0
        for p in self.players:
            cards = self.deck.draw(cards_each)
            p.take_cards(cards)
        print(f"[Game] Dealt {cards_each} cards to each player. Deck remaining: {self.deck.remaining()}")

    def play_round(self):
        """Play a single round: deal, then simulate turns until all hands empty.
           Replace the play logic with the real game rules as needed."""
        # Prepare round
        self.round_number += 1
        for p in self.players:
            p.reset_for_round()
        # Rebuild and shuffle deck for each round (common in many card games)
        self.deck = card_game.Deck(num_decks=self.deck_count)
        self.deck.shuffle()
        self._deal_all_cards_equally()

        print(f"--- Starting Round {self.round_number} ---")
        # Simple turn-based loop: each player plays the top card each turn until all hands empty
        turn_index = 0
        active_players = [p for p in self.players if p.hand]
        play_sequence = []  # record tuples (player_id, card)
        while any(p.hand for p in self.players):
            current_player = self.players[turn_index % len(self.players)]
            if current_player.hand:
                card = current_player.play_card()
                play_sequence.append((current_player.player_id, str(card)))
                # In real rules: evaluate play, handle trick or win conditions
            turn_index += 1

        # Determine round results (placeholder: decide winner randomly or by custom logic)
        # >>> REPLACE the logic below with the actual Kali Teedi round winner calculation <<<
        # For now: we pick a random winner among players and penalize others based on remaining cards (which are 0 here).
        # Instead we'll compute "penalty" as number of cards played by player modulo something to illustrate scoring.
        # A more sensible example: penalize by number of cards originally dealt (example).
        original_cards_dealt = {p.player_id: 0 for p in self.players}
        # For our equal-deal logic above, compute that each player got the same number
        if self.players:
            equal_cards = (self.deck_count * 52) // len(self.players)
            for p in self.players:
                original_cards_dealt[p.player_id] = equal_cards

        # Example scoring rule (simple): each player's penalty = original_cards_dealt * points_per_remaining_card
        scoreboard_delta = {}
        for p in self.players:
            penalty = original_cards_dealt[p.player_id] * self.points_rules.get("points_per_remaining_card", 1)
            scoreboard_delta[p.player_id] = -penalty  # lose points
            p.score += scoreboard_delta[p.player_id]

        # Award the "round winner" some points (just pick one randomly for example)
        winner = random.choice(self.players)
        winner_bonus = self.points_rules.get("winner_bonus", sum(abs(v) for v in scoreboard_delta.values()))
        scoreboard_delta[winner.player_id] = scoreboard_delta.get(winner.player_id, 0) + winner_bonus
        winner.score += winner_bonus

        # Save history and return
        round_result = {
            "round": self.round_number,
            "play_sequence": play_sequence,
            "delta": scoreboard_delta,
            "scores_after_round": {p.player_id: p.score for p in self.players},
            "winner": winner.player_id
        }
        self.round_history.append(round_result)
        print(f"[Game] Round {self.round_number} finished. Winner: {winner.player_id}")
        return round_result

    def get_scoreboard(self) -> List[Tuple[str, str, int]]:
        """Return list of (player_id, display_name, cumulative_score) sorted by score desc."""
        board = sorted([(p.player_id, p.display_name, p.score) for p in self.players],
                       key=lambda x: x[2], reverse=True)
        return board

    def is_game_over(self) -> bool:
        """You can define game over condition; here we leave it to caller or when deck cannot deal further."""
        # Sample condition: if deck leftover is less than number of players, not enough for a new round
        return self.deck.remaining() < len(self.players)


    

