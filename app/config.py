import os
from datetime import timedelta


class Config:
    # Segurança
    SECRET_KEY = os.environ.get("SECRET_KEY", "roleta-local-secret-change-in-prod")

    # Banco de dados
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'roleta.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload de imagens
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
    IMAGE_MAX_SIZE = (400, 400)  # px

    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
