// static/js/message-manager.js

class MessageManager {
    constructor(socket, devMode = false) {
        this.socket = socket;
        this.devMode = devMode;
        
        // On récupère les éléments DOM une seule fois au démarrage
        this.scrollContainer = document.getElementById('container-scroll'); 
        this.conversation = document.getElementById('conversation');

        // On lance les écouteurs
        this.initSocketListeners();
    }

    initSocketListeners() {
        this.socket.on('load_history', (history) => {
            if (this.devMode) console.log("Chargement historique:", history.length, "messages");
            
            // Vider l'écran pour éviter les doublons
            this.clearConversation();

            history.forEach(data => {
                data.is_final = true;
                this.addMessage(data);
            });
        });

        this.socket.on('display_message', (data) => {
            if (this.devMode) console.log("Nouveau message:", data);
            this.addMessage(data);
        });

        this.scrollToBottom();
    }

    clearConversation() {
        this.conversation.innerHTML = '';
    }

    scrollToBottom() {
        if (!this.scrollContainer) return;
        requestAnimationFrame(() => {
            this.scrollContainer.scrollTop = this.scrollContainer.scrollHeight;
        });
    }

    addMessage(data) {
        // Validation basique
        if (!data.fr || !data.es || data.fr.trim() === "" || data.es.trim() === "") return;

        const temps = this.conversation.querySelectorAll('.msg-row.temp');
        temps.forEach(e => e.remove());

        let isUserAtBottom = true;
        if (this.scrollContainer) {
            const threshold = 100;
            const position = this.scrollContainer.scrollTop + this.scrollContainer.clientHeight;
            const height = this.scrollContainer.scrollHeight;
            isUserAtBottom = position >= height - threshold;
        }

        let time;
        if (data.timestamp) {
            time = new Date(data.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        } else {
            time = "??:??";
        }

        // Gérer source_language ou lang (pour compatibilité)
        const sourceLang = data.source_language || data.lang || 'unknown';
        const isFr = sourceLang.includes('fr');
        const isEs = sourceLang.includes('es');

        const row = document.createElement('div');

        row.className = `msg-row grid grid-cols-2 gap-6 group hover:bg-white/5 transition-colors ${data.is_final ? '' : 'opacity-60 italic temp'}`;
        

        row.innerHTML = `
            <div class="border-r border-zinc-700/50 pr-6 py-2 self-stretch ">
                <div class="text-xs text-zinc-500 mb-1 flex items-center gap-2 select-none min-h-[1.25rem]">
                    <span class="font-bold text-zinc-600">${isFr ? time : '&nbsp;'}</span>
                </div>
                <p class="text-xl md:text-2xl font-light text-white leading-relaxed break-words">
                    ${data.fr}
                </p>
            </div>
            <div class="pl-2 py-2 self-stretch">
                <div class="text-xs text-zinc-500 mb-1 flex items-center gap-2 select-none min-h-[1.25rem]">
                    <span class="font-bold text-zinc-600">${isEs ? time : '&nbsp;'}</span>
                </div>
                <p class="text-xl md:text-2xl font-light text-accent leading-relaxed break-words">
                    ${data.es}
                </p>
            </div>
        `;

        this.conversation.appendChild(row);

        if (isUserAtBottom || data.is_final) {
            this.scrollToBottom();
        }

    }
}