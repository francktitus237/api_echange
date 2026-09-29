# Configuration Dokploy — ForexPlatform API

## Architecture déployée

`docker-compose.yml` contient tout : `app` (Gunicorn + Celery via supervisord), `db` (PostgreSQL 15), `redis`, `rabbitmq`, `nginx`.

```
Domaine → Traefik Dokploy → app:8000 → Django
```

## Variables d'environnement (Dokploy → Environment)

### Obligatoires

| Variable | Valeur |
|---|---|
| `SECRET_KEY` | Chaîne aléatoire 50+ caractères (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DEBUG` | `False` |
| `SITE_URL` | `https://api-forexplatform.sendbid.app` |

### Paiements (optionnel — sans clés, seul le paiement manuel fonctionne)

| Variable | Source |
|---|---|
| `STRIPE_SECRET_KEY` | dashboard.stripe.com → API keys (`sk_live_...`) |
| `STRIPE_PUBLISHABLE_KEY` | idem (`pk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe → Webhooks → après création (`whsec_...`) |
| `PAYPAL_CLIENT_ID` | developer.paypal.com → app REST |
| `PAYPAL_CLIENT_SECRET` | idem |
| `PAYPAL_SANDBOX` | `True` pour tester, `False` en production |

### Forex (optionnel — la BCE est gratuite sans clé)

| Variable | Effet |
|---|---|
| `EXCHANGERATE_API_KEY` | Taux plus fréquents (compte gratuit sur exchangerate-api.com) |
| `OPENEXCHANGERATES_APP_ID` | Provider supplémentaire |
| `FIXER_API_KEY` | Provider supplémentaire |

### Emails (optionnel — notifications bienvenue/paiement)

`EMAIL_HOST`, `EMAIL_PORT` (587), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`

### Admin (optionnel)

`DJANGO_SUPERUSER_USERNAME` + `DJANGO_SUPERUSER_PASSWORD` + `DJANGO_SUPERUSER_EMAIL`
→ crée ou promeut ce compte en superuser à chaque déploiement.
**Sans ces variables** : le premier utilisateur inscrit via `/register/` devient admin automatiquement.

## Domaine

Dans Dokploy → Domains :

| Champ | Valeur |
|---|---|
| Service | `app` |
| Port | `8000` |
| Path | `/` |
| HTTPS | activé |

## Webhook Stripe

Dans dashboard.stripe.com → Developers → Webhooks :

- **URL** : `https://api-forexplatform.sendbid.app/api/v1/webhooks/stripe/`
- **Événement** : `checkout.session.completed`
- Copier le "Signing secret" → `STRIPE_WEBHOOK_SECRET`

## Vérification post-déploiement

```bash
# Santé
curl https://api-forexplatform.sendbid.app/api/v1/health/

# Taux réels (public)
curl https://api-forexplatform.sendbid.app/api/v1/demo/
```

Logs `app` attendus :
```
=== Using bundled PostgreSQL (db) ===
=== Applying migrations ===
=== Seeding forex providers & schedules ===
=== Superuser setup ===
[INFO] Listening at: http://0.0.0.0:8000
```

## Flux de paiement

| Méthode | Flux |
|---|---|
| **Stripe** | Client → Checkout Stripe → webhook/return → `mark_completed()` → abonnement actif + clé API + email |
| **PayPal** | Client → approbation PayPal → capture au retour → idem |
| **Manuel** | Client demande → admin valide dans `/admin/` (action "compléter") → idem |
| **Free** | Activation immédiate, aucun paiement |

## Sécurité

- Clés API hashées SHA-256, affichées une seule fois
- Quota horaire par plan, appliqué côté serveur
- Rate limiting : 20 req/h anonyme, quota du plan pour les clés
- Webhook Stripe vérifié par signature
- Changez les mots de passe par défaut dans le compose pour la production
