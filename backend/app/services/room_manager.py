import json
import random
import string
import time
from fastapi import WebSocket
from app.models.room import Room, Player, RoomState, CurrentRound, Guess

def _generate_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase, k=6))

def _points_for_rank(rank: int) -> int:
    return ([10, 7, 5, 3][rank - 1]) if rank <= 4 else 1

class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        # room_code
        self.connections: dict[str, dict[str, WebSocket]] = {}

    def create_room(self, host: Player) -> Room:
        code = _generate_room_code()
        while code in self.rooms:
            code = _generate_room_code()

        room = Room(code=code, host_id=host.user_id, players=[host])
        self.rooms[code] = room
        self.connections[code] = {}
        return room

    def get_room(self, code: str) -> Room | None:
        return self.rooms.get(code)

    def delete_room(self, code: str):
        self.rooms.pop(code, None)
        self.connections.pop(code, None)

    async def connect(self, code: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[code][user_id] = websocket

        player = next((p for p in self.rooms[code].players if p.user_id == user_id), None)
        if player:
            player.is_connected = True

    def disconnect(self, code: str, user_id: str):
        self.connections[code].pop(user_id, None)

        room = self.rooms.get(code)
        if not room:
            return

        player = next((p for p in room.players if p.user_id == user_id), None)
        if player:
            player.is_connected = False

        connected = [p for p in room.players if p.is_connected]
        if not connected:
            self.delete_room(code)
            return

        # Auto-assign a new host if the host disconnected
        if room.host_id == user_id:
            room.host_id = connected[0].user_id

    async def broadcast(self, code: str, message: dict):
        payload = json.dumps(message)
        for ws in list(self.connections[code].values()):
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    async def send_to(self, code: str, user_id: str, message: dict):
        ws = self.connections[code].get(user_id)
        if ws:
            await ws.send_text(json.dumps(message))

    def join_room(self, code: str, player: Player) -> bool:
        room = self.rooms.get(code)
        if not room or room.state != RoomState.lobby:
            return False
        if not any(p.user_id == player.user_id for p in room.players):
            room.players.append(player)
        return True

    def transfer_host(self, code: str, from_user_id: str, to_user_id: str) -> bool:
        room = self.rooms.get(code)
        if not room or room.host_id != from_user_id:
            return False
        if not any(p.user_id == to_user_id for p in room.players):
            return False
        room.host_id = to_user_id
        return True

    def start_round(self, code: str, track_id: str, preview_url: str, track_name: str, artist_name: str) -> CurrentRound | None:
        room = self.rooms.get(code)
        if not room:
            return None

        # schedule playback 2 seconds from now so all clients receive the
        # message and buffer before the clip starts
        play_at = (time.time() + 2) * 1000

        round_data = CurrentRound(
            track_id=track_id,
            preview_url=preview_url,
            track_name=track_name,
            artist_name=artist_name,
            play_at=play_at,
        )
        room.current_round = round_data
        room.state = RoomState.playing
        room.round_number += 1
        return round_data

    def submit_guess(self, code: str, user_id: str, guess_text: str) -> dict | None:
        room = self.rooms.get(code)
        if not room or room.state != RoomState.playing or not room.current_round:
            return None

        if any(g.user_id == user_id for g in room.current_round.guesses):
            return None

        is_correct = guess_text.lower().strip() == room.current_round.track_name.lower().strip()
        rank = sum(1 for g in room.current_round.guesses if g.correct) + 1 if is_correct else 0
        points = _points_for_rank(rank) if is_correct else 0

        room.current_round.guesses.append(Guess(
            user_id=user_id,
            guessed_at=time.time() * 1000,
            correct=is_correct,
            points_awarded=points,
        ))

        if is_correct:
            player = next((p for p in room.players if p.user_id == user_id), None)
            if player:
                player.score += points

        return {"correct": is_correct, "points": points, "rank": rank if is_correct else None}

    def end_round(self, code: str):
        room = self.rooms.get(code)
        if room:
            room.state = RoomState.round_end

    def scoreboard(self, code: str) -> list[dict]:
        room = self.rooms.get(code)
        if not room:
            return []
        return [
            {"user_id": p.user_id, "username": p.username, "score": p.score}
            for p in sorted(room.players, key=lambda p: p.score, reverse=True)
        ]


room_manager = RoomManager()
