# Configuration Tailwind CSS

Ce projet utilise maintenant Tailwind CSS avec un processus de build pour générer un CSS optimisé.

## Installation

1. Installer Node.js et npm si ce n'est pas déjà fait
2. Installer les dépendances :
```bash
npm install
```

## Utilisation

### Générer le CSS (production)
```bash
npm run build-css
```

Cette commande génère `static/css/tailwind.css` (minifié et optimisé).

### Mode développement (watch)
```bash
npm run watch-css
```

Cette commande surveille les changements dans vos fichiers HTML/JS et régénère automatiquement le CSS.

## Avantages par rapport au CDN

✅ **Performance** : CSS optimisé et minifié (beaucoup plus léger)
✅ **Purge automatique** : Seules les classes utilisées sont incluses
✅ **Personnalisation** : Configuration centralisée dans `tailwind.config.js`
✅ **Pas de JavaScript** : CSS statique, chargement plus rapide
✅ **Production-ready** : Prêt pour la mise en production

## Fichiers de configuration

- `tailwind.config.js` : Configuration Tailwind (couleurs, thème, etc.)
- `static/css/input.css` : Fichier source avec les directives Tailwind
- `static/css/tailwind.css` : Fichier généré (à ne pas modifier manuellement)

## Workflow recommandé

1. **Développement** : Lancer `npm run watch-css` en arrière-plan
2. **Avant commit** : Exécuter `npm run build-css` pour générer la version optimisée
3. **Production** : Utiliser le fichier `tailwind.css` généré


