import secrets
from functools import wraps
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_connection
from .routes import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def json_body(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Le corps de la requête doit être du JSON valide"}), 400
        return fn(data, *args, **kwargs)
    return wrapper


@auth_bp.route("/inscription", methods=["POST"])
@require_auth
@json_body
def inscription(data, user):
    if user["role"] != "Admin":
        return jsonify({"error": "Accès réservé aux administrateurs"}), 403
    required = ["nom", "email", "mot_de_passe"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"'{field}' est requis"}), 400
        if not data[field].strip():
            return jsonify({"error": f"'{field}' ne peut pas être vide"}), 400

    nom = data["nom"].strip()
    email = data["email"].strip().lower()
    mot_de_passe = data["mot_de_passe"]
    role = data.get("role", "Utilisateur")

    if role not in ("Admin", "Utilisateur"):
        return jsonify({"error": "Le rôle doit être 'Admin' ou 'Utilisateur'"}), 400

    if len(mot_de_passe) < 6:
        return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        hash_pw = generate_password_hash(mot_de_passe)
        token = secrets.token_hex(32)
        cur.execute("""
            INSERT INTO utilisateur (nom, email, mot_de_passe, role, token)
            VALUES (?, ?, ?, ?, ?)
        """, (nom, email, hash_pw, role, token))
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return jsonify({
            "message": "Utilisateur créé avec succès",
            "utilisateur": {"id": user_id, "nom": nom, "email": email, "role": role}
        }), 201
    except Exception as e:
        conn.close()
        if "UNIQUE" in str(e):
            return jsonify({"error": "Cet email est déjà utilisé"}), 409
        return jsonify({"error": "Erreur lors de l'inscription"}), 500


@auth_bp.route("/connexion", methods=["POST"])
@json_body
def connexion(data):
    if "email" not in data or "mot_de_passe" not in data:
        return jsonify({"error": "'email' et 'mot_de_passe' sont requis"}), 400

    email = data["email"].strip().lower()
    mot_de_passe = data["mot_de_passe"]

    conn = get_connection()
    conn.row_factory = lambda c, r: {d[0]: r[i] for i, d in enumerate(c.description)}
    cur = conn.cursor()
    cur.execute("SELECT id, nom, email, role, mot_de_passe, token FROM utilisateur WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    if user is None or not check_password_hash(user["mot_de_passe"], mot_de_passe):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    return jsonify({
        "message": "Connexion réussie",
        "token": user["token"],
        "utilisateur": {"id": user["id"], "nom": user["nom"], "email": user["email"], "role": user["role"]}
    })
