import os
import json
import httpx  # Remplace requests
import socketio
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()

# Configuration
SPEECH_KEY = os.environ.get("SPEECH_KEY")
SPEECH_REGION = os.environ.get("SPEECH_REGION")
MASTER_PASSWORD = os.environ.get("MASTER_PASSWORD", "admin")
DB_FILE = "storage/transcript_history.json"
DEV_MODE = os.environ.get("DEV_MODE", "False") == "True"

# --- CONFIGURATION FASTAPI & SOCKETIO ---

app = FastAPI()

templates = Jinja2Templates(directory="templates")
templates.env.globals["DEV_MODE"] = DEV_MODE

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Configuration Socket.IO en mode Asynchrone (ASGI)
# Le cors_allowed_origins='*' est permissif, voir section sécurité plus bas
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# --- PERSISTANCE DES DONNÉES ---

def create_storage_directory():
    if not os.path.exists("storage"):
        os.makedirs("storage")

def load_history():
    """Charge l'historique depuis le disque au démarrage"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lecture historique: {e}")
            return []
    return []

def save_history(history_data):
    """Sauvegarde l'historique sur le disque"""
    create_storage_directory()
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde historique: {e}")

# Chargement initial (Variable Globale en mémoire)
history = load_history()

# --- ROUTES HTTP (FastAPI) ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/viewer")
async def viewer(request: Request):
    return templates.TemplateResponse("viewer.html", {"request": request})

@app.get("/master")
async def master(request: Request, pwd: str = ""):
    # FastAPI récupère automatiquement le paramètre 'pwd' de l'URL
    if pwd != MASTER_PASSWORD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
    return templates.TemplateResponse("master.html", {"request": request})

@app.get("/api/get-token")
async def get_azure_token():
    """
    Récupération asynchrone du token Azure.
    Ne bloque pas le serveur pendant la requête vers Microsoft.
    """
    if not SPEECH_KEY or not SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Clés API manquantes côté serveur")

    fetch_token_url = f"https://{SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": SPEECH_KEY}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(fetch_token_url, headers=headers)
            response.raise_for_status()
            return {"token": response.text, "region": SPEECH_REGION}
        except httpx.RequestError as e:
            print(f"Erreur réseau Azure: {e}")
            raise HTTPException(status_code=500, detail="Erreur de connexion à Azure")
        except httpx.HTTPStatusError as e:
            print(f"Erreur HTTP Azure: {e}")
            raise HTTPException(status_code=500, detail="Impossible de générer le token")

@app.post("/reset")
async def reset_history_route():
    """Commande pour vider l'historique"""
    global history
    history = []
    save_history(history)
    # On émet l'événement via le serveur SocketIO asynchrone
    await sio.emit("clear_screen")
    return {"status": "ok"}

# --- ÉVÉNEMENTS SOCKET.IO (Asynchrones) ---

@sio.event
async def connect(sid, environ):
    print(f"Client connecté: {sid}")
    # On envoie l'historique uniquement au client qui vient d'arriver (to=sid)
    await sio.emit("load_history", history, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client déconnecté: {sid}")

@sio.event
async def new_translation(sid, data):
    # Note: 'data' est automatiquement converti en dictionnaire Python par python-socketio
    if data.get("es").strip() == "" or data.get("fr").strip() == "":
        return
    
    # 1. Gestion des phrases FINALES
    if data.get("is_final"):
        history.append(data)
        
        # Limite à 200 phrases
        if len(history) > 200:
            history.pop(0)
            
        # Sauvegarde (Idéalement, cela devrait être fait en background task pour ne pas ralentir, 
        # mais pour un petit fichier c'est négligeable)
        save_history(history)

    # 2. Diffusion à tous les autres clients (skip_sid=sid si on ne veut pas renvoyer à l'émetteur)
    # Ici broadcast=True envoie à tout le monde
    await sio.emit("display_message", data)

# Pour lancer le serveur :
# uvicorn app:socket_app --reload