#!/usr/bin/env python3
"""
FastAPI implementation for Kali Teedi card game.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import card_game_player
import card_game_room
import kaali_teedi_gameplay
import card_game_storage

app = FastAPI()

# In-memory storage for demo purposes
rooms: Dict[str, card_game_room.Room] = {}

# -----------------------------
# Request Models
# -----------------------------

class CreateRoomRequest(BaseModel):
    host_id: str
    host_name: str

class AddPlayerRequest(BaseModel):
    room_code: str
    player_id: str
    display_name: str

class SetRulesRequest(BaseModel):
    room_code: str
    points_per_remaining_card: int = 1
    winner_bonus: Optional[int] = None

class StartGameRequest(BaseModel):
    room_code: str
    deck_count: int = 1

class PlayRoundRequest(BaseModel):
    room_code: str

# -----------------------------
# API Endpoints
# -----------------------------

@app.post("/create_room")
def create_room(req: CreateRoomRequest):
    room = card_game_room.Room(host_player_id=req.host_id)
    host_player = card_game_player.Player(player_id=req.host_id, display_name=req.host_name)
    room.add_player(host_player)
    rooms[room.room_code] = room
    return {"room_code": room.room_code, "host_id": req.host_id, "host_name": req.host_name}

@app.post("/add_player")
def add_player(req: AddPlayerRequest):
    room = rooms.get(req.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    player = card_game_player.Player(player_id=req.player_id, display_name=req.display_name)
    if not room.add_player(player):
        raise HTTPException(status_code=400, detail="Could not add player")
    return {"success": True, "player_id": req.player_id, "display_name": req.display_name}

@app.post("/set_rules")
def set_rules(req: SetRulesRequest):
    room = rooms.get(req.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    rules = {"points_per_remaining_card": req.points_per_remaining_card}
    if req.winner_bonus is not None:
        rules["winner_bonus"] = req.winner_bonus
    room.set_points_rules(rules)
    return {"success": True, "rules": rules}

@app.post("/start_game")
def start_game(req: StartGameRequest):
    room = rooms.get(req.room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    try:
        game = kaali_teedi_gameplay.Game.start_game(room=room, deck_count=req.deck_count)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "room_code": req.room_code, "deck_count": req.deck_count}

@app.post("/play_round")
def play_round(req: PlayRoundRequest):
    room = rooms.get(req.room_code)
    if not room or not room.game:
        raise HTTPException(status_code=404, detail="Game not found")
    round_result = room.game.play_round()
    # Optionally persist scores
    storage = card_game_storage.JSONScoreStorage()
    scoreboard_dict = {pid: score for pid, _, score in room.game.get_scoreboard()}
    storage.save_game_scores(room_code=room.room_code, scoreboard=scoreboard_dict)
    return round_result

@app.get("/scoreboard/{room_code}")
def get_scoreboard(room_code: str):
    room = rooms.get(room_code)
    if not room or not room.game:
        raise HTTPException(status_code=404, detail="Game not found")
    board = room.game.get_scoreboard()
    return {"scoreboard": board}

@app.get("/players/{room_code}")
def list_players(room_code: str):
    room = rooms.get(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    players = [{"player_id": p.player_id, "display_name": p.display_name, "score": p.score} for p in room.list_players()]
    return {"players": players}

@app.get("/rooms")
def list_rooms():
    return {"rooms": list(rooms.keys())}

# -----------------------------
# FastAPI entry point
# -----------------------------

# To run: uvicorn main:app --reload