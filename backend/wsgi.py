"""WSGI entrypoint for production servers (gunicorn).

Exposes a module-level ``app`` so gunicorn can be pointed at ``wsgi:app``.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
