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
            {
                "fr": msg.fr,
                "es": msg.es,
                "timestamp": msg.timestamp.isoformat(),
                "source_language": msg.source_language,
            }
            for msg in messages
        ]
        print("HISTORY: ", history)
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


async def get_connected_sockets_count() -> int:
    """
    Retourne le nombre de sockets connectés à un instant t.
    Utilise le manager de socketio pour compter les participants actifs.
    """
    try:
        # Obtenir tous les participants dans le namespace par défaut '/'
        participants = await sio.manager.get_participants("/", None)
        return len(participants) if participants else 0
    except Exception as e:
        print(f"Erreur lors du comptage des sockets: {e}")
        return 0


async def get_socket_statistics() -> dict:
    """
    Retourne des statistiques détaillées sur les connexions Socket.IO.
    """
    try:
        total_count = await get_connected_sockets_count()
        master_sid = sid_registry.get("master")
        is_master_connected = master_sid is not None

        # Compter les viewers (tous les sockets sauf le master)
        viewer_count = total_count - (1 if is_master_connected else 0)

        return {
            "total_connected": total_count,
            "master_connected": is_master_connected,
            "master_sid": master_sid,
            "viewer_count": max(0, viewer_count),  # S'assurer que c'est >= 0
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques: {e}")
        return {
            "total_connected": 0,
            "master_connected": False,
            "master_sid": None,
            "viewer_count": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


@app.get("/api/socket-count")
async def get_socket_count():
    """
    Endpoint API pour obtenir le nombre de sockets connectés.
    Accessible sans authentification pour faciliter le monitoring.
    """
    count = await get_connected_sockets_count()
    return {"connected_sockets": count, "timestamp": datetime.now().isoformat()}


@app.get("/api/socket-stats")
async def get_socket_stats():
    """
    Endpoint API pour obtenir des statistiques détaillées sur les connexions.
    Inclut le nombre total, l'état du master, et le nombre de viewers.
    """
    stats = await get_socket_statistics()
    return stats


@app.post("/api/sync-socket-count")
async def sync_socket_count_endpoint():
    """
    Endpoint API pour synchroniser manuellement le compteur de viewers.
    Utile pour corriger les désynchronisations.
    """
    viewer_count = await sync_viewer_count()
    stats = await get_socket_statistics()
    return {"success": True, "synced_viewer_count": viewer_count, "statistics": stats}


# --- ÉVÉNEMENTS SOCKET.IO (Asynchrones) ---

sid_registry = {
    "master": None,
    "viewer_count": 0,
}


@sio.event
async def connect(sid, environ):
    global history, sid_registry
    # Récupérer le Referer depuis environ
    referer = environ.get("HTTP_REFERER", "")

    if "/master" in referer:
        client_type = "master"
    elif "/viewer" in referer:
        client_type = "viewer"
    else:
        client_type = "unknown"

    print(f"Client connecté: {sid} depuis {client_type}")

    # Enregistrer le type de client (vous avez déjà sid_registry)
    if client_type == "master":
        sid_registry["master"] = sid
    elif client_type == "viewer":
        sid_registry["viewer_count"] += 1

    await sio.emit("load_history", history, to=sid)

    if sid_registry.get("master"):
        await sio.emit(
            "update_viewer_count",
            sid_registry["viewer_count"],
            to=sid_registry["master"],
        )


@sio.event
async def disconnect(sid):
    global sid_registry
    try:
        if sid == sid_registry.get("master"):
            sid_registry["master"] = None
        else:
            # Décrémenter le compteur de viewers
            sid_registry["viewer_count"] = max(
                0, sid_registry.get("viewer_count", 0) - 1
            )
            # Notifier le master si connecté
            if sid_registry.get("master"):
                await sio.emit(
                    "update_viewer_count",
                    sid_registry["viewer_count"],
                    to=sid_registry["master"],
                )

        # Afficher le nombre total de sockets restants (pour debug)
        total_count = await get_connected_sockets_count()
        print(f"Client déconnecté: {sid}. Sockets restants: {total_count}")
    except Exception as e:
        print(f"Erreur lors de la déconnexion: {e}")


async def sync_viewer_count():
    """
    Synchronise le compteur de viewers avec le nombre réel de sockets connectés.
    Utile pour corriger les désynchronisations.
    """
    global sid_registry
    try:
        total_count = await get_connected_sockets_count()
        master_sid = sid_registry.get("master")

        # Vérifier si le master est toujours connecté en vérifiant s'il est dans les participants
        is_master_connected = False
        if master_sid:
            participants = await sio.manager.get_participants("/", None)
            is_master_connected = participants and master_sid in participants

        # Si le master n'est plus connecté, le retirer du registre
        if master_sid and not is_master_connected:
            sid_registry["master"] = None

        # Recalculer le nombre de viewers
        viewer_count = total_count - (1 if is_master_connected else 0)
        sid_registry["viewer_count"] = max(0, viewer_count)

        # Mettre à jour le master si nécessaire
        if master_sid and is_master_connected:
            await sio.emit(
                "update_viewer_count", sid_registry["viewer_count"], to=master_sid
            )

        return sid_registry["viewer_count"]
    except Exception as e:
        print(f"Erreur lors de la synchronisation: {e}")
        return sid_registry.get("viewer_count", 0)


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
            source_language=data.get("lang", "unknown"),
            timestamp=data["timestamp"],
        )

        history.append(
            {
                "fr": data["fr"],
                "es": data["es"],
                "timestamp": data["timestamp"],
            }
        )

    # On broadcast à tout le monde (ajouter source_language pour cohérence)
    broadcast_data = data.copy()
    broadcast_data["source_language"] = data.get("lang", "unknown")
    await sio.emit("display_message", broadcast_data, skip_sid=sid)


# Pour lancer le serveur :
# uvicorn app:socket_app --reload
