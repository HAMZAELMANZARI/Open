import sqlite3
import os
import secrets
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "equipment.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS marque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS modele (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            marque_id INTEGER NOT NULL REFERENCES marque(id)
        );

        CREATE TABLE IF NOT EXISTS magasin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            adresse TEXT
        );

        CREATE TABLE IF NOT EXISTS equipement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_serie TEXT UNIQUE,
            modele_id INTEGER NOT NULL REFERENCES modele(id),
            statut TEXT NOT NULL DEFAULT 'DISPONIBLE'
                CHECK(statut IN ('DISPONIBLE','EN USAGE','MAINTENANCE','RETIRE','PERDU')),
            magasin_id INTEGER REFERENCES magasin(id),
            date_acquisition TEXT,
            dernier_service TEXT
        );

        CREATE TABLE IF NOT EXISTS utilisateur (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            mot_de_passe TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Utilisateur',
            token TEXT
        );

        CREATE TABLE IF NOT EXISTS mission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            destination TEXT,
            date_debut TEXT,
            date_fin TEXT,
            statut TEXT DEFAULT 'PLANIFICATION'
        );

        CREATE TABLE IF NOT EXISTS reservation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipement_id INTEGER NOT NULL REFERENCES equipement(id),
            mission_id INTEGER NOT NULL REFERENCES mission(id),
            date_reservation TEXT,
            date_retour TEXT,
            statut TEXT DEFAULT 'RESERVEE'
                CHECK(statut IN ('RESERVEE','SORTIE','RETOURNEE'))
        );
    """)

    conn.commit()
    return conn


def seed_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM marque")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    cur.executemany("INSERT OR IGNORE INTO marque (nom) VALUES (?)",
                    [(m,) for m in ["HK", "Colt", "Nightforce", "Thales", "Safran"]])

    cur.executemany("INSERT OR IGNORE INTO modele (nom, marque_id) VALUES (?, ?)",
                    [("HK416", 1), ("G36", 1), ("M4A1", 2), ("ACOG 4x", 3),
                     ("PRC-148", 4), ("JIM LR", 5)])

    cur.executemany("INSERT OR IGNORE INTO magasin (nom, adresse) VALUES (?, ?)",
                    [("Magasin Central", "Quartier général, Zone A"),
                     ("Depot Sud", "Base opérationnelle Sud"),
                     ("Armurerie Nord", "Bâtiment 7, Secteur Nord")])

    cur.executemany("""
        INSERT INTO equipement (numero_serie, modele_id, statut, magasin_id, date_acquisition, dernier_service)
        VALUES (?,?,?,?,?,?)
    """, [
        ("SN-416-001", 1, "DISPONIBLE", 1, "2025-06-01", "2026-04-15"),
        ("SN-416-002", 1, "EN USAGE",   2, "2025-06-01", "2026-03-20"),
        ("SN-G36-001", 2, "MAINTENANCE", 3, "2025-08-15", "2026-05-01"),
        ("SN-M4-001",  3, "DISPONIBLE", 1, "2024-11-01", "2026-02-10"),
        ("SN-ACOG-01", 4, "DISPONIBLE", 1, "2025-09-01", None),
        ("SN-PRC-148", 5, "EN USAGE",   2, "2025-12-01", "2026-04-28"),
        ("SN-JIM-001", 6, "PERDU",      None, "2025-03-01", "2025-12-15"),
    ])

    cur.execute("""
        INSERT OR IGNORE INTO utilisateur (nom, email, mot_de_passe, role, token)
        VALUES (?, ?, ?, ?, ?)
    """, ("Alex Carter", "admin@mil.fr", generate_password_hash("admin123"), "Admin", secrets.token_hex(32)))

    cur.executemany("""
        INSERT INTO mission (nom, destination, date_debut, date_fin, statut)
        VALUES (?,?,?,?,?)
    """, [
        ("Opération Épervier", "Zone Est", "2026-05-10", "2026-06-20", "ACTIVE"),
        ("Mission Sentinel", "Base Avancée Delta", "2026-04-01", "2026-04-30", "TERMINEE"),
        ("Exercice Nord", "Secteur Arctique", "2026-07-01", None, "PLANIFICATION"),
    ])

    cur.executemany("""
        INSERT INTO reservation (equipement_id, mission_id, date_reservation, date_retour, statut)
        VALUES (?,?,?,?,?)
    """, [
        (2, 1, "2026-05-08", None, "SORTIE"),
        (6, 1, "2026-05-08", None, "SORTIE"),
        (1, 2, "2026-03-28", "2026-05-01", "RETOURNEE"),
    ])

    conn.commit()
    conn.close()
