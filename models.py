from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column # For SQLAlchemy 2.0 type hints

db = SQLAlchemy()

# User model for database
class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    # Flask-Login specific methods (UserMixin provides implementations, but you can override)
    def get_id(self):
        return str(self.id)