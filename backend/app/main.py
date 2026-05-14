from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import rooms, websocket

load_dotenv()

app = FastAPI(title="Beatdrop")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(websocket.router)

@app.get("/health")
def health():
    return {"status": "ok"}
