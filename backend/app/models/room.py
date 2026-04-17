from pydantic import BaseModel
from typing import Optional
from enum import Enum

class RoomState(str, Enum):
    lobby = "lobby"
    playing = "playing"
    round_end = "round_end"

class Player(BaseModel):
    user_id: str
    username: str
    score: int = 0
    is_connected: bool = True

class Guess(BaseModel):
    user_id: str
    guessed_at: float
    correct: bool
    points_awarded: int

class CurrentRound(BaseModel):
    track_id: str
    preview_url: str
    track_name: str
    artist_name: str
    play_at: float
    guesses: list[Guess] = []

class RoomSettings(BaseModel):
    time_limit_seconds: Optional[int] = None
    rounds_total: int = 5

class Room(BaseModel):
    code: str
    host_id: str
    players: list[Player] = []
    state: RoomState = RoomState.lobby
    current_round: Optional[CurrentRound] = None
    settings: RoomSettings = RoomSettings()
    round_number: int = 0
