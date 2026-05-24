import os
from flask import Flask, send_from_directory
from config import config
from models import db

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    # Serve React frontend from build folder
    react_build_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
    app = Flask(__name__, static_folder=react_build_path, static_url_path='')
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    
    try:
        from flask_cors import CORS
        CORS(app, origins=app.config.get("CORS_ORIGINS", ["localhost:8000", "http://localhost:8000"]))
    except ImportError:
        pass
    
    from routes import api
    from timetable_routes import timetable_bp
    app.register_blueprint(api)
    app.register_blueprint(timetable_bp)
    
    # Serve React index.html for all non-API routes (for React Router)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react(path):
        if path and (path.startswith('api/') or path.endswith(('.js', '.css', '.png', '.jpg', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot'))):
            if os.path.exists(os.path.join(react_build_path, path)):
                return send_from_directory(react_build_path, path)
            return {'error': 'Not found'}, 404
        return send_from_directory(react_build_path, 'index.html')
    
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
