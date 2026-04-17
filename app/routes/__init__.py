from flask import Blueprint

# Importar blueprints para facilitar imports externos
from app.routes.roulette import roulette_bp
from app.routes.admin import admin_bp
from app.routes.reports import reports_bp

__all__ = ["roulette_bp", "admin_bp", "reports_bp"]
