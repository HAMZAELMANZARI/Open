from functools import wraps
from flask import Blueprint, jsonify, request
from database.db import get_connection

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
        if not token:
            return jsonify({"error": "Token requis"}), 401
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nom, email, role FROM utilisateur WHERE token = ?", (token,))
        user = cur.fetchone()
        conn.close()
        if user is None:
            return jsonify({"error": "Token invalide"}), 401
        return fn(user, *args, **kwargs)
    return wrapper

def json_body(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Le corps de la requête doit être du JSON valide"}), 400
        return fn(data, *args, **kwargs)
    return wrapper

def row_to_dict(cursor, row):
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))

def _fetch_all(query, params=None):
    conn = get_connection()
    conn.row_factory = row_to_dict
    cur = conn.cursor()
    cur.execute(query, params or [])
    rows = cur.fetchall()
    conn.close()
    return rows

def _fetch_one(query, params=None):
    conn = get_connection()
    conn.row_factory = row_to_dict
    cur = conn.cursor()
    cur.execute(query, params or [])
    row = cur.fetchone()
    conn.close()
    return row

# ─── Utilisateur ──────────────────────────────────────────────────────

utilisateur_bp = Blueprint("utilisateur", __name__, url_prefix="/api/utilisateurs")

@utilisateur_bp.route("", methods=["GET"])
@require_auth
def list_utilisateurs(user):
    rows = _fetch_all("SELECT id, nom, email, role FROM utilisateur ORDER BY nom")
    return jsonify(rows)

@utilisateur_bp.route("/<int:user_id>", methods=["PUT"])
@require_auth
@json_body
def update_utilisateur(data, user, user_id):
    allowed = ["nom", "email", "role", "mot_de_passe"]
    sets, params = [], []
    for f in allowed:
        if f in data:
            if f == "mot_de_passe":
                from werkzeug.security import generate_password_hash
                sets.append("mot_de_passe = ?")
                params.append(generate_password_hash(data[f]))
            else:
                sets.append(f"{f} = ?")
                params.append(data[f])
    if not sets:
        return jsonify({"error": "Aucun champ à mettre à jour"}), 400
    if "role" in data and data["role"] not in ("Admin", "Utilisateur"):
        return jsonify({"error": "Le rôle doit être 'Admin' ou 'Utilisateur'"}), 400
    params.append(user_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE utilisateur SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated == 0:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({"message": "Utilisateur mis à jour"})

@utilisateur_bp.route("/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_utilisateur(user, user_id):
    if user["id"] == user_id:
        return jsonify({"error": "Impossible de supprimer votre propre compte"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM utilisateur WHERE id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({"message": "Utilisateur supprimé"})

# ─── Dashboard ──────────────────────────────────────────────────────

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

@dashboard_bp.route("/stats", methods=["GET"])
@require_auth
def stats(user):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM equipement")
    total = cur.fetchone()[0]
    counts = {}
    for s in ("DISPONIBLE", "EN USAGE", "MAINTENANCE", "PERDU"):
        cur.execute("SELECT COUNT(*) FROM equipement WHERE statut = ?", (s,))
        counts[s] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mission WHERE statut = 'ACTIVE'")
    missions_actives = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reservation WHERE statut = 'SORTIE'")
    equipements_sortis = cur.fetchone()[0]
    conn.close()
    return jsonify({
        "total_equipements": total,
        "disponible": counts["DISPONIBLE"],
        "en_usage": counts["EN USAGE"],
        "maintenance": counts["MAINTENANCE"],
        "perdu": counts["PERDU"],
        "missions_actives": missions_actives,
        "equipements_sortis": equipements_sortis,
    })

# ─── Marque ──────────────────────────────────────────────────────────

marque_bp = Blueprint("marque", __name__, url_prefix="/api/marques")

@marque_bp.route("", methods=["GET"])
@require_auth
def list_marques(user):
    return jsonify(_fetch_all("SELECT id, nom FROM marque ORDER BY nom"))

@marque_bp.route("", methods=["POST"])
@require_auth
@json_body
def create_marque(data, user):
    if "nom" not in data or not data["nom"].strip():
        return jsonify({"error": "Le nom est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO marque (nom) VALUES (?)", (data["nom"].strip(),))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({"id": new_id, "message": "Marque créée"}), 201
    except Exception:
        conn.close()
        return jsonify({"error": "Cette marque existe déjà"}), 409

@marque_bp.route("/<int:marque_id>", methods=["PUT"])
@require_auth
@json_body
def update_marque(data, user, marque_id):
    if "nom" not in data or not data["nom"].strip():
        return jsonify({"error": "Le nom est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE marque SET nom = ? WHERE id = ?", (data["nom"].strip(), marque_id))
        conn.commit()
        updated = cur.rowcount
        conn.close()
        if updated == 0:
            return jsonify({"error": "Marque introuvable"}), 404
        return jsonify({"message": "Marque mise à jour"})
    except Exception:
        conn.close()
        return jsonify({"error": "Cette marque existe déjà"}), 409

@marque_bp.route("/<int:marque_id>", methods=["DELETE"])
@require_auth
def delete_marque(user, marque_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM marque WHERE id = ?", (marque_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Marque introuvable"}), 404
    return jsonify({"message": "Marque supprimée"})

# ─── Modèle ──────────────────────────────────────────────────────────

modele_bp = Blueprint("modele", __name__, url_prefix="/api/modeles")

@modele_bp.route("", methods=["GET"])
@require_auth
def list_modeles(user):
    rows = _fetch_all("""
        SELECT m.id, m.nom, m.marque_id, ma.nom AS marque_nom
        FROM modele m JOIN marque ma ON ma.id = m.marque_id
        ORDER BY m.nom
    """)
    return jsonify(rows)

@modele_bp.route("", methods=["POST"])
@require_auth
@json_body
def create_modele(data, user):
    if "nom" not in data or "marque_id" not in data:
        return jsonify({"error": "nom et marque_id sont requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO modele (nom, marque_id) VALUES (?, ?)",
                (data["nom"].strip(), data["marque_id"]))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Modèle créé"}), 201

@modele_bp.route("/<int:modele_id>", methods=["PUT"])
@require_auth
@json_body
def update_modele(data, user, modele_id):
    if "nom" not in data or "marque_id" not in data:
        return jsonify({"error": "nom et marque_id sont requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE modele SET nom = ?, marque_id = ? WHERE id = ?",
                (data["nom"].strip(), data["marque_id"], modele_id))
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated == 0:
        return jsonify({"error": "Modèle introuvable"}), 404
    return jsonify({"message": "Modèle mis à jour"})

@modele_bp.route("/<int:modele_id>", methods=["DELETE"])
@require_auth
def delete_modele(user, modele_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM modele WHERE id = ?", (modele_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Modèle introuvable"}), 404
    return jsonify({"message": "Modèle supprimé"})

# ─── Magasin ─────────────────────────────────────────────────────────

magasin_bp = Blueprint("magasin", __name__, url_prefix="/api/magasins")

@magasin_bp.route("", methods=["GET"])
@require_auth
def list_magasins(user):
    return jsonify(_fetch_all("SELECT id, nom, adresse FROM magasin ORDER BY nom"))

@magasin_bp.route("", methods=["POST"])
@require_auth
@json_body
def create_magasin(data, user):
    if "nom" not in data or not data["nom"].strip():
        return jsonify({"error": "Le nom est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO magasin (nom, adresse) VALUES (?, ?)",
                    (data["nom"].strip(), data.get("adresse", "")))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({"id": new_id, "message": "Magasin créé"}), 201
    except Exception:
        conn.close()
        return jsonify({"error": "Ce magasin existe déjà"}), 409

@magasin_bp.route("/<int:magasin_id>", methods=["PUT"])
@require_auth
@json_body
def update_magasin(data, user, magasin_id):
    if "nom" not in data or not data["nom"].strip():
        return jsonify({"error": "Le nom est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE magasin SET nom = ?, adresse = ? WHERE id = ?",
                    (data["nom"].strip(), data.get("adresse", ""), magasin_id))
        conn.commit()
        updated = cur.rowcount
        conn.close()
        if updated == 0:
            return jsonify({"error": "Magasin introuvable"}), 404
        return jsonify({"message": "Magasin mis à jour"})
    except Exception:
        conn.close()
        return jsonify({"error": "Ce magasin existe déjà"}), 409

@magasin_bp.route("/<int:magasin_id>", methods=["DELETE"])
@require_auth
def delete_magasin(user, magasin_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM magasin WHERE id = ?", (magasin_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Magasin introuvable"}), 404
    return jsonify({"message": "Magasin supprimé"})

# ─── Équipement ──────────────────────────────────────────────────────

equipement_bp = Blueprint("equipement", __name__, url_prefix="/api/equipements")

@equipement_bp.route("", methods=["GET"])
@require_auth
def list_equipements(user):
    query = """
        SELECT e.id, e.numero_serie, e.modele_id, mo.nom AS modele_nom,
               ma.nom AS marque_nom, e.statut, e.magasin_id, mg.nom AS magasin_nom,
               e.date_acquisition, e.dernier_service
        FROM equipement e
        JOIN modele mo ON mo.id = e.modele_id
        JOIN marque ma ON ma.id = mo.marque_id
        LEFT JOIN magasin mg ON mg.id = e.magasin_id
    """
    conditions = []
    params = []

    statut = request.args.get("statut")
    if statut:
        conditions.append("e.statut = ?")
        params.append(statut)

    modele_id = request.args.get("modele_id")
    if modele_id:
        conditions.append("e.modele_id = ?")
        params.append(modele_id)

    q = request.args.get("q")
    if q:
        conditions.append("(e.numero_serie LIKE ? OR mo.nom LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY e.id"

    return jsonify(_fetch_all(query, params))

@equipement_bp.route("/<int:equip_id>", methods=["GET"])
@require_auth
def get_equipement(user, equip_id):
    row = _fetch_one("""
        SELECT e.*, mo.nom AS modele_nom, ma.nom AS marque_nom, mg.nom AS magasin_nom
        FROM equipement e
        JOIN modele mo ON mo.id = e.modele_id
        JOIN marque ma ON ma.id = mo.marque_id
        LEFT JOIN magasin mg ON mg.id = e.magasin_id
        WHERE e.id = ?
    """, (equip_id,))
    if row is None:
        return jsonify({"error": "Équipement introuvable"}), 404
    return jsonify(row)

@equipement_bp.route("", methods=["POST"])
@require_auth
@json_body
def create_equipement(data, user):
    required = ["numero_serie", "modele_id"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"'{f}' est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO equipement (numero_serie, modele_id, statut, magasin_id, date_acquisition, dernier_service)
            VALUES (?,?,?,?,?,?)
        """, (
            data["numero_serie"], data["modele_id"],
            data.get("statut", "DISPONIBLE"),
            data.get("magasin_id"), data.get("date_acquisition"),
            data.get("dernier_service"),
        ))
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({"id": new_id, "message": "Équipement créé"}), 201
    except Exception as e:
        conn.close()
        if "UNIQUE" in str(e):
            return jsonify({"error": "Ce numéro de série existe déjà"}), 409
        return jsonify({"error": "Erreur lors de la création"}), 500

@equipement_bp.route("/<int:equip_id>", methods=["PUT"])
@require_auth
@json_body
def update_equipement(data, user, equip_id):
    allowed = ["numero_serie", "modele_id", "statut", "magasin_id", "date_acquisition", "dernier_service"]
    sets, params = [], []
    for f in allowed:
        if f in data:
            sets.append(f"{f} = ?")
            params.append(data[f])
    if not sets:
        return jsonify({"error": "Aucun champ à mettre à jour"}), 400
    params.append(equip_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE equipement SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated == 0:
        return jsonify({"error": "Équipement introuvable"}), 404
    return jsonify({"message": "Équipement mis à jour"})

@equipement_bp.route("/<int:equip_id>", methods=["DELETE"])
@require_auth
def delete_equipement(user, equip_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM equipement WHERE id = ?", (equip_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Équipement introuvable"}), 404
    return jsonify({"message": "Équipement supprimé"})

# ─── Mission ─────────────────────────────────────────────────────────

mission_bp = Blueprint("mission", __name__, url_prefix="/api/missions")

@mission_bp.route("", methods=["GET"])
@require_auth
def list_missions(user):
    return jsonify(_fetch_all("SELECT * FROM mission ORDER BY id"))

@mission_bp.route("/<int:mission_id>", methods=["GET"])
@require_auth
def get_mission(user, mission_id):
    row = _fetch_one("SELECT * FROM mission WHERE id = ?", (mission_id,))
    if row is None:
        return jsonify({"error": "Mission introuvable"}), 404
    return jsonify(row)

@mission_bp.route("", methods=["POST"])
@require_auth
@json_body
def create_mission(data, user):
    if "nom" not in data or not data["nom"].strip():
        return jsonify({"error": "Le nom est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO mission (nom, destination, date_debut, date_fin, statut)
        VALUES (?,?,?,?,?)
    """, (data["nom"].strip(), data.get("destination"), data.get("date_debut"),
          data.get("date_fin"), data.get("statut", "PLANIFICATION")))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Mission créée"}), 201

@mission_bp.route("/<int:mission_id>", methods=["DELETE"])
@require_auth
def delete_mission(user, mission_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM mission WHERE id = ?", (mission_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Mission introuvable"}), 404
    return jsonify({"message": "Mission supprimée"})

@mission_bp.route("/<int:mission_id>", methods=["PUT"])
@require_auth
@json_body
def update_mission(data, user, mission_id):
    allowed = ["nom", "destination", "date_debut", "date_fin", "statut"]
    sets, params = [], []
    for f in allowed:
        if f in data:
            sets.append(f"{f} = ?")
            params.append(data[f])
    if not sets:
        return jsonify({"error": "Aucun champ à mettre à jour"}), 400
    params.append(mission_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE mission SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated == 0:
        return jsonify({"error": "Mission introuvable"}), 404
    return jsonify({"message": "Mission mise à jour"})

# ─── Réservation ─────────────────────────────────────────────────────

reservation_bp = Blueprint("reservation", __name__, url_prefix="/api/reservations")

@reservation_bp.route("", methods=["GET"])
@require_auth
def list_reservations(user):
    rows = _fetch_all("""
        SELECT r.id, r.equipement_id, e.numero_serie, mo.nom AS modele_nom,
               r.mission_id, mi.nom AS mission_nom,
               r.date_reservation, r.date_retour, r.statut
        FROM reservation r
        JOIN equipement e ON e.id = r.equipement_id
        JOIN modele mo ON mo.id = e.modele_id
        JOIN mission mi ON mi.id = r.mission_id
        ORDER BY r.id
    """)
    return jsonify(rows)

@reservation_bp.route("", methods=["POST"])
@require_auth
@json_body
def create_reservation(data, user):
    required = ["equipement_id", "mission_id", "date_reservation"]
    for f in required:
        if f not in data:
            return jsonify({"error": f"'{f}' est requis"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reservation (equipement_id, mission_id, date_reservation, date_retour, statut)
        VALUES (?,?,?,?,?)
    """, (data["equipement_id"], data["mission_id"], data["date_reservation"],
          data.get("date_retour"), data.get("statut", "RESERVEE")))
    conn.commit()
    new_id = cur.lastrowid
    if data.get("statut") == "SORTIE":
        cur.execute("UPDATE equipement SET statut = 'EN USAGE' WHERE id = ?", (data["equipement_id"],))
        conn.commit()
    conn.close()
    return jsonify({"id": new_id, "message": "Réservation créée"}), 201

@reservation_bp.route("/<int:res_id>", methods=["PUT"])
@require_auth
@json_body
def update_reservation(data, user, res_id):
    allowed = ["date_reservation", "date_retour", "statut"]
    sets, params = [], []
    for f in allowed:
        if f in data:
            sets.append(f"{f} = ?")
            params.append(data[f])
    if not sets:
        return jsonify({"error": "Aucun champ à mettre à jour"}), 400

    conn = get_connection()
    cur = conn.cursor()
    params.append(res_id)
    cur.execute(f"UPDATE reservation SET {', '.join(sets)} WHERE id = ?", params)

    if data.get("statut") == "RETOURNEE":
        cur.execute("SELECT equipement_id FROM reservation WHERE id = ?", (res_id,))
        equip_id = cur.fetchone()
        if equip_id:
            cur.execute("UPDATE equipement SET statut = 'DISPONIBLE' WHERE id = ?", (equip_id[0],))
    elif data.get("statut") == "SORTIE":
        cur.execute("SELECT equipement_id FROM reservation WHERE id = ?", (res_id,))
        equip_id = cur.fetchone()
        if equip_id:
            cur.execute("UPDATE equipement SET statut = 'EN USAGE' WHERE id = ?", (equip_id[0],))

    conn.commit()
    updated = cur.rowcount
    conn.close()
    if updated == 0:
        return jsonify({"error": "Réservation introuvable"}), 404
    return jsonify({"message": "Réservation mise à jour"})

@reservation_bp.route("/<int:res_id>", methods=["DELETE"])
@require_auth
def delete_reservation(user, res_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT equipement_id, statut FROM reservation WHERE id = ?", (res_id,))
    res = cur.fetchone()
    if res and res[1] in ("SORTIE", "RESERVEE"):
        cur.execute("UPDATE equipement SET statut = 'DISPONIBLE' WHERE id = ?", (res[0],))
    cur.execute("DELETE FROM reservation WHERE id = ?", (res_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Réservation introuvable"}), 404
    return jsonify({"message": "Réservation supprimée"})
