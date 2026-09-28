# ForexPlatform API - Guide de Production

## 🎯 Vue d'ensemble

ForexPlatform API est une solution complète pour les taux de change en temps réel avec :
- Système d'abonnement par niveaux (Free, Standard, Premium, Partner)
- Gestion des clés API sécurisées
- Dashboard admin Django pour la gestion
- Interface utilisateur pour inscription et souscription
- Configuration prête pour le déploiement Dokploy

## 🚀 Déploiement sur Dokploy

### Variables d'environnement

Configurez ces variables dans l'interface Dokploy :

```bash
# Sécurité
SECRET_KEY=votre_clé_secrète_django_ici
DEBUG=False
SETUP_SECRET=votre_secret_pour_setup_api

# Base de données
DB_NAME=forex_db
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe_postgres
DB_HOST=db
DB_PORT=5432
USE_SQLITE=False

# Serveur
ALLOWED_HOSTS=votre-domaine.com
PORT=8000

# Cache et files d'attente
REDIS_URL=redis://redis:6379/0
USE_REDIS=True
CELERY_RESULT_BACKEND=redis://redis:6379/1
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//

# CORS
CORS_ALLOWED_ORIGINS=https://votre-domaine.com
```

### Services Docker

Utilisez le fichier `docker-compose.dokploy.yml` qui inclut :
- **app** : Application Django principale
- **celery_worker** : Worker pour les tâches asynchrones
- **celery_beat** : Planificateur de tâches
- **db** : PostgreSQL 15
- **redis** : Redis 7
- **rabbitmq** : RabbitMQ pour la messagerie

## 👥 Gestion des utilisateurs

### Inscription des utilisateurs

Les utilisateurs peuvent s'inscrire via : `https://votre-domaine.com/register/`

Lors de l'inscription :
- Un compte utilisateur est créé
- Un abonnement Free est automatiquement attribué
- Une clé API est générée automatiquement

### Dashboard Admin Django

Accédez au dashboard via : `https://votre-domaine.com/admin/`

**Fonctionnalités disponibles :**
- Gestion des utilisateurs
- Gestion des abonnements (plan, statut, dates)
- Gestion des clés API (création, suppression, activation)
- Visualisation des logs d'audit
- Actions groupées (activer/annuler des abonnements)

## 🔑 Configuration API pour les clients

### Pour vos clients (utilisateurs de l'API)

**Processus simple :**

1. **Créer un compte** : `https://votre-domaine.com/register/`
2. **Choisir un abonnement** : `https://votre-domaine.com/subscription/`
3. **Récupérer la clé API** : Affichée dans l'interface abonnement

**Configuration dans leur projet :**

```python
# Exemple Python
import requests

headers = {
    'X-API-KEY': 'fxp_leur_clé_api_ici'
}

response = requests.get(
    'https://votre-domaine.com/api/v1/rates/EUR/USD/',
    headers=headers
)
```

```javascript
// Exemple JavaScript
fetch('https://votre-domaine.com/api/v1/rates/EUR/USD/', {
    headers: {
        'X-API-KEY': 'fxp_leur_clé_api_ici'
    }
})
```

## 📊 Plans d'abonnement

| Plan | Prix | Requêtes/heure | Fonctionnalités |
|------|------|----------------|-----------------|
| Free | 0€ | 100 | Taux en temps réel, support email |
| Standard | 9.99€/mois | 1 000 | + Support prioritaire, historique 30j |
| Premium | 29.99€/mois | 5 000 | + Support 24/7, historique 90j, API avancée |
| Partner | 99.99€/mois | 50 000 | + Historique illimité, API personnalisée, SLA |

## 🔧 Documentation API

- **Documentation interactive** : `https://votre-domaine.com/api/v1/docs/`
- **Health check** : `https://votre-domaine.com/api/v1/health/`
- **Documentation HTML** : `https://votre-domaine.com/api/v1/docs/`

## 🛡️ Sécurité

- Clés API hachées avec SHA-256
- Authentification JWT pour les endpoints utilisateurs
- Rate limiting par tier d'abonnement
- Logs d'audit complets
- CORS configuré pour votre domaine

## 📈 Monitoring

### Logs d'audit
Surveillez via le dashboard admin :
- Requêtes API par client
- Codes de réponse
- Temps de réponse
- Adresses IP

### Health checks
- Base de données PostgreSQL
- Cache Redis
- Service API

## 🔄 Mises à jour

### Pour appliquer les migrations après les changements :

```bash
docker-compose exec app python manage.py migrate
```

### Pour créer un superutilisateur admin :

```bash
docker-compose exec app python manage.py createsuperuser
```

## 🆘 Support

En cas de problème :
1. Vérifiez les logs des conteneurs
2. Consultez le dashboard admin
3. Vérifiez les variables d'environnement
4. Testez le health check

## 📝 Fichiers importants

- `docker-compose.dokploy.yml` : Configuration Docker pour Dokploy
- `DOKPLOY_CONFIG.md` : Guide détaillé de configuration Dokploy
- `.env` : Variables d'environnement locales
- `.dockerignore` : Fichiers exclus de l'image Docker
- `.gitignore` : Fichiers exclus du versioning