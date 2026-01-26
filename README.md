# live-speech-translation

web app for speech live translation and sharing


## installation

Créez une ressource azure speech sur microsoft azure, au moment où je fait se projet ils donnent 5h d'utilisation gratuite par moi ce qui est suffisant pour beaucoup de discours.

Récupérez la clé d'API et la région.

Créez un fichier ".env" à la racine du projet, avec les différents champs:

```
SPEECH_KEY=...
SPEECH_REGION=...
MASTER_PASSWORD=votrepswd
SECRET_KEY=votre_clé_secrète_pour_les_sessions (optionnel, généré automatiquement si absent)
```

**Note sur l'authentification :** 
- L'authentification utilise maintenant des sessions sécurisées avec cookies (au lieu de GET avec mot de passe dans l'URL)
- Les sessions persistent pendant 30 jours sur l'appareil
- Pour la production avec HTTPS, définissez `SECRET_KEY` dans le .env avec une clé forte (générée avec `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

Installez les requirements, dans un environnement virtuel de préférence et pour lancer l'app: 

```
python app.py
```

## Déploiement (CI/CD)

Le dépôt inclut une GitHub Action (`.github/workflows/deploy.yml`) qui déploie sur un serveur SSH à chaque push sur `main`.

**Prérequis sur le serveur :**
- Python 3, venv, `pip install -r requirements.txt`
- **Node.js et npm** (pour le build Tailwind → `static/css/tailwind.css`)
- pm2 pour faire tourner l’app

Le script de deploy exécute : `git pull` → `npm ci` + `npm run build-css` → `pip install -r requirements.txt` → `pm2 reload`. Aucune action manuelle après un push sur `main` si Node et npm sont déjà installés sur la machine.


