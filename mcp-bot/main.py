"""
Minecraft Bridge MCP Server - Core API
Bridge entre MCP et l'API REST du serveur Minecraft
Endpoints de base du bridge-server (branche main)
"""

import os
import json
import uuid
from typing import Any, Dict, Optional
import requests
import weave
from dotenv import load_dotenv
from fastmcp import FastMCP

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

load_dotenv()
BASE_URL = os.environ.get("BRIDGE_BASE_URL", "https://8d86e8ed8956.ngrok-free.app")
TIMEOUT = float(os.environ.get("BRIDGE_HTTP_TIMEOUT", "10.0"))

# ------------------------------------------------------------------------------
# HTTP helpers
# ------------------------------------------------------------------------------

def _u(path: str) -> str:
    """Construit l'URL complète"""
    if not path.startswith("/"):
        path = "/" + path
    return f"{BASE_URL}{path}"

def _headers(idem: bool = True) -> Dict[str, str]:
    """Génère les headers pour la requête"""
    h = {"Content-Type": "application/json"}
    if idem:
        h["Idempotency-Key"] = str(uuid.uuid4())
    return h

def _normalize_response(resp: requests.Response) -> Dict[str, Any]:
    """Normalise la réponse HTTP"""
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        return {"success": True, "data": resp.text}
    
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} {data}")
    
    if isinstance(data, dict) and not data.get("success", True):
        err = data.get("error") or data.get("message") or "Unknown error"
        raise RuntimeError(f"API error: {err}")
    
    return data

def _get(path: str, params: Optional[Dict[str, Any]] = None, idem: bool = False) -> Dict[str, Any]:
    """Effectue une requête GET"""
    r = requests.get(_u(path), params=params, headers=_headers(idem), timeout=TIMEOUT)
    return _normalize_response(r)

def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Effectue une requête POST"""
    r = requests.post(_u(path), headers=_headers(True), data=json.dumps(body), timeout=TIMEOUT)
    return _normalize_response(r)

# ------------------------------------------------------------------------------
# MCP server
# ------------------------------------------------------------------------------

mcp = FastMCP("Minecraft Bridge MCP")
weave_client = weave.init("minecraft-bot-1") # metrics client

# ------------------------------------------------------------------------------
# Tools : Santé et Bot
# ------------------------------------------------------------------------------

@mcp.tool
@weave.op()
def health() -> Dict[str, Any]:
    """
    Vérifie le statut de santé du serveur et du bot.
    Retourne le statut du serveur et l'état de connexion du bot.
    Endpoint: GET /health
    """
    return _get("/health")

@mcp.tool
@weave.op()
def bot_status() -> Dict[str, Any]:
    """
    Obtient le statut complet du bot Minecraft.
    Retourne: connected, spawned, username, health, food, position, gameMode, playersOnline
    Endpoint: GET /bot/status
    """
    return _get("/bot/status")

# ------------------------------------------------------------------------------
# Tools : Mouvement
# ------------------------------------------------------------------------------

@mcp.tool
@weave.op()
def move_to(x: float, y: float, z: float) -> Dict[str, Any]:
    """
    Déplace le bot vers les coordonnées spécifiées.
    Utilise le pathfinding avec gestion du timeout et des chemins impossibles.
    Endpoint: POST /movement/moveTo
    """
    body = {"x": x, "y": y, "z": z}
    return _post("/movement/moveTo", body)

@mcp.tool
@weave.op()
def follow_player(playerName: Optional[str] = None, distance: float = 3, continuous: bool = False) -> Dict[str, Any]:
    """
    Fait suivre un joueur au bot.
    Si playerName non spécifié, suit le joueur le plus proche.
    
    Args:
        playerName: Nom du joueur à suivre (optionnel)
        distance: Distance de suivi en blocs (défaut: 3)
        continuous: Si True, continue de suivre indéfiniment
    
    Endpoint: POST /movement/follow
    """
    body: Dict[str, Any] = {"distance": distance, "continuous": continuous}
    if playerName:
        body["playerName"] = playerName
    return _post("/movement/follow", body)

@mcp.tool
@weave.op()
def stop_movement() -> Dict[str, Any]:
    """
    Arrête tous les mouvements du bot.
    Stoppe le pathfinder et tous les états de contrôle (avant/arrière/gauche/droite/jump/sprint/sneak).
    Endpoint: POST /movement/stop
    """
    return _post("/movement/stop", {})

@mcp.tool
@weave.op()
def get_position() -> Dict[str, Any]:
    """
    Obtient la position actuelle du bot.
    Retourne: position (x, y, z), yaw et pitch
    Endpoint: GET /movement/position
    """
    return _get("/movement/position")

@mcp.tool
@weave.op()
def look_at_player(playerName: str) -> Dict[str, Any]:
    """
    Fait regarder le bot vers un joueur spécifique.
    
    Args:
        playerName: Nom du joueur à regarder
    
    Endpoint: POST /movement/lookAtPlayer
    """
    body = {"playerName": playerName}
    return _post("/movement/lookAtPlayer", body)

# ------------------------------------------------------------------------------
# Tools : Chat
# ------------------------------------------------------------------------------

@mcp.tool
@weave.op()
def chat_say(message: str) -> Dict[str, Any]:
    """
    Envoie un message dans le chat du serveur Minecraft.
    
    Args:
        message: Message à envoyer
    
    Endpoint: POST /chat/say
    """
    body = {"message": message}
    return _post("/chat/say", body)

# ------------------------------------------------------------------------------
# Tools : Minage
# ------------------------------------------------------------------------------

@mcp.tool
@weave.op()
def mine_block(blockType: str, maxDistance: int = 32) -> Dict[str, Any]:
    """
    Mine un bloc d'un type spécifique.
    Le bot trouve le bloc le plus proche, se déplace jusqu'à lui et le mine.
    
    Args:
        blockType: Type de bloc à miner (ex: "stone", "wood", "diamond_ore")
        maxDistance: Distance maximale de recherche en blocs (défaut: 32)
    
    Endpoint: POST /mining/block
    """
    body = {"blockType": blockType, "maxDistance": maxDistance}
    return _post("/mining/block", body)

# ------------------------------------------------------------------------------
# Tools : Craft
# ------------------------------------------------------------------------------

@mcp.tool
@weave.op()
def craft_item(item: str, count: int = 1) -> Dict[str, Any]:
    """
    Fabrique un item dans Minecraft.
    Résout automatiquement la recette et utilise une table de craft si nécessaire.
    
    Args:
        item: Nom de l'item à fabriquer (ex: "stick", "stone_pickaxe")
        count: Quantité à fabriquer (défaut: 1)
    
    Endpoint: POST /crafting/item
    """
    body = {"item": item, "count": count}
    return _post("/crafting/item", body)

# ------------------------------------------------------------------------------
# Tools : Inventaire
# ------------------------------------------------------------------------------

@mcp.tool
@weave.op()
def get_inventory() -> Dict[str, Any]:
    """
    Obtient l'inventaire complet du bot.
    Retourne la liste des items avec nom, displayName, count, slot et le totalItems.
    Endpoint: GET /inventory
    """
    return _get("/inventory")

@mcp.tool
@weave.op()
def drop_item(itemName: str, count: int = 1) -> Dict[str, Any]:
    """
    Jette un item de l'inventaire du bot.
    
    Args:
        itemName: Nom de l'item à jeter
        count: Quantité à jeter (défaut: 1, -1 pour tout)
    
    Endpoint: POST /inventory/drop
    """
    body = {"itemName": itemName, "count": count}
    return _post("/inventory/drop", body)

# ------------------------------------------------------------------------------
# Point d'entrée principal
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[MCP] Minecraft Bridge Server - Core API")
    print(f"[MCP] Connecting to Bridge API at {BASE_URL}")
    print(f"[MCP] Default port: 3001 (configurable via BRIDGE_BASE_URL)")
    print(f"[MCP] Timeout: {TIMEOUT}s")
    
    try:
        # Test de connexion
        health_check = _get("/health")
        print(f"[MCP] Health check: {health_check}")
        
        if health_check.get("data", {}).get("bot", {}) == "connected":
            print("[MCP] ✓ Bot is connected")
        else:
            print("[MCP] ⚠ Bot is not connected - some endpoints may return 503")
            
    except Exception as e:
        print(f"[MCP] Warning: Could not connect to API - {e}")
        print(f"[MCP] Server will start anyway, API may become available later")
    
    print(f"[MCP] Starting MCP server...")
    mcp.run(transport="streamable-http")