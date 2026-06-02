from flask import Flask, jsonify, render_template, redirect, url_for
from database.db import init_db, seed_db
from .auth import auth_bp
from .routes import (
    dashboard_bp, marque_bp, modele_bp, magasin_bp,
    equipement_bp, mission_bp, reservation_bp, utilisateur_bp,
)


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    init_db()
    seed_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(marque_bp)
    app.register_blueprint(modele_bp)
    app.register_blueprint(magasin_bp)
    app.register_blueprint(equipement_bp)
    app.register_blueprint(mission_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(utilisateur_bp)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.route("/")
    def root():
        return redirect("/connexion")

    @app.route("/api")
    def api_root():
        return jsonify({
            "endpoints": {
                "auth": {
                    "inscription": "POST /api/auth/inscription",
                    "connexion": "POST /api/auth/connexion",
                },
                "dashboard": {"stats": "GET /api/dashboard/stats"},
                "marques": {"list": "GET /api/marques", "create": "POST /api/marques"},
                "modeles": {"list": "GET /api/modeles", "create": "POST /api/modeles"},
                "magasins": {"list": "GET /api/magasins", "create": "POST /api/magasins"},
                "equipements": {
                    "list": "GET /api/equipements",
                    "get": "GET /api/equipements/<id>",
                    "create": "POST /api/equipements",
                    "update": "PUT /api/equipements/<id>",
                    "delete": "DELETE /api/equipements/<id>",
                },
                "missions": {
                    "list": "GET /api/missions",
                    "get": "GET /api/missions/<id>",
                    "create": "POST /api/missions",
                    "update": "PUT /api/missions/<id>",
                },
                "reservations": {
                    "list": "GET /api/reservations",
                    "create": "POST /api/reservations",
                    "update": "PUT /api/reservations/<id>",
                    "delete": "DELETE /api/reservations/<id>",
                },
            }
        })

    @app.route("/<page>")
    def serve_page(page):
        allowed = ["connexion", "inscription", "dashboard", "equipements",
                    "marques", "modeles", "magasins", "missions", "reservations"]
        if page in allowed:
            return render_template(f"{page}.html")
        return redirect("/connexion")

    return app
