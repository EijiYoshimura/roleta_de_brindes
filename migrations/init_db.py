"""
Script de inicialização e seed do banco de dados.
Pode ser rodado múltiplas vezes com segurança (idempotente).
"""
import os
import sys

# Garantir que o path raiz do projeto esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Prize, Setting


def init_db():
    app = create_app()
    with app.app_context():
        # Criar todas as tabelas (não apaga dados existentes)
        db.create_all()
        print("✓ Tabelas criadas/verificadas.")

        # Seed: itens especiais padrão
        if Prize.query.filter_by(item_type="retry").count() == 0:
            retry = Prize(
                name="Tente Novamente",
                item_type="retry",
                weight=0.15,
                color="#e74c3c",
                is_active=True,
                exhausted_behavior="hide_weight",
                quantity=0,
            )
            db.session.add(retry)
            print("✓ Item 'Tente Novamente' criado.")

        if Prize.query.filter_by(item_type="no_win").count() == 0:
            no_win = Prize(
                name="Não foi dessa vez",
                item_type="no_win",
                weight=0.10,
                color="#95a5a6",
                is_active=True,
                exhausted_behavior="hide_weight",
                quantity=0,
            )
            db.session.add(no_win)
            print("✓ Item 'Não foi dessa vez' criado.")

        # Seed: configurações padrão
        defaults = {
            "retry_weight": "0.15",
            "no_win_weight": "0.10",
            "spin_duration_ms": "5000",
            "event_name": "Roleta de Brindes",
        }
        for key, value in defaults.items():
            if not Setting.query.get(key):
                db.session.add(Setting(key=key, value=value))
                print(f"✓ Setting '{key}' = '{value}' criado.")

        db.session.commit()
        print("\n✓ Banco de dados inicializado com sucesso!")
        print(f"  Arquivo: {app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == "__main__":
    init_db()
