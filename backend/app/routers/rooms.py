from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.room_manager import room_manager
from app.services.spotify import search_tracks
from app.models.room import Player

router = APIRouter()

class CreateRoomRequest(BaseModel):
    user_id: str
    username: str

class JoinRoomRequest(BaseModel):
    user_id: str
    username: str

@router.post("/rooms")
def create_room(body: CreateRoomRequest):
    host = Player(user_id=body.user_id, username=body.username)
    room = room_manager.create_room(host)
    return {"room_code": room.code, "host_id": room.host_id}

@router.post("/rooms/{room_code}/join")
def join_room(room_code: str, body: JoinRoomRequest):
    player = Player(user_id=body.user_id, username=body.username)
    success = room_manager.join_room(room_code, player)
    if not success:
        raise HTTPException(status_code=404, detail="Room not found or game already started")
    return {"joined": True}

@router.get("/rooms/{room_code}")
def get_room(room_code: str):
    room = room_manager.get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "code": room.code,
        "host_id": room.host_id,
        "state": room.state,
        "players": [p.model_dump() for p in room.players],
        "settings": room.settings.model_dump(),
        "round_number": room.round_number,
    }

@router.get("/search")
async def search(q: str, limit: int = 10):
    if not q.strip():
        return {"tracks": []}
    tracks = await search_tracks(q, limit)
    return {"tracks": tracks}
