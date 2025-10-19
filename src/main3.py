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
import kaali_teedi_gameplay
import card_game_room


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


def print_scoreboard(game: kaali_teedi_gameplay.Game):
    board = game.get_scoreboard()
    rows = [(idx+1, pid, name, score) for idx, (pid, name, score) in enumerate(board)]
    print(format_table(rows, ["Pos", "Player ID", "Name", "Score"]))

# -----------------------------
# CLI flow (example)
# -----------------------------

def cli_demo():
    print("=== Kali Teedi - CLI Demo ===")
    host_id = input("Enter your user id (host): ").strip() or "host1"
    room = card_game_room.Room(host_player_id=host_id)
    # Host auto-joins
    host_player = card_game_player.Player(player_id=host_id, display_name=input("Host display name (optional): ").strip() or host_id)
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
        p = card_game_player.Player(player_id=pid, display_name=pname)
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
    game = kaali_teedi_gameplay.Game.start_game(deck_count=1, room=room)

    storage = card_game_storage.JSONScoreStorage() 

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
