import os
from flask import Flask
from config import config
from models import db

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    
    try:
        from flask_cors import CORS
        CORS(app, origins=app.config.get("CORS_ORIGINS", ["*"]))
    except ImportError:
        pass
    
    from routes import api
    app.register_blueprint(api)
    
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
