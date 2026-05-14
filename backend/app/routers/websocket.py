from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.room_manager import room_manager
from app.models.room import Player

router = APIRouter()

@router.websocket("/ws/{room_code}/{user_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_id: str, username: str):
    room = room_manager.get_room(room_code)
    if not room:
        await websocket.close(code=4004)
        return

    await room_manager.connect(room_code, user_id, websocket)
    await room_manager.broadcast(room_code, {
        "type": "player_joined",
        "username": username,
        "players": [p.model_dump() for p in room.players],
    })

    try:
        while True:
            data = await websocket.receive_json()
            await _handle_message(room_code, user_id, data)

    except WebSocketDisconnect:
        room_manager.disconnect(room_code, user_id)
        remaining = room_manager.get_room(room_code)
        if remaining:
            await room_manager.broadcast(room_code, {
                "type": "player_left",
                "username": username,
                "players": [p.model_dump() for p in remaining.players],
                "new_host_id": remaining.host_id,
            })


async def _handle_message(room_code: str, user_id: str, data: dict):
    msg_type = data.get("type")
    room = room_manager.get_room(room_code)
    if not room:
        return

    if msg_type == "start_round":
        if room.host_id != user_id:
            return
        round_data = room_manager.start_round(
            room_code,
            track_id=data["track_id"],
            preview_url=data["preview_url"],
            track_name=data["track_name"],
            artist_name=data["artist_name"],
        )
        if round_data:
            await room_manager.broadcast(room_code, {
                "type": "round_starting",
                "round_number": room.round_number,
                "preview_url": round_data.preview_url,
                "play_at": round_data.play_at,
                "artist_name": round_data.artist_name,
            })

    elif msg_type == "submit_guess":
        result = room_manager.submit_guess(room_code, user_id, data["text"])
        if result:
            await room_manager.broadcast(room_code, {
                "type": "guess_result",
                "user_id": user_id,
                "correct": result["correct"],
                "points": result["points"],
                "rank": result["rank"],
                "scoreboard": room_manager.scoreboard(room_code),
            })

    elif msg_type == "end_round":
        if room.host_id != user_id:
            return
        room_manager.end_round(room_code)
        answer = room.current_round.track_name if room.current_round else "Unknown"
        await room_manager.broadcast(room_code, {
            "type": "round_ended",
            "answer": answer,
            "scoreboard": room_manager.scoreboard(room_code),
        })

    elif msg_type == "transfer_host":
        success = room_manager.transfer_host(room_code, user_id, data["to_user_id"])
        if success:
            await room_manager.broadcast(room_code, {
                "type": "host_changed",
                "new_host_id": data["to_user_id"],
            })

    elif msg_type == "end_game":
        if room.host_id != user_id:
            return
        await room_manager.broadcast(room_code, {
            "type": "game_ended",
            "final_scoreboard": room_manager.scoreboard(room_code),
        })
        room_manager.delete_room(room_code)
