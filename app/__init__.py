import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Carregar configuração
    app.config.from_object("app.config.Config")

    # Garantir que as pastas necessárias existam
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Inicializar extensões
    db.init_app(app)

    # Registrar blueprints
    from app.routes.roulette import roulette_bp
    from app.routes.admin import admin_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(roulette_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(reports_bp, url_prefix="/admin/reports")

    # Criar tabelas e seed inicial
    with app.app_context():
        db.create_all()
        _seed_defaults()

    # Handlers de erro
    from app.routes.roulette import handle_404, handle_500
    app.register_error_handler(404, handle_404)
    app.register_error_handler(500, handle_500)

    return app


def _seed_defaults():
    """Insere dados iniciais apenas se as tabelas estiverem vazias."""
    from app.models import Prize, Setting

    if Prize.query.count() == 0:
        defaults = [
            Prize(
                name="Tente Novamente",
                item_type="retry",
                weight=0.15,
                color="#e74c3c",
                is_active=True,
                exhausted_behavior="hide_weight",
                quantity=0,
            ),
            Prize(
                name="Não foi dessa vez",
                item_type="no_win",
                weight=0.10,
                color="#95a5a6",
                is_active=True,
                exhausted_behavior="hide_weight",
                quantity=0,
            ),
        ]
        db.session.add_all(defaults)

    if Setting.query.count() == 0:
        settings = [
            Setting(key="retry_weight", value="0.15"),
            Setting(key="no_win_weight", value="0.10"),
            Setting(key="spin_duration_ms", value="5000"),
            Setting(key="event_name", value="Roleta de Brindes"),
        ]
        db.session.add_all(settings)

    db.session.commit()
