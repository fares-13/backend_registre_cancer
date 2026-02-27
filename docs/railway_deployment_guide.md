# Guide de Déploiement Railway

Votre projet est maintenant prêt à être déployé sur Railway.

## 1. Pré-requis
- Un compte [Railway](https://railway.app/).
- Les identifiants PostgreSQL que vous m'avez fournis (déjà configurés dans le `.env` local).

## 2. Étapes de Déploiement

### Option A : Déploiement via GitHub (Recommandé)
1. Poussez votre code sur un dépôt GitHub.
2. Sur Railway, créez un nouveau projet et sélectionnez "Deploy from GitHub repo".
3. Railway détectera automatiquement le `Procfile` et installera les dépendances via `requirements.txt`.

### Option B : Déploiement via Railway CLI
1. Installez la CLI Railway : `npm i -g @railway/cli`.
2. Connectez-vous : `railway login`.
3. Liez votre projet : `railway link`.
4. Déployez : `railway up`.

## 3. Variables d'Environnement (Railway Dashboard)
Une fois le service créé, assurez-vous que les variables suivantes sont définies dans l'onglet **Variables** :
- `DATABASE_URL` : Automatique si vous liez un service PostgreSQL.
- `SECRET_KEY` : Votre clé secrète.
- `DEBUG` : `False` (pour la production).
- `ALLOWED_HOSTS` : mettre `*` ou l'URL de Railway (ex: `cancer-registry.up.railway.app`).

## 4. Initialisation de la Base de Données
Une fois déployé, vous devrez exécuter les migrations sur le serveur Railway :
1. Allez dans l'onglet **View Logs** ou utilisez la CLI.
2. Exécutez : `python manage.py migrate`.
3. Créez un super-utilisateur si besoin : `python manage.py createsuperuser`.

---
**Note technique** : J'ai configuré `whitenoise` pour servir les fichiers statiques (CSS/JS) directement via Django, ce qui est indispensable sur Railway.
