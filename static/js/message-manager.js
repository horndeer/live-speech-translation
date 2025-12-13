// static/js/message-manager.js

class MessageManager {
    constructor(socket, devMode = false) {
        this.socket = socket;
        this.devMode = devMode;
        
        // On récupère les éléments DOM une seule fois au démarrage
        this.container = document.querySelector('.container');
        this.conversation = document.getElementById('conversation');

        // On lance les écouteurs
        this.initSocketListeners();
    }

    initSocketListeners() {
        this.socket.on('load_history', (history) => {
            if (this.devMode) console.log("Chargement historique:", history.length, "messages");
            
            // Vider l'écran pour éviter les doublons
            this.conversation.innerHTML = '';
            
            history.forEach(data => this.addMessage(data));

            // Force scroll en bas après chargement
            requestAnimationFrame(() => {
                this.container.scrollTop = this.container.scrollHeight;
            });
        });

        this.socket.on('display_message', (data) => {
            if (this.devMode) console.log("Nouveau message:", data);
            this.addMessage(data);
        });

        this.socket.on('clear_screen', () => {
            this.conversation.innerHTML = '';
        });
    }

    addMessage(data) {
        // Validation basique
        if (!data.fr || !data.es || data.fr.trim() === "" || data.es.trim() === "") return;

        // 1. Suppression des messages temporaires (lignes .temp)
        const temps = this.conversation.querySelectorAll('.msg-row.temp');
        temps.forEach(e => e.remove());

        // 2. Calcul du scroll AVANT insertion
        // Est-ce que l'utilisateur est déjà en bas ? (Tolérance 50px)
        const isScrolledToBottom = (this.container.scrollHeight - this.container.scrollTop) <= (this.container.clientHeight + 50);

        // 3. Création DOM
        const row = document.createElement('div');
        row.className = data.is_final ? 'msg-row' : 'msg-row temp';

        const cellFr = document.createElement('div');
        cellFr.className = 'msg-cell fr-cell';
        cellFr.innerText = data.fr;

        const cellEs = document.createElement('div');
        cellEs.className = 'msg-cell es-cell';
        cellEs.innerText = data.es;

        row.appendChild(cellFr);
        row.appendChild(cellEs);

        // 4. Insertion (Append car flex-direction: column)
        this.conversation.appendChild(row);

        // 5. Scroll intelligent
        if (isScrolledToBottom || data.is_final) {
            requestAnimationFrame(() => {
                this.container.scrollTop = this.container.scrollHeight;
            });
        }
    }
}