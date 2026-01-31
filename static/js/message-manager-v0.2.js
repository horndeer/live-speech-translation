// static/js/message-manager.js

class MessageManager {
    constructor(socket, devMode = false) {
        this.socket = socket;
        this.devMode = devMode;

        this.scrollContainer = document.getElementById('container-scroll');
        this.conversation = document.getElementById('conversation');

        this.initSocketListeners();
    }

    initSocketListeners() {
        this.socket.on('load_history', (history) => {
            if (this.devMode) console.log("Chargement historique:", history.length, "messages");
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

        this.socket.on('clear_screen', () => {
            this.clearConversation();
        });

        this.scrollToBottom();
    }

    clearConversation() {
        this.conversation.innerHTML = '';
    }

    scrollToBottom() {
        if (!this.scrollContainer) return;
        const el = this.scrollContainer;
        if (el.scrollTop + el.clientHeight >= el.scrollHeight - 2) return;
        el.scrollTop = el.scrollHeight;
    }

    _buildRowHtml(data, time, isFr, isEs) {
        return `
            <div class="border-r border-zinc-700/50 pr-6 py-2 self-stretch ">
                <div class="text-xs text-zinc-500 mb-1 flex items-center gap-2 select-none min-h-[1.25rem]">
                    <span class="font-bold text-zinc-600">${isFr ? time : '&nbsp;'}</span>
                </div>
                <p class="text-xl md:text-2xl font-normal text-white leading-relaxed break-words">${data.fr}</p>
            </div>
            <div class="pl-2 py-2 self-stretch">
                <div class="text-xs text-zinc-500 mb-1 flex items-center gap-2 select-none min-h-[1.25rem]">
                    <span class="font-bold text-zinc-600">${isEs ? time : '&nbsp;'}</span>
                </div>
                <p class="text-xl md:text-2xl font-normal text-accent leading-relaxed break-words">${data.es}</p>
            </div>
        `;
    }

    addMessage(data) {
        if (!data.fr || !data.es || data.fr.trim() === "" || data.es.trim() === "") return;

        const time = data.timestamp
            ? new Date(data.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
            : '??:??';
        const sourceLang = data.source_language || data.lang || 'unknown';
        const isFr = sourceLang.includes('fr');
        const isEs = sourceLang.includes('es');

        const tempRow = this.conversation.querySelector('.msg-row.temp');

        if (data.is_final) {
            if (tempRow) {
                tempRow.classList.remove('opacity-60', 'italic', 'temp');
                const cols = tempRow.querySelectorAll('p');
                if (cols[0]) cols[0].textContent = data.fr;
                if (cols[1]) cols[1].textContent = data.es;
                const times = tempRow.querySelectorAll('.font-bold.text-zinc-600');
                if (times[0]) times[0].textContent = isFr ? time : '\u00A0';
                if (times[1]) times[1].textContent = isEs ? time : '\u00A0';
            } else {
                const row = document.createElement('div');
                row.className = 'msg-row grid grid-cols-2 gap-6 group hover:bg-white/5 transition-colors';
                row.innerHTML = this._buildRowHtml(data, time, isFr, isEs);
                this.conversation.appendChild(row);
            }
        } else {
            if (tempRow) {
                const cols = tempRow.querySelectorAll('p');
                if (cols[0]) cols[0].textContent = data.fr;
                if (cols[1]) cols[1].textContent = data.es;
            } else {
                const row = document.createElement('div');
                row.className = 'msg-row grid grid-cols-2 gap-6 group hover:bg-white/5 transition-colors opacity-60 italic temp';
                row.innerHTML = this._buildRowHtml(data, time, isFr, isEs);
                this.conversation.appendChild(row);
            }
        }

        let isUserAtBottom = true;
        if (this.scrollContainer) {
            const position = this.scrollContainer.scrollTop + this.scrollContainer.clientHeight;
            isUserAtBottom = position >= this.scrollContainer.scrollHeight - 100;
        }
        if (isUserAtBottom || data.is_final) {
            requestAnimationFrame(() => this.scrollToBottom());
        }
    }
}