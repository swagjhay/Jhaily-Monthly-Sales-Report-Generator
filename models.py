from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
  __tablename__ = 'users'
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(120), unique=True, nullable=False)
  password_hash = db.Column(db.String(255), nullable=False)
  businesses = db.relationship('Business', backref='owner', lazy=True)

  @property
  def password(self):
    raise AttributeError("Password is not a readable attribute.")

  @password.setter
  def password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)

  def __repr__(self):
    return f"<User {self.email}>"


class Business(db.Model):
  __tablename__ = 'businesses'
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
  name = db.Column(db.String(120), nullable=False)
  recipient_email = db.Column(db.String(120), nullable=False)
  sales_file_path = db.Column(db.String(255), nullable=False)
  active = db.Column(db.Boolean, default=True, nullable=False)
  unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

  def __repr__(self):
    return f"<Business {self.name} ({'active' if self.active else 'inactive'})>"
