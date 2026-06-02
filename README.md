# Gestion Matériel 

Flask ≥3.1 + Jinja2 + vanilla JS — gestion d'équipement militaire. Code (messages, BDD, templates) en **français**. Prod via Waitress ≥3.0.

Pas de tests, pas de linter, pas de formateur, pas de CI, pas de `.git`.

## Exécution

```bash
pip install -r requirements.txt
python run_api.py              # Production (Waitress, port 8000)
python run_api.py --dev        # Développement (Flask reload, port 8000)
```

Warning Werkzeug en `--dev` est normal.

## DB

- `database/equipment.db` — auto-créée au démarrage par `init_db()` + `seed_db()`, appelé dans `create_app()` (idempotent)
- Utilisateur seed : `admin@mil.fr` / `admin123` (Admin)
- Pas de `.gitignore` ni `.git` — `.db` versionné volontairement
- UNIQUE géré manuellement → 409 (pas de ON DELETE CASCADE)
- DELETE ignore les clés étrangères (SQLite, pas de `PRAGMA foreign_keys = ON`)
- `get_connection()` crée une nouvelle connexion SQLite à chaque appel (pas de pool)

## Architecture

| Fichier | Rôle |
|---|---|
| `run_api.py` | Point d'entrée unique |
| `api/app.py` | `create_app()` factory, 9 blueprints, `serve_page` (9 pages + `base.html` layout) |
| `api/routes.py` | `require_auth`, `json_body`, helpers DB, 8 blueprints métier |
| `api/auth.py` | Blueprint auth (connexion publique, inscription admin-only) |
| `database/db.py` | Connexion SQLite, schéma, seeds |
| `static/js/api.js` | Client `api.get/post/put/del` avec `Authorization: Bearer <token>` depuis `localStorage` |

## Décorateurs (ordre critique)

```python
@require_auth   # OUTER — fournit `user` en 1er arg positionnel
@json_body      # INNER — fournit `data` en 1er arg positionnel
def fn(data, user):  # data AVANT user
```

- `@require_auth` seul → `def fn(user)` (GET/DELETE)
- `@require_auth` + `@json_body` → `def fn(data, user)` (POST/PUT)
- `auth.py` a sa propre copie de `json_body` (pas de `@require_auth`)
- Inscription (`POST /api/auth/inscription`) nécessite `@require_auth` + rôle Admin

## API

| Méthodes | Ressource | Notes |
|---|---|---|
| GET `/api` | Liste tous les endpoints | |
| POST | `/api/auth/connexion` | Public (pas de `@require_auth`) |
| POST | `/api/auth/inscription` | Admin only |
| GET/PUT/DELETE | `/api/utilisateurs[/<id>]` | GET = liste ; PUT/DELETE par id |
| GET | `/api/dashboard/stats` | |
| GET/POST/PUT/DELETE | `/api/marques`, `/api/modeles`, `/api/magasins` | CRUD complet |
| GET (liste+detail)/POST/PUT/DELETE | `/api/equipements[/<id>]` | CRUD complet ; GET liste accepte `?statut=`, `?modele_id=`, `?q=` |
| GET (liste+detail)/POST/PUT/DELETE | `/api/missions[/<id>]` | CRUD complet |
| GET (liste)/POST/PUT/DELETE | `/api/reservations[/<id>]` | Pas de GET détail |

### Statuts métier & transitions

- **equipement** : `DISPONIBLE`, `EN USAGE`, `MAINTENANCE`, `RETIRE`, `PERDU`
- **reservation** : `RESERVEE`, `SORTIE`, `RETOURNEE`
- Création `SORTIE` ou PUT `SORTIE` → équipement → `EN USAGE`
- PUT `RETOURNEE` → équipement → `DISPONIBLE`
- DELETE réservation → équipement libéré si `SORTIE`/`RESERVEE`

## Frontend

- Pages : `GET /<page>` sert `templates/<page>.html` via `serve_page` (9 pages autorisées ; `base.html` = layout)
- Auth : token dans `localStorage` (`token`, `user`) ; redirection si absent
- JS : `api.js` gère les appels ; `app.js` est un placeholder vide
- Barre de recherche globale dans le sidebar (visible sauf dashboard, connexion, inscription) → navigate vers `/equipements?q=`
- La page équipements lit `?q=` de l'URL au chargement pour pré-remplir son filtre
