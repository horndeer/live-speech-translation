import os
import json
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_mariage_secure'
socketio = SocketIO(app, cors_allowed_origins="*")

# FICHIER DE SAUVEGARDE (Pour ne pas perdre le discours si le serveur reboot)
DB_FILE = "storage/transcript_history.json"

def create_storage_directory():
    if not os.path.exists('storage'):
        os.makedirs('storage')

def load_history():
    """Charge l'historique depuis le disque au démarrage"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history():
    """Sauvegarde l'historique sur le disque"""
    create_storage_directory()
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# On charge l'historique au lancement du script
history = load_history()

# --- ROUTES (Inchangées) ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/viewer')
def viewer(): return render_template('viewer.html')

@app.route('/master')
def master():
    if request.args.get('pwd') != os.environ.get('MASTER_PASSWORD', 'admin'):
        return "Accès refusé", 403
    return render_template('master.html', 
                           speech_key=os.environ.get('SPEECH_KEY'), 
                           speech_region=os.environ.get('SPEECH_REGION'))

# --- LOGIQUE SOCKET IO ROBUSTE ---

@socketio.on('connect')
def handle_connect():
    """
    LOGIQUE CLÉ : Quand un viewer arrive, on lui donne tout le contexte.
    Le client n'a pas besoin de demander, c'est automatique.
    """
    print(f"Client connecté. Envoi de {len(history)} lignes d'historique.")
    emit('load_history', history)

@socketio.on('new_translation')
def handle_translation(data):
    """Reçoit du Master -> Stocke -> Diffuse aux Viewers"""
    
    # 1. Gestion des phrases FINALES (validées par l'IA)
    if data.get('is_final'):
        # On ajoute à la mémoire du serveur
        history.append(data)
        
        # On limite à 200 phrases pour ne pas surcharger le navigateur des invités à la longue
        if len(history) > 200:
            history.pop(0)
            
        # On sauvegarde sur le disque dur (Persistance)
        save_history()
    
    # 2. Diffusion (Broadcast)
    # On envoie à tout le monde.
    # Note : Même les phrases "non-finales" (en cours) sont diffusées pour l'effet live,
    # mais elles ne sont PAS stockées dans l'historique.
    emit('display_message', data, broadcast=True)

@app.route('/reset', methods=['POST'])
def reset_history():
    """Commande admin pour vider l'historique entre deux discours"""
    global history
    history = []
    save_history() # On vide aussi le fichier
    socketio.emit('clear_screen', broadcast=True)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)