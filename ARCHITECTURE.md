# Architecture — ForexPlatform API

Document technique expliquant le fonctionnement complet du système : conteneurs, flux de requêtes, authentification, paiements, pipeline de données forex.

---

## 1. Vue d'ensemble

ForexPlatform est une API SaaS de taux de change. Un client s'inscrit, choisit un plan, paie (Stripe/PayPal/manuel), reçoit une clé API, et interroge les endpoints de taux/conversion avec quota horaire selon son plan.

```
                        ┌─────────────────────────────────────────────┐
   Client (web/mobile)  │              VPS / Dokploy                  │
         │              │                                             │
         ▼ HTTPS        │   Traefik (dokploy-network)                 │
   api-forexplatform.   │        │                                    │
   sendbid.app          │        ▼ :443→80                            │
         │              │   ┌─────────────────────────────────────┐   │
         └─────────────►│   │ nginx:80 (reverse proxy + headers   │   │
                        │   │           sécurité + rate limit 20r/m)│  │
                        │   └──────────────┬──────────────────────┘   │
                        │                  ▼ :8000                    │
                        │   ┌─────────────────────────────────────┐   │
                        │   │ app — conteneur supervisord         │   │
                        │   │  ├─ gunicorn (2 workers, Django)    │   │
                        │   │  ├─ celery worker (2 processus)     │   │
                        │   │  └─ celery beat (planificateur)     │   │
                        │   └──┬───────────┬───────────┬──────────┘   │
                        │      ▼           ▼           ▼              │
                        │   ┌──────┐   ┌───────┐   ┌──────────┐       │
                        │   │  db  │   │ redis │   │ rabbitmq │       │
                        │   │ Pg15 │   │  7    │   │    3     │       │
                        │   └──────┘   └───────┘   └──────────┘       │
                        └─────────────────────────────────────────────┘
                                         │
                                         ▼ HTTPS sortant (sync)
                              frankfurter.app (BCE) + providers
```

---

## 2. Les conteneurs (`docker-compose.yml`)

| Conteneur | Rôle | Détail |
|---|---|---|
| `app` | Tout le backend | `supervisord` lance 3 processus : **gunicorn** (HTTP, 2 workers, timeout 120s), **celery worker** (tâches async, 2 processus), **celery beat** (planificateur, DatabaseScheduler) |
| `db` | PostgreSQL 15 Alpine | Données persistées dans volume `db_data`. Users, clés hashées, abonnements, paiements, taux, wallets, audit logs |
| `redis` | Redis 7 | Cache des taux (TTL 300s) + backend de résultats Celery |
| `rabbitmq` | RabbitMQ 3 | Broker de messages Celery (file de tâches) |
| `nginx` | Nginx Alpine | Reverse proxy → `app:8000`, headers de sécurité, rate limiting 20 req/min sur `/api/` |

**Choix clé** : les 3 processus Python tournent dans UN conteneur via `supervisord` (pas 3 services séparés). Plus simple à déployer sur Dokploy — un seul service à gérer.

---

## 3. Cycle de démarrage (`docker/entrypoint.sh`)

À chaque déploiement, l'entrypoint orchestre l'initialisation — **uniquement pour le processus supervisord** (les workers passeraient sinon migrate en parallèle) :

```
1. unset DATABASE_URL          → neutralise la DB externe injectée par Dokploy
2. SECRET_KEY vide ?           → génère une clé éphémère (warning)
3. `db` résolvable ?           → oui : force DB_* vers PostgreSQL bundled
                                  non : fallback SQLite (dev local)
4. Si supervisord :
   ├── migrate (retry ×15, attend que Postgres démarre)
   ├── collectstatic
   ├── loaddata currencies     → 36 devises
   ├── seed_forex              → providers + crons Celery
   ├── sync_all_rates()        → première synchro immédiate
   └── setup_admin             → superuser via env, ou 1er inscrit promu
5. exec supervisord → gunicorn + worker + beat
```

**Résultat** : déploiement zéro-touch. Le serveur arrive "prêt" : base migrée, devises chargées, providers créés, taux déjà syncés, admin existant.

---

## 4. Flux d'une requête API

```
GET /api/v1/rates/USD/EUR/   +   X-API-KEY: fxp_...
        │
        ▼ nginx (limit 20r/m, headers)
        ▼ gunicorn → Django middleware
        │
  ┌─ RateLimitMiddleware (apps/api_gateway/middleware.py)
  │    ├── Route exemptée (/health/, /docs/, /admin/) ? → passe
  │    ├── X-API-KEY présent ?
  │    │      ├── hash SHA-256 → lookup APIClient.is_active
  │    │      ├── compteur `rl:client:{id}:{heure}` vs quota du plan
  │    │      └── pose request.api_client (pour l'audit)
  │    └── sinon → compteur `rl:anon:{ip}:{heure}` vs 20/h
  │         quota dépassé → 429
  │
  ┌─ APIKeyAuthentication (DRF)
  │      valide la clé → request.user = client.user
  │      APIClient.total_requests += 1
  │
  ┌─ ExchangeRateDetailView (apps/forex/views.py)
  │      get_live_rate() → cache ? DB ? inverse ? cross ? provider ?
  │      → réponse JSON
  │
  └─ Middleware (sortie)
       écrit AuditLog {client, endpoint, status, temps, ip}
```

### Authentification — 2 modes

| Header | Cas d'usage |
|---|---|
| `X-API-KEY: fxp_...` | Clients API (serveurs, apps mobiles) — quota horaire |
| `Authorization: Bearer <JWT>` | Dashboard/session utilisateur — SimpleJWT |

La clé API n'est **jamais stockée en clair** : SHA-256 en base, préfixe `fxp_xxxx` affiché, clé complète montrée une seule fois à la génération.

### Rate limiting — 2 niveaux

| Niveau | Qui | Quota |
|---|---|---|
| nginx | toutes IP | 20 req/min burst 10 sur `/api/` |
| Django middleware | anonyme par IP | 20 req/h |
| Django middleware | clé API par client | quota du plan : 100 / 1 000 / 5 000 / 50 000 req/h |

---

## 5. Pipeline de données forex

### Sync (toutes les 15 min — Celery beat)

```
seed_forex crée :
  ├── ForexProvider "ECB"      → api.frankfurter.app, gratis, sans clé
  ├── ForexProvider optionnels → si EXCHANGERATE_API_KEY / FIXER / OXR renseignés
  └── PeriodicTasks            → sync 15 min · stale 30 min · archive quotidien

sync_all_rates() :
  for chaque provider actif :
      HTTP GET → parse → pour chaque devise :
          ExchangeRate.update_or_create(EUR→devise)
  + parités fixes officielles : EUR→XAF 655.957 · EUR→XOF 655.957 · EUR→KMF 491.9678
```

### Lecture d'un taux (`get_live_rate` — ordre de fallback)

```
1. Cache Redis (TTL FOREX_CACHE_TTL=300s)
2. DB : ExchangeRate(base→target) récent
3. DB inverse : 1/rate(target→base)
4. Taux croisé : EUR→FROM et EUR→TO connus → rate = EUR→TO / EUR→FROM
   ex: USD→XAF = 655.957 / 1.1380
5. Provider externe en live (timeout 3s) → stocke en DB
6. Dernier taux en DB même stale
```

→ **Toute paire fonctionne** même si seule la BCE EUR-based est en base. USD/EUR, CAD/XAF, GBP/JPY…

### Conversion (`/convert/`)

```
converted = amount × market_rate
fee       = converted × spread(tier)      ← revenu business
final     = converted - fee               ← ce que le client reçoit
```

Spreads : free 2.5% · standard 1.5% · premium 1.0% · partner 0.5%

---

## 6. Flux de paiement

```
Client /subscription/ → "S'abonner" → /payment/?plan=X
        │
        ▼ POST payment_view (plan validé contre whitelist)
        │
   ┌────┼─────────────┬──────────────┐
   │    │             │              │
   ▼ free           ▼ stripe      ▼ paypal        ▼ manual
 activation    Payment(pending)  Payment(pending) Payment(pending)
 immédiate         │                │             │
 + clé API    Stripe Checkout   PayPal Order   Email admin
              (session hébergée) (approve_url)  │
                  │                │             ▼
        ┌─────────┴──────┐         │        Admin /admin/
        ▼                ▼         │        "Marquer complété"
   return /success   webhook      ▼             │
   + session_id   /api/v1/    return paypal/    │
   → verify       webhooks/     → capture       │
   côté serveur   stripe/       côté serveur    │
        │         (signature        │           │
        │          vérifiée)        │           │
        └──────────┴────────────────┴───────────┘
                   ▼
        Payment.mark_completed()
            ├── status = 'completed'
            ├── subscription.plan = X, is_active=True
            ├── génère clé API tier=plan
            ├── email "paiement confirmé"
            └── AuditLog
```

**Sécurité** : le succès n'est jamais accordé sur simple retour navigateur — `verify_stripe_session`/`capture_paypal_order` interrogent l'API du provider. Le webhook signé couvre le cas où le client ferme son navigateur avant le retour.

---

## 7. Wallets & transferts (`apps/transfers`)

```
Wallet(user, currency, balance, reserved_balance)
WalletTransaction(type, amount, balance_before, balance_after, reference)
Transfer(user, from_wallet→to_wallet, rate_used, status)

Endpoints :
  GET/POST /wallets/              → créer/lister ses wallets
  GET /wallets/{code}/transactions/ → relevé
  POST /transfers/create/         → convertir entre ses wallets
                                    via get_live_rate (cross-rates OK)
  POST /wallets/credit/           → [ADMIN] crédite le wallet d'un client
                                    après réception réelle de fonds
```

Tout mouvement = transaction tracée avec soldes avant/après → auditabilité comptable.

---

## 8. Structure Django

```
forex_platform/
├── forex_platform/
│   ├── settings.py        ← toute la config vient de os.getenv()
│   └── urls.py            ← pages web + admin + /api/v1/
├── apps/
│   ├── core/              ← Currency (fixture : 36 devises)
│   ├── forex/             ← ForexProvider, ExchangeRate, HistoricalRate
│   │   ├── services.py    ← get_live_rate + chaîne de fallback
│   │   ├── tasks.py       ← sync_all_rates, mark_stale, archive OHLC
│   │   └── management/commands/seed_forex.py
│   ├── api_gateway/       ← APIClient, Subscription, Payment, AuditLog
│   │   ├── authentication.py  ← X-API-KEY → SHA-256 → user
│   │   ├── middleware.py      ← rate limit + audit log
│   │   ├── payments.py        ← Stripe Checkout + PayPal Orders v2
│   │   ├── emails.py          ← welcome / confirmé / manuel
│   │   ├── views.py           ← pages web + API clés + paiements
│   │   └── management/commands/setup_admin.py
│   └── transfers/         ← Wallet, WalletTransaction, Transfer
├── templates/             ← home FR/EN, docs, dashboard, auth, payment
├── docker/                ← entrypoint.sh + supervisord.conf
└── nginx/                 ← reverse proxy
```

---

## 9. Variables d'environnement → comportement

| Variable | Défaut | Effet si vide/absente |
|---|---|---|
| `SECRET_KEY` | — | Clé éphémère générée (sessions perdues au restart) |
| `DEBUG` | `False` | — |
| `ALLOWED_HOSTS` | domaine prod + localhost | `DEBUG=False` + mauvais host = 400 partout |
| `STRIPE_*` | vide | Méthode "carte" → erreur propre + suggestion manuel |
| `PAYPAL_*`, `PAYPAL_SANDBOX` | vide / `False` | Idem ; `False` = API live PayPal |
| `EMAIL_*` | vide | Emails silencieusement désactivés, pas de crash |
| `*_API_KEY` forex | vide | BCE seule — fonctionne, taux quotidiens |
| `DJANGO_SUPERUSER_*` | vide | 1er utilisateur inscrit promu admin |
| `DB_*`, `REDIS_URL`, `RABBITMQ_URL` | forcés par compose | Ne pas configurer — gérés en interne |

---

## 10. Sécurité — résumé des mécanismes

| Mécanisme | Implémentation |
|---|---|
| Clés API | SHA-256, affichage unique, révocation (jamais suppression) |
| Tier | Dérivé de l'abonnement — jamais du client |
| Webhook Stripe | Signature `whsec_` vérifiée |
| Paiement | Confirmation serveur-à-serveur, pas de confiance au retour navigateur |
| Rate limit | nginx 20r/m + middleware par IP/clé + exempts health/docs |
| Admin | Premier inscrit promu OU `DJANGO_SUPERUSER_*` — sinon personne |
| Migrations | Uniquement le conteneur principal (pas de race condition) |
| Secrets | Tout en env, rien en dur, `.env` hors du repo/image |
