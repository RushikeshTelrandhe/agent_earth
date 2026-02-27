"""
Agent Earth — Production WSGI Entrypoint
==========================================
Used by gunicorn in production (Railway / Render).
For local development, use: python main.py dashboard
"""

import os
from dashboard.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") != "production"
    print(f"\n  Agent Earth API on port {port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)
