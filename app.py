import datetime
import os
import json
import secrets
import httpx  # Remplace requests
import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse, Response
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from database import *

# Charge les variables d'environnement
load_dotenv()

# Configuration
SPEECH_KEY = os.environ.get("SPEECH_KEY")
SPEECH_REGION = os.environ.get("SPEECH_REGION")
MASTER_PASSWORD = os.environ.get("MASTER_PASSWORD", "admin")
DB_FILE = "storage/transcript_history.json"
DEV_MODE = os.environ.get("DEV_MODE", "False") == "True"

# Configuration de sécurité pour les sessions
# Génère une clé secrète si elle n'existe pas (à définir en production via .env)
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
SESSION_COOKIE_NAME = "master_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 jours en secondes

# Serializer pour signer les cookies de session
serializer = URLSafeTimedSerializer(SECRET_KEY)

# --- CONFIGURATION FASTAPI & SOCKETIO ---

CURRENT_SESSION_ID = 1
history = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global CURRENT_SESSION_ID, history
    await init_db()
    # Optionnel : Créer une session par défaut si aucune n'existe
    convs = await get_conversations()
    if not convs:
        success, new_conv = await start_new_conversation()
        print(
            f"Aucune session trouvé, création d'une nouvelle sessions, id:{CURRENT_SESSION_ID}"
        )
    else:
        last_conv = await get_last_conversation()
        CURRENT_SESSION_ID = last_conv.id
        messages = await get_messages_by_conversation(CURRENT_SESSION_ID)
        history = [
            {"fr": msg.fr, "es": msg.es, "timestamp": msg.timestamp.isoformat()}
            for msg in messages
        ]
        print(
            f"Chargement de la dernière session, id:{CURRENT_SESSION_ID}, name:{last_conv.title}, messages:{len(messages)}"
        )
    yield
    # Shutdown (if needed)


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")
templates.env.globals["DEV_MODE"] = DEV_MODE

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Configuration Socket.IO en mode Asynchrone (ASGI)
# Le cors_allowed_origins='*' est permissif, voir section sécurité plus bas
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)


# --- PERSISTANCE DES DONNÉES ---


def parse_iso(ts: str | None) -> datetime:
    if not ts:
        return datetime.now()
    try:
        # gère les ISO avec 'Z' (UTC) ou offset
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return datetime.now()


async def start_new_conversation():
    global CURRENT_SESSION_ID, history
    try:
        title = f"Conversation du {datetime.now().strftime('%d/%m %H:%M')}"
        new_conv = await create_conversation(title=title)
        CURRENT_SESSION_ID = new_conv.id
        history = []
        await sio.emit("clear_screen")
    except:
        return False, CURRENT_SESSION_ID
    return True, new_conv.id


# --- AUTHENTIFICATION ET SESSIONS ---


def create_session_token() -> str:
    """Crée un token de session signé avec une date d'expiration"""
    data = {"authenticated": True, "timestamp": datetime.now().isoformat()}
    return serializer.dumps(data, salt="master-auth")


def verify_session_token(token: str) -> bool:
    """Vérifie si un token de session est valide"""
    try:
        serializer.loads(token, salt="master-auth", max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def get_session_token(request: Request) -> str | None:
    """Récupère le token de session depuis le cookie"""
    return request.cookies.get(SESSION_COOKIE_NAME)


async def require_auth(request: Request) -> bool:
    """Dépendance FastAPI pour vérifier l'authentification"""
    token = get_session_token(request)
    if not token or not verify_session_token(token):
        # Si c'est une requête API, retourner une erreur JSON
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentification requise",
            )
        # Pour les pages HTML, lever une exception qui sera gérée
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Authentification requise"
        )
    return True


def check_auth(request: Request) -> RedirectResponse | None:
    """Vérifie l'authentification et retourne une redirection si nécessaire"""
    token = get_session_token(request)
    if not token or not verify_session_token(token):
        return RedirectResponse(url="/login", status_code=303)
    return None


# --- ROUTES HTTP (FastAPI) ---


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/viewer")
async def viewer(request: Request):
    return templates.TemplateResponse("viewer.html", {"request": request})


@app.get("/login")
async def login_page(request: Request):
    """Page de connexion"""
    # Si déjà authentifié, rediriger vers /master
    token = get_session_token(request)
    if token and verify_session_token(token):
        return RedirectResponse(url="/master", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/login")
async def login(response: Response, password: str = Form(...)):
    """Endpoint d'authentification via POST"""
    if password != MASTER_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect"
        )

    # Créer le token de session
    session_token = create_session_token()

    # Définir le cookie sécurisé
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,  # Protection XSS - le cookie n'est pas accessible via JavaScript
        secure=False,  # Mettre à True en production avec HTTPS
        samesite="lax",  # Protection CSRF
    )

    return {"success": True, "message": "Authentification réussie"}


@app.post("/api/logout")
async def logout(response: Response):
    """Endpoint de déconnexion"""
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"success": True, "message": "Déconnexion réussie"}


@app.get("/master")
async def master(request: Request):
    """Page maître protégée par authentification"""
    redirect = check_auth(request)
    if redirect:
        return redirect

    convs_list = await get_conversation_list()
    print("CONVS LIST: ", convs_list)
    return templates.TemplateResponse(
        "master.html", {"request": request, "convs_list": convs_list}
    )


@app.get("/master/new")
async def new_conversation(request: Request):
    """Créer une nouvelle conversation (protégée)"""
    redirect = check_auth(request)
    if redirect:
        return redirect

    await start_new_conversation()
    return RedirectResponse(url="/master", status_code=303)


@app.get("/api/get-token")
async def get_azure_token():
    """
    Récupération asynchrone du token Azure.
    Ne bloque pas le serveur pendant la requête vers Microsoft.
    """
    if not SPEECH_KEY or not SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Clés API manquantes côté serveur")

    fetch_token_url = (
        f"https://{SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    )
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
            raise HTTPException(
                status_code=500, detail="Impossible de générer le token"
            )


# --- ÉVÉNEMENTS SOCKET.IO (Asynchrones) ---


@sio.event
async def connect(sid, environ):
    global history
    print(f"Client connecté: {sid}")
    await sio.emit("load_history", history, to=sid)


@sio.event
async def disconnect(sid):
    print(f"Client déconnecté: {sid}")


@sio.event
async def new_translation(sid, data):
    # On sauvegarde SEULEMENT si c'est final
    if data.get("es").strip() == "" or data.get("fr").strip() == "":
        return

    if data.get("is_final"):
        await add_message(
            conversation_id=CURRENT_SESSION_ID,
            fr=data["fr"],
            es=data["es"],
            source_language=data.get("lang", "fr"),
            timestamp=parse_iso(data["timestamp"]),
        )

    # On broadcast à tout le monde
    await sio.emit("display_message", data, skip_sid=sid)


# Pour lancer le serveur :
# uvicorn app:socket_app --reload
