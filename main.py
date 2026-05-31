from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import json, os, hashlib

app = FastAPI()
DATA_FILE = "data.json"

def load():
    if not os.path.exists(DATA_FILE):
        return {"teams": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ── Модели ──────────────────────────────────────────────

class CreateTeam(BaseModel):
    team_name: str
    admin_gd_name: str
    admin_account_id: int
    admin_points: float
    is_public: bool = True
    password: Optional[str] = None

class JoinTeam(BaseModel):
    team_name: str
    gd_name: str
    account_id: int
    points: float
    password: Optional[str] = None

class UpdatePoints(BaseModel):
    team_name: str
    gd_name: str
    account_id: int
    points: float

# ── Эндпоинты ───────────────────────────────────────────

@app.get("/teams")
def list_teams():
    """Список всех команд (для браузера)"""
    data = load()
    result = []
    for name, team in data["teams"].items():
        result.append({
            "name": name,
            "is_public": team.get("is_public", True),
            "member_count": len(team.get("players", [])),
        })
    return {"teams": result}

@app.post("/team/create")
def create_team(body: CreateTeam):
    data = load()
    if body.team_name in data["teams"]:
        raise HTTPException(400, "Team already exists")
    
    pw_hash = hash_pw(body.password) if body.password and not body.is_public else None

    data["teams"][body.team_name] = {
        "is_public": body.is_public,
        "password_hash": pw_hash,
        "admin_account_id": body.admin_account_id,
        "players": [{
            "gd_name": body.admin_gd_name,
            "account_id": body.admin_account_id,
            "points": body.admin_points,
        }]
    }
    save(data)
    return {"ok": True, "team_name": body.team_name}

@app.post("/team/join")
def join_team(body: JoinTeam):
    data = load()
    if body.team_name not in data["teams"]:
        raise HTTPException(404, "Team not found")
    
    team = data["teams"][body.team_name]
    
    # Проверка пароля для приватных команд
    if not team.get("is_public", True):
        if not body.password:
            raise HTTPException(403, "Password required")
        if hash_pw(body.password) != team.get("password_hash", ""):
            raise HTTPException(403, "Wrong password")
    
    players = team.get("players", [])
    
    # Обновляем если уже есть, иначе добавляем
    for p in players:
        if p["account_id"] == body.account_id:
            p["gd_name"] = body.gd_name
            p["points"] = body.points
            save(data)
            return {"ok": True, "joined": False, "updated": True}
    
    players.append({
        "gd_name": body.gd_name,
        "account_id": body.account_id,
        "points": body.points,
    })
    team["players"] = players
    save(data)
    return {"ok": True, "joined": True}

@app.post("/team/update_points")
def update_points(body: UpdatePoints):
    """Автообновление поинтов без пароля (для тех кто уже в команде)"""
    data = load()
    if body.team_name not in data["teams"]:
        raise HTTPException(404, "Team not found")
    
    team = data["teams"][body.team_name]
    players = team.get("players", [])
    
    for p in players:
        if p["account_id"] == body.account_id:
            p["gd_name"] = body.gd_name
            p["points"] = body.points
            save(data)
            return {"ok": True}
    
    raise HTTPException(404, "Player not in team")

@app.get("/team/{team_name}")
def get_team(team_name: str):
    data = load()
    if team_name not in data["teams"]:
        raise HTTPException(404, "Team not found")
    team = data["teams"][team_name]
    return {
        "name": team_name,
        "is_public": team.get("is_public", True),
        "players": sorted(team.get("players", []), key=lambda p: p.get("points", 0), reverse=True)
    }
