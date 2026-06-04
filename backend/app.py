import os
from flask import Flask, send_from_directory
from config import config
from models import db

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    # In production, serve React frontend from build folder
    react_build_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
    is_production = config_name == "production" or os.path.exists(react_build_path)
    
    if is_production:
        # Serve React with static files
        app = Flask(__name__, 
                   static_folder=os.path.join(react_build_path, 'static'),
                   static_url_path='/static')
    else:
        # Development: API only
        app = Flask(__name__)
    
    app.config.from_object(config.get(config_name, config["default"]))
    
    db.init_app(app)

    from extensions import limiter, migrate
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    try:
        from flask_cors import CORS
        # supports_credentials lets the browser send/receive the httpOnly auth
        # cookies. Harmless for the same-origin Docker deployment; required if
        # the SPA is ever served from a different origin in dev.
        CORS(
            app,
            origins=app.config.get("CORS_ORIGINS", ["http://localhost:3000", "localhost:3000"]),
            supports_credentials=True,
        )
    except ImportError:
        pass
    
    from routes import api
    from timetable_routes import timetable_bp
    from attendance_routes import attendance_bp
    from exam_routes import exam_bp
    app.register_blueprint(api)
    app.register_blueprint(timetable_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(exam_bp)
    
    # Serve React index.html for all non-API routes (for React Router)
    if is_production:
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>', methods=['GET'])
        def serve_react(path):
            # Don't catch API requests (hashed assets under /static are handled
            # by Flask's static handler already).
            if path.startswith('api/'):
                return {'error': 'Not found'}, 404
            # Serve real files copied from public/ to the build root
            # (scheduler-logo.png, favicon.ico, manifest.json, ...). Without
            # this, these requests fall through to index.html and the browser
            # gets HTML where it expected an image/asset.
            if path:
                asset_path = os.path.join(react_build_path, path)
                if os.path.isfile(asset_path):
                    return send_from_directory(react_build_path, path)
            # Otherwise serve index.html so React Router can handle the route.
            # index.html references hashed JS/CSS bundles, so it must never be
            # cached by the browser — otherwise users keep loading stale assets
            # after a rebuild. The hashed bundles themselves can be cached freely.
            index_path = os.path.join(react_build_path, 'index.html')
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    return f.read(), 200, {
                        'Content-Type': 'text/html; charset=utf-8',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                    }
            return {'error': 'index.html not found'}, 500
    
    # Schema is managed by Flask-Migrate (Alembic). Run `flask db upgrade` to
    # build/upgrade the database. (Seed scripts still call db.create_all()
    # themselves for convenience when bootstrapping a throwaway dev DB.)

    @app.after_request
    def set_security_headers(response):
        # Defense-in-depth hardening. These are deliberately conservative so
        # they don't break the bundled React app (no restrictive script-src,
        # which would block CRA's inline runtime). Auth tokens themselves live
        # in httpOnly cookies, so they're already out of JavaScript's reach.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
