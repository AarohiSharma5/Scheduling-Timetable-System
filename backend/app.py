import os
from flask import Flask, send_from_directory
from config import config
from models import db

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    # Serve React frontend from build folder - use proper static file serving
    react_build_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
    app = Flask(__name__, static_folder=os.path.join(react_build_path, 'static'), static_url_path='/static')
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
    
    # Serve React index.html for all non-API/non-static routes (for React Router)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>', methods=['GET'])
    def serve_react(path):
        # Don't catch static files or API requests
        if path.startswith('api/') or path.startswith('static/'):
            return {'error': 'Not found'}, 404
        # Serve index.html for all React routes
        index_path = os.path.join(react_build_path, 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
        return {'error': 'index.html not found'}, 500
    
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
