# ForexPlatform API

API SaaS de taux de change — données réelles (BCE + providers de marché), abonnements par quota, clés API sécurisées, paiements Stripe/PayPal, dashboard client et admin Django.

**Production :** https://api-forexplatform.sendbid.app

---

## 🏗️ Architecture

```
Client (web/mobile/backend)
        │
        ▼
Traefik (Dokploy) → nginx:80 / app:8000
        │
   Django + Gunicorn ──┬── PostgreSQL (données, taux, users)
        │              ├── Redis (cache + résultats Celery)
        │              └── RabbitMQ (broker Celery)
        │
   supervisord lance dans `app` :
   gunicorn + celery worker + celery beat
```

Services : `app`, `db`, `redis`, `rabbitmq`, `nginx` — tout est dans `docker-compose.yml`.

---

## ✨ Fonctionnalités

### Site public
- Landing page FR (`/`) et EN (`/?lang=en`) — ticker de taux **réels**, tarifs, FAQ
- Inscription (`/register/`), connexion (`/login/`), documentation client (`/docs/`)

### Espace client (`/dashboard/`)
- Plan + quota horaire + requêtes totales (barre de progression)
- Clés API : génération nommée, affichage unique, révocation
- Taux en direct (refresh auto 60s) + historique des paiements

### Paiements
- **Stripe Checkout** — redirection vers la page hébergée, webhook signé `/api/v1/webhooks/stripe/`
- **PayPal Orders v2** — approbation puis capture au retour
- **Manuel** — demande → validation admin → activation automatique

### API REST (`/api/v1/`)
- Auth par header `X-API-KEY: fxp_...` (hashée SHA-256, jamais stockée en clair)
- Quota horaire par plan, taux croisés automatiques (toute base), conversion avec spread
- Docs interactives : Swagger `/api/docs/` · ReDoc `/api/redoc/`

### Admin Django (`/admin/`)
- Utilisateurs, clés API, abonnements, paiements, audit log
- Actions en masse : activer abonnements, compléter paiements
- Le **premier utilisateur inscrit** devient superadmin automatiquement au déploiement

---

## 💱 Données forex

| Source | Fraîcheur | Clé requise |
|---|---|---|
| BCE (frankfurter.app) | Quotidien officiel | Non — gratuit |
| ExchangeRate-API | ~horaire | `EXCHANGERATE_API_KEY` |
| Open Exchange Rates | ~horaire | `OPENEXCHANGERATES_APP_ID` |
| Fixer.io | ~horaire | `FIXER_API_KEY` |

- Sync toutes les **15 min** via Celery beat, marquage "stale" après 2h, archivage OHLC quotidien
- **36 devises** dont XAF/XOF/KMF (parité EUR officielle fixe : 655,957 / 491,9678)
- Fallback : cache Redis → DB → providers live → taux croisés/inverses calculés

---

## 🔌 Utilisation API

```bash
# Sans clé — démo publique
curl https://api-forexplatform.sendbid.app/api/v1/demo/

# Avec clé
curl -H "X-API-KEY: fxp_votre_cle" \
     https://api-forexplatform.sendbid.app/api/v1/rates/USD/EUR/

# Conversion
curl -X POST -H "X-API-KEY: fxp_votre_cle" \
     -H "Content-Type: application/json" \
     -d '{"from_currency":"CAD","to_currency":"XAF","amount":100}' \
     https://api-forexplatform.sendbid.app/api/v1/convert/
```

Endpoints : `health`, `demo`, `currencies` (publics) · `rates`, `convert`, `history`, `wallets`, `transfers` (clé requise) · `api-keys` (JWT) · `webhooks/stripe` · `wallets/credit` (admin).

Collection Postman : `postman_collection.json` à la racine.

---

## 🚀 Déploiement Dokploy

1. **Créer l'app** → type Docker Compose → repo Git, fichier `docker-compose.yml`
2. **Domaine** → service `app`, port `8000`, path `/`, HTTPS ✓
3. **Variables d'environnement** (voir `.env.example`) :

| Variable | Obligatoire | Rôle |
|---|---|---|
| `SECRET_KEY` | ✅ | 50+ caractères aléatoires |
| `DEBUG` | ✅ | `False` en production |
| `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` | Paiement carte | Stripe Checkout |
| `PAYPAL_CLIENT_ID` + `PAYPAL_CLIENT_SECRET` | PayPal | Orders v2 |
| `EMAIL_HOST` + user/pass | Emails | Notifications clients |
| `EXCHANGERATE_API_KEY` | Optionnel | Taux plus frais que BCE |
| `DJANGO_SUPERUSER_*` | Optionnel | Force un compte admin précis |

4. **Deploy** → l'entrypoint fait tout : migrations, collectstatic, fixtures devises, seed providers + crons, première sync, promotion admin.

### Webhook Stripe à déclarer
```
URL : https://api-forexplatform.sendbid.app/api/v1/webhooks/stripe/
Événement : checkout.session.completed
```

---

## 🛠️ Développement local

```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
cd forex_platform
python manage.py migrate
python manage.py loaddata currencies
python manage.py seed_forex
python manage.py createsuperuser
python manage.py runserver
```

---

## 📁 Structure

```
├── docker-compose.yml          # Stack Dokploy (app, db, redis, rabbitmq, nginx)
├── docker/entrypoint.sh        # Orchestration démarrage (migrate, seed, sync, admin)
├── nginx/nginx.conf            # Proxy → app:8000
├── postman_collection.json     # Tests API prêts à l'emploi
├── templates/                  # home FR/EN, docs, dashboard, auth, paiement
└── forex_platform/
    ├── apps/api_gateway/       # Auth clés, quotas, audit, paiements, UI
    │   ├── payments.py         # Stripe Checkout + PayPal Orders v2
    │   ├── emails.py           # Notifications (welcome, paiement, manuel)
    │   ├── middleware.py       # Rate limiting + audit log
    │   └── management/commands/setup_admin.py  # auto-superuser
    ├── apps/forex/             # Providers, taux, conversion, tasks Celery
    ├── apps/transfers/         # Wallets multi-devises + transferts
    └── apps/core/              # Devises (fixture 36 devises)
```

## 🔒 Sécurité

- Clés API hashées SHA-256 — affichées **une seule fois**
- Quotas serveur par tier — le client ne peut pas choisir son tier
- Webhook Stripe avec vérification de signature
- Rate limiting : 20/h anonyme (par IP), quota du plan pour les clés
- `DEBUG=False`, `SECRET_KEY` via env, CSRF + `ALLOWED_HOSTS` configurés
