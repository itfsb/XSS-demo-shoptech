import hashlib
import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-insecure-key")

# VULN: cookies lisibles par JavaScript (désactivé pour la démo XSS cookie theft)
# DEFENSE: passer à True — Set-Cookie: HttpOnly
app.config["SESSION_COOKIE_HTTPONLY"] = False
app.config["SESSION_COOKIE_SAMESITE"] = None

DATABASE = "database.db"


# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email    TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT NOT NULL,
                price       REAL NOT NULL,
                category    TEXT NOT NULL,
                stock       INTEGER DEFAULT 10,
                image_url   TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                username   TEXT NOT NULL,
                content    TEXT NOT NULL,
                rating     INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )

        users = [
            ("alice", "alice@shoptech.com", hashlib.sha256(b"password").hexdigest()),
            ("bob", "bob@shoptech.com", hashlib.sha256(b"password").hexdigest()),
            ("admin", "admin@shoptech.com", hashlib.sha256(b"admin123").hexdigest()),
        ]
        for u in users:
            conn.execute(
                "INSERT OR IGNORE INTO users (username, email, password) VALUES (?, ?, ?)", u
            )

        products = [
            (
                'MacBook Pro 14"',
                "Processeur M3 Pro, 18 Go RAM, 512 Go SSD. Performance exceptionnelle pour les professionnels.",
                2499.99,
                "Laptops",
                "https://placehold.co/400x300/1a1a2e/ffffff?text=MacBook+Pro",
            ),
            (
                "iPhone 15 Pro",
                "Puce A17 Pro, caméra 48 MP, Dynamic Island. Le smartphone ultime d'Apple.",
                1199.99,
                "Smartphones",
                "https://placehold.co/400x300/16213e/ffffff?text=iPhone+15+Pro",
            ),
            (
                "AirPods Pro 2",
                "Réduction de bruit active, audio spatial, étui MagSafe. Son immersif.",
                279.99,
                "Audio",
                "https://placehold.co/400x300/0f3460/ffffff?text=AirPods+Pro",
            ),
            (
                "iPad Air M2",
                "Écran Liquid Retina 11\", puce M2, compatible Apple Pencil Pro. Polyvalent.",
                699.99,
                "Tablettes",
                "https://placehold.co/400x300/533483/ffffff?text=iPad+Air",
            ),
            (
                "Apple Watch Series 9",
                "GPS + Cellular, double tap, capteur de température. La montre connectée de référence.",
                449.99,
                "Wearables",
                "https://placehold.co/400x300/2c003e/ffffff?text=Apple+Watch",
            ),
            (
                "Samsung Galaxy S24 Ultra",
                "Stylet intégré S Pen, zoom optique 10x, Galaxy AI. La référence Android.",
                1349.99,
                "Smartphones",
                "https://placehold.co/400x300/1b1b2f/ffffff?text=Galaxy+S24+Ultra",
            ),
        ]
        for p in products:
            conn.execute(
                "INSERT OR IGNORE INTO products (name, description, price, category, image_url) VALUES (?, ?, ?, ?, ?)",
                p,
            )

        conn.commit()


# ---------------------------------------------------------------------------
# Routes principales
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products LIMIT 6").fetchall()
    return render_template("index.html", products=products, user=session.get("username"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = hashlib.sha256(request.form.get("password", "").encode()).hexdigest()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        if user:
            session["username"] = user["username"]
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            return redirect(url_for("index"))
        error = "Identifiants incorrects."
    return render_template("login.html", error=error, user=session.get("username"))


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not username or not email or not password:
            error = "Tous les champs sont requis."
        else:
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                    (username, email, pw_hash),
                )
                db.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Nom d'utilisateur ou email déjà utilisé."
    return render_template("register.html", error=error, user=session.get("username"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Vulnérabilité 1 — Reflected XSS
# ---------------------------------------------------------------------------

@app.route("/search")
def search():
    q = request.args.get("q", "")
    db = get_db()
    products = db.execute(
        "SELECT * FROM products WHERE name LIKE ? OR description LIKE ?",
        (f"%{q}%", f"%{q}%"),
    ).fetchall()

    # VULN: q est passé brut au template — le filtre | safe désactive l'échappement
    # DEFENSE: html.escape(q) avant de passer au template
    return render_template(
        "search.html", query=q, products=products, user=session.get("username")
    )


# ---------------------------------------------------------------------------
# Vulnérabilités 2 + 4 — Stored XSS + CSRF
# ---------------------------------------------------------------------------

@app.route("/product/<int:product_id>", methods=["GET", "POST"])
def product(product_id):
    db = get_db()
    prod = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not prod:
        return "Produit introuvable", 404

    if request.method == "POST":
        if not session.get("username"):
            return redirect(url_for("login"))
        content = request.form.get("review", "")
        rating = request.form.get("rating", 5)

        # VULN: contenu stocké sans sanitisation (Stored XSS)
        # DEFENSE: import bleach; content = bleach.clean(content, tags=[], strip=True)
        db.execute(
            "INSERT INTO reviews (product_id, username, content, rating) VALUES (?, ?, ?, ?)",
            (product_id, session["username"], content, rating),
        )
        db.commit()
        return redirect(url_for("product", product_id=product_id))

    reviews = db.execute(
        "SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC",
        (product_id,),
    ).fetchall()
    return render_template(
        "product.html",
        product=prod,
        reviews=reviews,
        user=session.get("username"),
    )


# ---------------------------------------------------------------------------
# Vulnérabilité 3 — DOM-based XSS (rendu côté client)
# ---------------------------------------------------------------------------

@app.route("/profile")
def profile():
    if not session.get("username"):
        return redirect(url_for("login"))
    return render_template(
        "profile.html",
        user=session.get("username"),
        email=session.get("email"),
    )


# ---------------------------------------------------------------------------
# Endpoints CSRF (cibles de la chaîne XSS+CSRF)
# ---------------------------------------------------------------------------

@app.route("/account/change-email", methods=["POST"])
def change_email():
    if not session.get("username"):
        return jsonify({"error": "Non authentifié"}), 401

    # VULN: aucun token CSRF — n'importe quelle origine peut forger cette requête
    # DEFENSE: vérifier un token CSRF stocké en session
    data = request.get_json(silent=True) or request.form
    new_email = data.get("email", "").strip()

    db = get_db()
    db.execute(
        "UPDATE users SET email = ? WHERE username = ?",
        (new_email, session["username"]),
    )
    db.commit()
    session["email"] = new_email
    return jsonify({"success": True, "email": new_email})


@app.route("/account/change-password", methods=["POST"])
def change_password():
    if not session.get("username"):
        return jsonify({"error": "Non authentifié"}), 401

    # VULN: aucun token CSRF
    data = request.get_json(silent=True) or request.form
    new_pw = hashlib.sha256(data.get("password", "").encode()).hexdigest()

    db = get_db()
    db.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (new_pw, session["username"]),
    )
    db.commit()
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Checkout — cible du keylogger (Stored XSS niveau 3)
# ---------------------------------------------------------------------------

@app.route("/checkout")
def checkout():
    if not session.get("username"):
        return redirect(url_for("login"))
    return render_template("checkout.html", user=session.get("username"))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5000)
