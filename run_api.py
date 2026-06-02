#!/usr/bin/env python3
"""
Usage:
    python run_api.py              # Production (Waitress, port 8000)
    python run_api.py --dev        # Développement (Flask reload, port 8000)
"""

import sys
from api.app import create_app

app = create_app()

if __name__ == "__main__":
    if "--dev" in sys.argv:
        app.run(host="0.0.0.0", port=8000, debug=True)
    else:
        from waitress import serve
        serve(app, host="0.0.0.0", port=8000)
