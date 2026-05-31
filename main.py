from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "data.json"

# ─── Модели ───────────────────────────────────────────────────────────────────

class CreateBoard(BaseModel):
    board_name: str
    admin_password: str

class JoinBoard(BaseModel):
    board_name: str
    gd_name: str
    account_id: int

class JoinWithPoints(BaseModel):
    board_name: str
    gd_name: str
    account_id: int
    points: float

class AddDemon(BaseModel):
    board_name: str
    gd_name: str
    demon_name: str
    demon_type: str
    admin_password: str

class SetPoints(BaseModel):
    board_name: str
    gd_name: str
    points: float
    admin_password: str

# ─── Хранилище ────────────────────────────────────────────────────────────────

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"boards": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Эндпоинты ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Night Prowlers Server is running!"}

@app.post("/board/create")
def create_board(body: CreateBoard):
    data = load_data()
    name = body.board_name.strip().lower()
    if name in data["boards"]:
        raise HTTPException(status_code=400, detail="Board already exists")
    data["boards"][name] = {
        "display_name": body.board_name.strip(),
        "admin_password": body.admin_password,
        "players": []
    }
    save_data(data)
    return {"ok": True, "message": f"Board '{body.board_name}' created!"}

@app.post("/board/join")
def join_board(body: JoinBoard):
    data = load_data()
    name = body.board_name.strip().lower()
    if name not in data["boards"]:
        raise HTTPException(status_code=404, detail="Board not found")
    board = data["boards"][name]
    for p in board["players"]:
        if p["account_id"] == body.account_id:
            return {"ok": True, "message": "Already in board"}
    board["players"].append({
        "name": body.gd_name,
        "account_id": body.account_id,
        "points": 0.0,
        "demons": []
    })
    save_data(data)
    return {"ok": True, "message": f"Joined '{board['display_name']}'!"}

@app.post("/board/join_with_points")
def join_with_points(body: JoinWithPoints):
    data = load_data()
    name = body.board_name.strip().lower()
    if name not in data["boards"]:
        raise HTTPException(status_code=404, detail="Board not found")
    board = data["boards"][name]
    # Обновляем если уже есть
    for p in board["players"]:
        if p["account_id"] == body.account_id:
            p["points"] = round(body.points, 1)
            p["name"] = body.gd_name
            save_data(data)
            return {"ok": True, "message": "Points updated"}
    # Добавляем нового
    board["players"].append({
        "name": body.gd_name,
        "account_id": body.account_id,
        "points": round(body.points, 1),
        "demons": []
    })
    save_data(data)
    return {"ok": True, "message": f"Joined with {body.points} points!"}

@app.get("/board/{board_name}")
def get_board(board_name: str):
    data = load_data()
    name = board_name.strip().lower()
    if name not in data["boards"]:
        raise HTTPException(status_code=404, detail="Board not found")
    board = data["boards"][name]
    players = sorted(board["players"], key=lambda p: p["points"], reverse=True)
    return {"board_name": board["display_name"], "players": players}

@app.post("/admin/add_demon")
def add_demon(body: AddDemon):
    data = load_data()
    name = body.board_name.strip().lower()
    if name not in data["boards"]:
        raise HTTPException(status_code=404, detail="Board not found")
    board = data["boards"][name]
    if board["admin_password"] != body.admin_password:
        raise HTTPException(status_code=403, detail="Wrong password")
    for player in board["players"]:
        if player["name"].lower() == body.gd_name.strip().lower():
            for d in player["demons"]:
                if d["name"].lower() == body.demon_name.strip().lower():
                    raise HTTPException(status_code=400, detail="Demon already added")
            player["demons"].append({"name": body.demon_name.strip(), "type": body.demon_type.strip().lower()})
            save_data(data)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Player not found")

@app.post("/admin/set_points")
def set_points(body: SetPoints):
    data = load_data()
    name = body.board_name.strip().lower()
    if name not in data["boards"]:
        raise HTTPException(status_code=404, detail="Board not found")
    board = data["boards"][name]
    if board["admin_password"] != body.admin_password:
        raise HTTPException(status_code=403, detail="Wrong password")
    for player in board["players"]:
        if player["name"].lower() == body.gd_name.strip().lower():
            player["points"] = round(body.points, 1)
            save_data(data)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Player not found")

@app.delete("/admin/remove_player")
def remove_player(board_name: str, gd_name: str, admin_password: str):
    data = load_data()
    name = board_name.strip().lower()
    if name not in data["boards"]:
        raise HTTPException(status_code=404, detail="Board not found")
    board = data["boards"][name]
    if board["admin_password"] != admin_password:
        raise HTTPException(status_code=403, detail="Wrong password")
    before = len(board["players"])
    board["players"] = [p for p in board["players"] if p["name"].lower() != gd_name.strip().lower()]
    if len(board["players"]) == before:
        raise HTTPException(status_code=404, detail="Player not found")
    save_data(data)
    return {"ok": True}
