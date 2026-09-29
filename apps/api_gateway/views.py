import os
from django.utils.timezone import now
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from .models import APIClient, Subscription, Payment
from apps.forex.models import ExchangeRate


class DocsHTMLView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        base_url = request.build_absolute_uri('/api/v1').rstrip('/')
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ForexPlatform API - Documentation</title>
<style>
  :root {{ --primary: #2563eb; --green: #16a34a; --orange: #ea580c; --red: #dc2626; --gray: #f8fafc; --border: #e2e8f0; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f1f5f9; color: #1e293b; }}
  header {{ background: linear-gradient(135deg, #1e3a8a, #2563eb); color: white; padding: 40px 24px; text-align: center; }}
  header h1 {{ font-size: 2rem; font-weight: 800; }}
  header p {{ margin-top: 8px; opacity: .85; font-size: 1.05rem; }}
  .badge {{ display: inline-block; background: #22c55e; color: white; padding: 4px 12px; border-radius: 999px; font-size: .8rem; font-weight: 700; margin-top: 10px; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 32px 16px; }}
  .base-url-box {{ background: #1e293b; color: #7dd3fc; padding: 16px 20px; border-radius: 10px; font-family: monospace; font-size: 1rem; margin-bottom: 32px; display: flex; align-items: center; gap: 12px; }}
  .base-url-box span {{ color: #94a3b8; font-size: .85rem; }}
  section {{ margin-bottom: 40px; }}
  section h2 {{ font-size: 1.3rem; font-weight: 700; border-left: 4px solid var(--primary); padding-left: 12px; margin-bottom: 16px; color: #0f172a; }}
  .endpoint {{ background: white; border: 1px solid var(--border); border-radius: 10px; margin-bottom: 14px; overflow: hidden; }}
  .endpoint-header {{ display: flex; align-items: center; gap: 12px; padding: 14px 18px; cursor: pointer; }}
  .method {{ font-weight: 800; font-size: .8rem; padding: 4px 10px; border-radius: 6px; min-width: 56px; text-align: center; }}
  .GET {{ background: #dbeafe; color: #1d4ed8; }}
  .POST {{ background: #dcfce7; color: #15803d; }}
  .DELETE {{ background: #fee2e2; color: #b91c1c; }}
  .endpoint-header .path {{ font-family: monospace; font-size: .95rem; font-weight: 600; color: #0f172a; flex: 1; }}
  .auth-badge {{ font-size: .72rem; padding: 3px 8px; border-radius: 999px; font-weight: 600; }}
  .auth-open {{ background: #fef9c3; color: #854d0e; }}
  .auth-key {{ background: #ede9fe; color: #5b21b6; }}
  .auth-jwt {{ background: #fce7f3; color: #9d174d; }}
  .endpoint-body {{ border-top: 1px solid var(--border); padding: 18px; display: none; }}
  .endpoint-body.open {{ display: block; }}
  .desc {{ color: #475569; margin-bottom: 14px; font-size: .93rem; }}
  .label {{ font-size: .78rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 6px; }}
  pre {{ background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 8px; font-size: .82rem; overflow-x: auto; margin-bottom: 12px; line-height: 1.6; }}
  .key-green {{ color: #86efac; }}
  .key-blue {{ color: #93c5fd; }}
  .key-orange {{ color: #fcd34d; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  @media(max-width:600px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
  .info-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; font-size: .88rem; color: #1e40af; margin-bottom: 16px; }}
  .info-box strong {{ display: block; margin-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th {{ background: #f8fafc; text-align: left; padding: 10px 14px; border-bottom: 2px solid var(--border); font-weight: 700; color: #475569; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  .tag-r {{ color: #dc2626; font-weight: 700; }}
  .tag-o {{ color: #ea580c; font-weight: 700; }}
  footer {{ text-align: center; padding: 32px; color: #94a3b8; font-size: .85rem; }}
  .copy-btn {{ background: #2563eb; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: .8rem; float: right; }}
  .copy-btn:hover {{ background: #1d4ed8; }}
</style>
</head>
<body>
<header>
  <h1>💱 ForexPlatform API</h1>
  <p>Documentation officielle — Taux de change en temps réel</p>
  <span class="badge">✅ API en ligne — v1.0.0</span>
</header>
<div class="container">

  <div class="base-url-box">
    <span>BASE URL</span>
    <strong id="baseurl">{base_url}</strong>
    <button class="copy-btn" onclick="navigator.clipboard.writeText('{base_url}');this.textContent='✓ Copié'">Copier</button>
  </div>

  <div class="info-box">
    <strong>Authentification</strong>
    Ajouter le header <code>X-API-KEY: votre-clé</code> à chaque requête protégée.<br>
    Pour obtenir une clé : créez un compte sur <a href="/register/">/register/</a> puis gérez vos clés depuis le <a href="/dashboard/">dashboard</a>.
  </div>

  <!-- ===== PUBLICS ===== -->
  <section>
    <h2>🌍 Endpoints publics (sans auth)</h2>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/health/</span>
        <span class="auth-badge auth-open">Public</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Vérifie que l'API, la base de données et le cache fonctionnent.</p>
        <div class="label">Exemple de réponse</div>
        <pre>{{\n  <span class="key-green">"status"</span>: <span class="key-orange">"ok"</span>,\n  <span class="key-green">"service"</span>: <span class="key-orange">"ForexPlatform API"</span>,\n  <span class="key-green">"version"</span>: <span class="key-orange">"1.0.0"</span>,\n  <span class="key-green">"checks"</span>: {{ <span class="key-green">"database"</span>: <span class="key-orange">"ok"</span>, <span class="key-green">"cache"</span>: <span class="key-orange">"ok"</span> }}\n}}</pre>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/currencies/</span>
        <span class="auth-badge auth-open">Public</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Liste les 33 devises disponibles avec leur code, nom, symbole et drapeau.</p>
        <div class="label">Exemple de réponse</div>
        <pre>{{\n  <span class="key-green">"success"</span>: true,\n  <span class="key-green">"count"</span>: 33,\n  <span class="key-green">"currencies"</span>: [\n    {{ <span class="key-green">"code"</span>: <span class="key-orange">"EUR"</span>, <span class="key-green">"name"</span>: <span class="key-orange">"Euro"</span>, <span class="key-green">"symbol"</span>: <span class="key-orange">"€"</span>, <span class="key-green">"flag"</span>: <span class="key-orange">"🇪🇺"</span> }},\n    {{ <span class="key-green">"code"</span>: <span class="key-orange">"USD"</span>, <span class="key-green">"name"</span>: <span class="key-orange">"US Dollar"</span>, <span class="key-green">"symbol"</span>: <span class="key-orange">"$"</span>, <span class="key-green">"flag"</span>: <span class="key-orange">"🇺🇸"</span> }}\n  ]\n}}</pre>
      </div>
    </div>
  </section>

  <!-- ===== TAUX ===== -->
  <section>
    <h2>💱 Taux de change (X-API-KEY requis)</h2>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/rates/&#123;FROM&#125;/&#123;TO&#125;/</span>
        <span class="auth-badge auth-key">API Key</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Retourne le taux de change en temps réel entre deux devises.</p>
        <div class="label">Paramètres URL</div>
        <table><tr><th>Paramètre</th><th>Exemple</th><th>Description</th></tr>
        <tr><td><code>FROM</code></td><td>EUR</td><td>Devise source (code ISO)</td></tr>
        <tr><td><code>TO</code></td><td>USD</td><td>Devise cible (code ISO)</td></tr></table><br>
        <div class="label">Exemple de requête</div>
        <pre>GET {base_url}/rates/EUR/USD/\nX-API-KEY: fxp_votre_cle</pre>
        <div class="label">Exemple de réponse</div>
        <pre>{{\n  <span class="key-green">"success"</span>: true,\n  <span class="key-green">"source"</span>: <span class="key-orange">"live"</span>,\n  <span class="key-green">"rate"</span>: {{\n    <span class="key-green">"pair"</span>: <span class="key-orange">"EUR/USD"</span>,\n    <span class="key-green">"market_rate"</span>: <span class="key-orange">"1.08520"</span>,\n    <span class="key-green">"timestamp"</span>: <span class="key-orange">"2026-01-01T12:00:00Z"</span>\n  }}\n}}</pre>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/rates/?base=EUR</span>
        <span class="auth-badge auth-key">API Key</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Retourne tous les taux depuis une devise de base (défaut : USD).</p>
        <div class="label">Paramètre query</div>
        <table><tr><th>Param</th><th>Défaut</th><th>Description</th></tr>
        <tr><td><code>base</code></td><td>USD</td><td>Devise de base</td></tr></table><br>
        <div class="label">Exemple</div>
        <pre>GET {base_url}/rates/?base=EUR\nX-API-KEY: fxp_votre_cle</pre>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/history/&#123;FROM&#125;/&#123;TO&#125;/?days=30</span>
        <span class="auth-badge auth-key">API Key</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Historique des taux (max 365 jours) avec OHLC (open, high, low, close).</p>
        <div class="label">Exemple</div>
        <pre>GET {base_url}/history/EUR/USD/?days=7\nX-API-KEY: fxp_votre_cle</pre>
      </div>
    </div>
  </section>

  <!-- ===== CONVERSION ===== -->
  <section>
    <h2>🔄 Conversion</h2>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method POST">POST</span>
        <span class="path">/convert/</span>
        <span class="auth-badge auth-key">API Key</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Convertit un montant d'une devise à une autre avec le taux du marché en temps réel.</p>
        <div class="grid2">
          <div>
            <div class="label">Body (JSON)</div>
            <pre>{{\n  <span class="key-green">"from_currency"</span>: <span class="key-orange">"EUR"</span>,\n  <span class="key-green">"to_currency"</span>: <span class="key-orange">"USD"</span>,\n  <span class="key-green">"amount"</span>: <span class="key-blue">500</span>\n}}</pre>
          </div>
          <div>
            <div class="label">Réponse</div>
            <pre>{{\n  <span class="key-green">"success"</span>: true,\n  <span class="key-green">"conversion"</span>: {{\n    <span class="key-green">"amount"</span>: <span class="key-orange">"500.00"</span>,\n    <span class="key-green">"converted_amount"</span>: <span class="key-orange">"542.60"</span>,\n    <span class="key-green">"market_rate"</span>: <span class="key-orange">"1.0852"</span>,\n    <span class="key-green">"fee_amount"</span>: <span class="key-orange">"8.76"</span>,\n    <span class="key-green">"tier"</span>: <span class="key-orange">"standard"</span>\n  }}\n}}</pre>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== AUTH ===== -->
  <section>
    <h2>🔐 Authentification JWT</h2>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method POST">POST</span>
        <span class="path">/auth/token/</span>
        <span class="auth-badge auth-open">Public</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Obtenir un token JWT avec identifiants utilisateur.</p>
        <div class="label">Body</div>
        <pre>{{ <span class="key-green">"username"</span>: <span class="key-orange">"user"</span>, <span class="key-green">"password"</span>: <span class="key-orange">"password"</span> }}</pre>
        <div class="label">Réponse</div>
        <pre>{{ <span class="key-green">"access"</span>: <span class="key-orange">"eyJ..."</span>, <span class="key-green">"refresh"</span>: <span class="key-orange">"eyJ..."</span> }}</pre>
        <div class="label">Utilisation</div>
        <pre>Authorization: Bearer eyJ...</pre>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method POST">POST</span>
        <span class="path">/auth/token/refresh/</span>
        <span class="auth-badge auth-open">Public</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Renouveler un access token avec le refresh token.</p>
        <pre>{{ <span class="key-green">"refresh"</span>: <span class="key-orange">"eyJ..."</span> }}</pre>
      </div>
    </div>
  </section>

  <!-- ===== WALLETS ===== -->
  <section>
    <h2>👛 Wallets &amp; Transferts (JWT requis)</h2>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/wallets/</span>
        <span class="auth-badge auth-jwt">JWT</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Liste tous les wallets de l'utilisateur connecté.</p>
        <pre>Authorization: Bearer eyJ...</pre>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/wallets/&#123;CURRENCY&#125;/transactions/</span>
        <span class="auth-badge auth-jwt">JWT</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Historique des transactions d'un wallet (ex: /wallets/EUR/transactions/).</p>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method POST">POST</span>
        <span class="path">/transfers/create/</span>
        <span class="auth-badge auth-jwt">JWT</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Créer un transfert entre deux utilisateurs avec conversion automatique.</p>
        <div class="label">Body</div>
        <pre>{{\n  <span class="key-green">"recipient_username"</span>: <span class="key-orange">"alice"</span>,\n  <span class="key-green">"source_currency"</span>: <span class="key-orange">"EUR"</span>,\n  <span class="key-green">"destination_currency"</span>: <span class="key-orange">"USD"</span>,\n  <span class="key-green">"amount"</span>: <span class="key-blue">200</span>\n}}</pre>
      </div>
    </div>

    <div class="endpoint">
      <div class="endpoint-header" onclick="toggle(this)">
        <span class="method GET">GET</span>
        <span class="path">/transfers/</span>
        <span class="auth-badge auth-jwt">JWT</span>
      </div>
      <div class="endpoint-body">
        <p class="desc">Liste l'historique des transferts de l'utilisateur connecté.</p>
      </div>
    </div>
  </section>

  <!-- ===== CODES ERREUR ===== -->
  <section>
    <h2>⚠️ Codes d'erreur</h2>
    <table>
      <tr><th>Code</th><th>Signification</th><th>Action</th></tr>
      <tr><td><strong>200</strong></td><td>Succès</td><td>—</td></tr>
      <tr><td><strong>400</strong></td><td>Données invalides</td><td>Vérifier le body de la requête</td></tr>
      <tr><td><strong class="tag-r">401</strong></td><td>Non authentifié</td><td>Vérifier X-API-KEY ou JWT</td></tr>
      <tr><td><strong>403</strong></td><td>Accès refusé</td><td>Secret invalide</td></tr>
      <tr><td><strong>404</strong></td><td>Ressource introuvable</td><td>Vérifier les paramètres</td></tr>
      <tr><td><strong class="tag-o">429</strong></td><td>Quota dépassé</td><td>Attendre ou changer de tier</td></tr>
      <tr><td><strong class="tag-r">503</strong></td><td>Taux indisponible</td><td>Réessayer dans quelques secondes</td></tr>
    </table>
  </section>

  <!-- ===== QUOTAS ===== -->
  <section>
    <h2>📊 Tiers &amp; Quotas</h2>
    <table>
      <tr><th>Tier</th><th>Requêtes/heure</th><th>Spread</th></tr>
      <tr><td>free</td><td>100</td><td>2.5%</td></tr>
      <tr><td><strong>standard</strong></td><td>1 000</td><td>1.5%</td></tr>
      <tr><td>premium</td><td>5 000</td><td>0.8%</td></tr>
      <tr><td>partner</td><td>50 000</td><td>0.3%</td></tr>
    </table>
  </section>

</div>
<footer>ForexPlatform API v1.0.0 — Documentation générée automatiquement — {base_url}</footer>
<script>
  function toggle(el) {{
    const body = el.nextElementSibling;
    body.classList.toggle('open');
  }}
</script>
</body>
</html>"""
        return HttpResponse(html, content_type='text/html')


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok = True
        cache_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False
        try:
            cache.set('health_check', '1', 5)
            cache_ok = cache.get('health_check') == '1'
        except Exception:
            cache_ok = False

        return Response({
            'status': 'ok' if db_ok and cache_ok else 'degraded',
            'service': 'ForexPlatform API',
            'version': '1.0.0',
            'timestamp': now().isoformat(),
            'checks': {
                'database': 'ok' if db_ok else 'error',
                'cache': 'ok' if cache_ok else 'error',
            }
        })


class APIKeyListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keys = APIClient.objects.filter(user=request.user).values(
            'id', 'name', 'api_key_prefix', 'tier',
            'quota_requests_per_hour', 'total_requests',
            'expires_at', 'is_active', 'created_at'
        )
        return Response({'success': True, 'api_keys': list(keys)})


class APIKeyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'success': False, 'error': 'Name is required.'}, status=400)

        # Tier comes from the user's subscription — never from client input.
        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription or not subscription.is_active():
            return Response(
                {'success': False, 'error': 'An active subscription is required to create API keys.'},
                status=403
            )
        tier = subscription.get_tier_from_plan()

        raw_key, key_hash, prefix = APIClient.generate_key()
        quota = APIClient.QUOTA_MAP.get(tier, 100)
        APIClient.objects.create(
            user=request.user,
            name=name,
            api_key_prefix=prefix,
            api_key_hash=key_hash,
            tier=tier,
            quota_requests_per_hour=quota,
        )
        return Response({'success': True, 'raw_key': raw_key}, status=201)


class APIKeyDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            key = APIClient.objects.get(pk=pk, user=request.user)
            key.is_active = False
            key.save(update_fields=['is_active'])
            return Response({'success': True, 'message': 'Key revoked.'})
        except APIClient.DoesNotExist:
            return Response({'success': False, 'error': 'API key not found.'}, status=404)


# Vues pour l'interface utilisateur
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if password != password_confirm:
            return render(request, 'register.html', {'error': 'Les mots de passe ne correspondent pas.'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Ce nom d\'utilisateur existe déjà.'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Cet email est déjà utilisé.'})
        
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Créer un abonnement en attente de paiement
        subscription = Subscription.objects.create(user=user, plan='free', status='pending')
        
        login(request, user)
        return redirect('/payment/')
    
    return render(request, 'register.html')


def subscription_view(request):
    if not request.user.is_authenticated:
        return redirect('/register/')
    
    try:
        subscription = Subscription.objects.get(user=request.user)
        current_plan = subscription.plan
    except Subscription.DoesNotExist:
        subscription = Subscription.objects.create(user=request.user, plan='free', status='pending')
        current_plan = 'free'
    
    # Récupérer la clé API active
    api_client = APIClient.objects.filter(user=request.user, is_active=True).first()
    api_key = None
    if api_client:
        # Pour des raisons de sécurité, on ne montre que le préfixe
        api_key = f"{api_client.api_key_prefix}... (utilisez votre clé complète)"
    
    return render(request, 'subscription.html', {
        'current_plan': current_plan,
        'api_key': api_key,
        'subscription': subscription,
    })


def payment_view(request):
    if not request.user.is_authenticated:
        return redirect('/register/')
    
    try:
        subscription = Subscription.objects.get(user=request.user)
    except Subscription.DoesNotExist:
        subscription = Subscription.objects.create(user=request.user, plan='free', status='pending')
    
    # Note: active subscribers CAN reach this page — it doubles as the
    # upgrade/downgrade flow (a new pending payment switches the plan
    # once approved by an admin).
    if request.method == 'POST':
        plan_prices = {
            'free': 0,
            'standard': 9.99,
            'premium': 29.99,
            'partner': 99.99,
        }
        plan = request.POST.get('plan', 'free')
        payment_method = request.POST.get('payment_method', 'stripe')

        # Validate — never trust POST data for plan or method
        if plan not in plan_prices:
            plan = 'free'
        if payment_method not in ('stripe', 'paypal', 'manual'):
            payment_method = 'manual'

        # Mettre à jour le plan de l'abonnement
        subscription.plan = plan
        subscription.save()

        # Free plan: activate immediately — no payment needed
        if plan == 'free':
            from django.utils.timezone import now as tz_now
            from datetime import timedelta
            subscription.status = 'active'
            subscription.start_date = tz_now()
            subscription.end_date = tz_now() + timedelta(days=30)
            subscription.save()
            # Generate API key if none exists
            if not APIClient.objects.filter(user=request.user, is_active=True).exists():
                raw_key, key_hash, prefix = APIClient.generate_key()
                APIClient.objects.create(
                    user=request.user,
                    name='Default API Key',
                    api_key_prefix=prefix,
                    api_key_hash=key_hash,
                    tier='free',
                    quota_requests_per_hour=APIClient.QUOTA_MAP.get('free', 100),
                )
                request.session['new_api_key'] = raw_key
            return redirect('/dashboard/')

        # Créer un paiement en attente
        payment = Payment.objects.create(
            user=request.user,
            subscription=subscription,
            amount=plan_prices.get(plan, 0),
            currency='EUR',
            payment_method=payment_method,
            status='pending'
        )
        
        if payment_method == 'manual':
            # Pour paiement manuel, informer l'utilisateur
            return render(request, 'payment.html', {
                'subscription': subscription,
                'plan_prices': plan_prices,
                'success': f'Demande de paiement manuel envoyée. Contactez le support pour finaliser le paiement de {plan_prices.get(plan, 0)}€. Votre référence : {payment.id}'
            })
        elif payment_method == 'stripe':
            # Rediriger vers Stripe (à implémenter avec Stripe SDK)
            return render(request, 'payment.html', {
                'subscription': subscription,
                'plan_prices': plan_prices,
                'error': 'Intégration Stripe à configurer. Utilisez le paiement manuel pour le moment.'
            })
        elif payment_method == 'paypal':
            # Rediriger vers PayPal (à implémenter avec PayPal SDK)
            return render(request, 'payment.html', {
                'subscription': subscription,
                'plan_prices': plan_prices,
                'error': 'Intégration PayPal à configurer. Utilisez le paiement manuel pour le moment.'
            })
    
    # Récupérer les prix des plans
    plan_prices = {
        'free': 0,
        'standard': 9.99,
        'premium': 29.99,
        'partner': 99.99,
    }
    
    return render(request, 'payment.html', {
        'subscription': subscription,
        'plan_prices': plan_prices,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is not None:
            login(request, user)
            return redirect('/dashboard/')
        return render(request, 'login.html', {'error': "Nom d'utilisateur ou mot de passe incorrect."})
    return render(request, 'login.html')


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/')


def home_view(request):
    lang = request.GET.get('lang', 'fr')
    return render(request, 'home_en.html' if lang == 'en' else 'home.html')


def docs_view(request):
    return render(request, 'docs.html')


def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    subscription, _ = Subscription.objects.get_or_create(
        user=request.user, defaults={'plan': 'free', 'status': 'pending'}
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'generate_key' and subscription.is_active():
            raw_key, key_hash, prefix = APIClient.generate_key()
            tier = subscription.get_tier_from_plan()
            APIClient.objects.create(
                user=request.user,
                name=request.POST.get('key_name', 'Default Key')[:100],
                api_key_prefix=prefix,
                api_key_hash=key_hash,
                tier=tier,
                quota_requests_per_hour=APIClient.QUOTA_MAP.get(tier, 100),
            )
            request.session['new_api_key'] = raw_key  # shown once, never again
        elif action == 'revoke_key':
            APIClient.objects.filter(
                pk=request.POST.get('key_id'), user=request.user
            ).update(is_active=False)
        return redirect('/dashboard/')

    new_api_key = request.session.pop('new_api_key', None)
    api_keys = APIClient.objects.filter(user=request.user).order_by('-created_at')
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:10]
    rates = ExchangeRate.objects.select_related('from_currency', 'to_currency').order_by('-fetched_at')[:20]

    return render(request, 'dashboard.html', {
        'subscription': subscription,
        'api_keys': api_keys,
        'api_client': api_keys.filter(is_active=True).first(),
        'new_api_key': new_api_key,
        'payments': payments,
        'rates': rates,
    })
