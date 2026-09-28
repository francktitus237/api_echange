# Configuration Dokploy pour ForexPlatform API

## Variables d'environnement requises

Dans l'interface Dokploy, configurez ces variables d'environnement :

### Sécurité
- `SECRET_KEY` : Clé secrète Django (générez une clé aléatoire longue)
- `DEBUG` : `False` (important pour la production)
- `SETUP_SECRET` : Secret pour la création de clés API automatique

### Paiement Stripe
- `STRIPE_PUBLIC_KEY` : Clé publique Stripe (pk_live_...)
- `STRIPE_SECRET_KEY` : Clé secrète Stripe (sk_live_...)
- `STRIPE_WEBHOOK_SECRET` : Secret webhook Stripe (whsec_...)

### Paiement PayPal
- `PAYPAL_CLIENT_ID` : Client ID PayPal
- `PAYPAL_CLIENT_SECRET` : Secret client PayPal
- `PAYPAL_MODE` : `sandbox` (test) ou `live` (production)

### Base de données (IMPORTANT - utilisez la base de données Dokploy)
- `DATABASE_URL` : **L'URL fournie par Dokploy** après création de la base de données PostgreSQL
  - Format : `postgresql://username:password@host:port/database`
  - Exemple : `postgresql://forex_user:password123@postgres-dokploy:5432/forex_db`

**Pour créer la base de données dans Dokploy :**
1. Allez dans la section "Databases" de Dokploy
2. Cliquez sur "Create Database" → "PostgreSQL"
3. Choisissez la version 15
4. Nommez-la `forex_db`
5. Dokploy vous fournira l'URL de connexion complète
6. Copiez cette URL dans la variable `DATABASE_URL`

### Configuration serveur
- `ALLOWED_HOSTS` : Votre domaine (ex: `api.votre-entreprise.com`)
- `PORT` : `8000`

### Cache et files d'attente
- `REDIS_URL` : `redis://redis:6379/0`
- `USE_REDIS` : `True`
- `CELERY_RESULT_BACKEND` : `redis://redis:6379/1`
- `RABBITMQ_URL` : `amqp://guest:guest@rabbitmq:5672//`

### CORS
- `CORS_ALLOWED_ORIGINS` : `https://votre-domaine.com`

## Services à déployer

### 1. Service principal (app)
- **Type** : Web service
- **Port** : 8000
- **Health check** : `/api/v1/health/`
- **Commande de démarrage** : `gunicorn forex_platform.wsgi:application --bind 0.0.0.0:8000`

### 2. Service Celery Worker
- **Type** : Worker service
- **Commande** : `celery -A forex_platform worker --loglevel=info`

### 3. Service Celery Beat
- **Type** : Worker service
- **Commande** : `celery -A forex_platform beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

## Bases de données

### PostgreSQL
- **Type** : PostgreSQL
- **Version** : 15
- **Nom** : db

### Redis
- **Type** : Redis
- **Version** : 7
- **Nom** : redis

## Configuration du domaine

1. Ajoutez votre domaine dans Dokploy
2. Configurez le SSL (Let's Encrypt)
3. Pointez le domaine vers le service principal (port 8000)

## Premiers pas après déploiement

1. **Accéder au dashboard admin** :
   - URL : `https://votre-domaine.com/admin/`
   - Créez un superutilisateur : `docker exec -it <container> python manage.py createsuperuser`

2. **Créer un compte utilisateur** :
   - URL : `https://votre-domaine.com/register/`
   - L'utilisateur recevra automatiquement un abonnement Free et une clé API

3. **Obtenir une clé API via setup** :
   - URL : `https://votre-domaine.com/api/v1/setup/create-key/?secret=VOTRE_SETUP_SECRET`
   - Conservez la clé générée

4. **Documentation API** :
   - URL : `https://votre-domaine.com/api/v1/docs/`

## Gestion des abonnements et paiements

Via le dashboard admin Django :
- Gérez les utilisateurs
- Modifiez les abonnements (Free → Standard → Premium → Partner)
- Activez/désactivez les clés API
- **Gérez les paiements manuels** : Marquez les paiements comme complétés pour activer les comptes
- Surveillez les logs d'audit

### Flux de paiement manuel (admin)
1. L'utilisateur choisit "Paiement manuel" sur la page de paiement
2. Un paiement en statut "pending" est créé
3. L'admin voit le paiement dans le dashboard
4. L'admin marque le paiement comme "complété"
5. L'abonnement est automatiquement activé
6. La clé API est générée automatiquement

## Sécurité

- Changez tous les mots de passe par défaut
- Utilisez des clés fortes pour SECRET_KEY et SETUP_SECRET
- Activez le SSL
- Configurez les règles de pare-feu
- Surveillez les logs d'audit