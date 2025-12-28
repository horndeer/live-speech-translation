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
            
            history.forEach(data => this.addMessage(data));

            // Force scroll en bas après chargement
            // requestAnimationFrame(() => {
            //     this.container.scrollTop = this.container.scrollHeight;
            // });
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


        const time = getCurrentTime(); 

        const row = document.createElement('div');

        row.className = `msg-row grid grid-cols-2 gap-6 group hover:bg-white/5 p-4 rounded-xl transition-colors ${data.is_final ? '' : 'opacity-60 italic temp'}`;
        

        row.innerHTML = `
            <div class="border-r border-zinc-700/50 pr-6">
                <div class="text-xs text-zinc-500 mb-1 flex items-center gap-2 select-none">
                    <span class="font-bold text-zinc-600">FR</span> <span>${time}</span>
                </div>
                <p class="text-xl md:text-2xl font-light text-white leading-relaxed break-words">
                    ${data.fr}
                </p>
            </div>
            <div class="pl-2">
                <div class="text-xs text-zinc-500 mb-1 flex items-center gap-2 select-none">
                    <span class="font-bold text-zinc-600">ES</span>
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