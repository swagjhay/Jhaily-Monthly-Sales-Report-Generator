import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from models import db, User

load_dotenv()

app = Flask(__name__)

# In production (Render), DATABASE_URL will be set to a real Postgres connection
# string (e.g. from Neon). Locally, with no DATABASE_URL set, this falls back to
# the same SQLite file you've been developing against all along -- no extra
# setup needed for day-to-day local coding.
database_url = os.environ.get("DATABASE_URL", "sqlite:///jhaily.db")
# Some providers (Neon included) hand out a "postgres://" URL, but SQLAlchemy
# 1.4+ requires "postgresql://" -- normalize it so either form works.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()
