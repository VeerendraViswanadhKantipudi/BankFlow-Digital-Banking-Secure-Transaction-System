import os
from app import create_app
from app.extensions import db
from app.core.config import Config

app = create_app(Config)

with app.app_context():
    # Automatically create tables in PostgreSQL if they do not exist
    db.create_all()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
