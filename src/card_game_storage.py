#!/usr/bin/env python3


import random
import string
import json
import os
from typing import List, Dict, Optional, Tuple



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

