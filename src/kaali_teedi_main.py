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

# -----------------------------
# Card / Deck / Utilities
# -----------------------------

SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

def gen_room_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank} of {self.suit}"


class Deck:
    def __init__(self, num_decks: int = 1, shuffle_on_create: bool = True):
        self.num_decks = max(1, int(num_decks))
        self.cards: List[Card] = []
        self._build()
        if shuffle_on_create:
            self.shuffle()

    def _build(self):
        self.cards = []
        for _ in range(self.num_decks):
            for suit in SUITS:
                for rank in RANKS:
                    self.cards.append(Card(rank, suit))

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, n: int = 1) -> List[Card]:
        drawn = []
        for _ in range(n):
            if not self.cards:
                break
            drawn.append(self.cards.pop(0))
        return drawn

    def remaining(self) -> int:
        return len(self.cards)


# -----------------------------
# Player
# -----------------------------

class Player:
    def __init__(self, player_id: str, display_name: Optional[str] = None):
        self.player_id = player_id
        self.display_name = display_name or player_id
        self.hand: List[Card] = []
        self.score: int = 0  # cumulative across rounds in a game
        self.in_round: bool = True  # used for round flow

    def take_cards(self, cards: List[Card]):
        self.hand.extend(cards)

    def play_card(self) -> Optional[Card]:
        """Pop and return one card from hand (simple behavior). Replace with UI/choice logic later."""
        if not self.hand:
            return None
        return self.hand.pop(0)

    def reset_for_round(self):
        self.hand = []
        self.in_round = True

    def __repr__(self):
        return f"<Player {self.display_name} ({self.player_id}) score={self.score} cards={len(self.hand)}>"

# -----------------------------
# Score storage: JSON + MySQL stub
# -----------------------------

class JSONScoreStorage:
    """Simple JSON-based storage for scores. Filename stored in same dir."""
    def __init__(self, filepath: str = "kali_scores.json"):
        self.filepath = filepath
        # Ensure file exists
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f:
                json.dump({}, f)

    def save_game_scores(self, room_code: str, scoreboard: Dict[str, int]):
        """
        scoreboard: dict player_id -> score
        """
        with open(self.filepath, "r") as f:
            db = json.load(f)
        db[room_code] = db.get(room_code, [])
        db[room_code].append({"scores": scoreboard})
        with open(self.filepath, "w") as f:
            json.dump(db, f, indent=2)
        print(f"[JSONStorage] Saved scores for room {room_code} to {self.filepath}")

    def load_room_scores(self, room_code: str) -> List[Dict]:
        with open(self.filepath, "r") as f:
            db = json.load(f)
        return db.get(room_code, [])


class MySQLScoreStorage:
    """
    Stubbed MySQL storage. To enable, install mysql-connector-python and provide connection params.
    This class demonstrates how to save scoreboard to relational DB.
    """
    def __init__(self, host: str, user: str, password: str, database: str):
        try:
            import mysql.connector
            self.mysql = mysql.connector
        except Exception as e:
            self.mysql = None
            print("[MySQLStorage] mysql.connector not available. Install 'mysql-connector-python' to enable.")

        self.config = {"host": host, "user": user, "password": password, "database": database}

    def save_game_scores(self, room_code: str, scoreboard: Dict[str, int]):
        if not self.mysql:
            raise RuntimeError("mysql.connector not available. Can't save to MySQL.")
        conn = self.mysql.connect(**self.config)
        cursor = conn.cursor()
        # Example simple schema: games (id, room_code, ts), scores (game_id, player_id, score)
        # You need to create tables beforehand - this is just a usage example.
        # Insert a game row
        cursor.execute("INSERT INTO games (room_code) VALUES (%s)", (room_code,))
        game_id = cursor.lastrowid
        # Insert scores
        for pid, score in scoreboard.items():
            cursor.execute("INSERT INTO scores (game_id, player_id, score) VALUES (%s, %s, %s)",
                           (game_id, pid, score))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[MySQLStorage] Saved scores for room {room_code} into MySQL.")


# -----------------------------
# Game & Room
# -----------------------------

class Room:
    """Represents a lobby/room that can hold up to 15 players."""
    MAX_PLAYERS = 15

    def __init__(self, host_player_id: str, room_code: Optional[str] = None, max_players: int = MAX_PLAYERS):
        self.room_code = room_code or gen_room_code()
        self.host_player_id = host_player_id
        self.max_players = min(max_players, self.MAX_PLAYERS)
        self.players: Dict[str, Player] = {}  # player_id -> Player
        self.game: Optional[Game] = None
        self.points_rules: Dict = {}  # customizable points settings
        print(f"[Room] Created room {self.room_code} (host={host_player_id})")

    def add_player(self, player: Player) -> bool:
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

    def list_players(self) -> List[Player]:
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
        self.deck = Deck(num_decks=self.deck_count)
        self.points_rules = points_rules or {"points_per_remaining_card": 1}
        self.round_number = 0
        self.finished: bool = False
        self.round_history: List[Dict] = []  # store per-round results
        # Copy players into game context
        self.players: List[Player] = list(room.players.values())

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
        self.deck = Deck(num_decks=self.deck_count)
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


# -----------------------------
# Presentation Utilities
# -----------------------------

def format_table(rows: List[Tuple], headers: List[str]) -> str:
    """Simple ASCII table formatting without external libs."""
    # Compute column widths
    cols = len(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    # Build header
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_row = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    lines = [sep, header_row, sep]
    # Rows
    for r in rows:
        row = "| " + " | ".join(str(r[i]).ljust(widths[i]) for i in range(cols)) + " |"
        lines.append(row)
    lines.append(sep)
    return "\n".join(lines)


def print_scoreboard(game: Game):
    board = game.get_scoreboard()
    rows = [(idx+1, pid, name, score) for idx, (pid, name, score) in enumerate(board)]
    print(format_table(rows, ["Pos", "Player ID", "Name", "Score"]))

# -----------------------------
# CLI flow (example)
# -----------------------------

def cli_demo():
    print("=== Kali Teedi - CLI Demo ===")
    host_id = input("Enter your user id (host): ").strip() or "host1"
    room = Room(host_player_id=host_id)
    # Host auto-joins
    host_player = Player(player_id=host_id, display_name=input("Host display name (optional): ").strip() or host_id)
    room.add_player(host_player)

    # Join other players
    while True:
        add_more = input("Add another player? (y/n): ").strip().lower()
        if add_more != 'y':
            break
        pid = input("Player id: ").strip()
        if not pid:
            print("Invalid id")
            continue
        pname = input("Display name (optional): ").strip() or pid
        p = Player(player_id=pid, display_name=pname)
        if not room.add_player(p):
            print("Could not add player.")
    print(f"Players in room {room.room_code}: {[p.display_name for p in room.list_players()]}")

    # Host sets points rules
    print("Set points rules for game (leave blank for defaults).")
    ppr = input("points_per_remaining_card (default 1): ").strip()
    winner_bonus = input("winner_bonus (default sum of penalties): ").strip()
    rules = {}
    if ppr:
        try:
            rules["points_per_remaining_card"] = int(ppr)
        except:
            rules["points_per_remaining_card"] = 1
    if winner_bonus:
        try:
            rules["winner_bonus"] = int(winner_bonus)
        except:
            pass
    room.set_points_rules(rules or {"points_per_remaining_card": 1})

    # Start game
    game = room.start_game(deck_count=1)

    storage = JSONScoreStorage()  # default json file

    # Play loop
    while True:
        round_res = game.play_round()
        # Display round delta and scoreboard
        print("\nRound result delta:")
        for pid, delta in round_res["delta"].items():
            print(f"  {pid}: {delta}")
        print("\nScores after round:")
        print_scoreboard(game)

        # Persist this game's latest scoreboard into storage
        scoreboard_dict = {pid: score for pid, _, score in game.get_scoreboard()}
        storage.save_game_scores(room_code=room.room_code, scoreboard=scoreboard_dict)

        # Ask user: restart current game with same players? or quit to new room?
        choice = input("\nOptions: (r)estart same game (same players), (c)ontinue next round, (q)uit to new room: ").strip().lower()
        if choice == 'r':
            # Reset scores and start a new Game instance with same players
            for p in game.players:
                p.score = 0
            game = room.start_game(deck_count=1)
            continue
        elif choice == 'c':
            # Continue next round until deck insufficient
            if game.is_game_over():
                print("Not enough cards to deal another full round. End of game.")
                break
            else:
                continue
        else:
            print("Quitting to new room screen.")
            break

    print("Final scoreboard:")
    print_scoreboard(game)
    print("Returning to new room screen (exit).")


if __name__ == "__main__":
    cli_demo()





## This is the part of documentation that was. provided to make any changes :
# stored in notes app

