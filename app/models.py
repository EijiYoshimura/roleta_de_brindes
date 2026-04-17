from datetime import datetime
from app import db


class Prize(db.Model):
    __tablename__ = "prizes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    item_type = db.Column(db.String(10), nullable=False, default="prize")
    # item_type: 'prize' | 'retry' | 'no_win'
    weight = db.Column(db.Float, nullable=False, default=0.0)
    # weight: usado apenas por retry/no_win como percentual (0.0–1.0)
    color = db.Column(db.String(7), nullable=False, default="#3498db")
    exhausted_behavior = db.Column(db.String(15), nullable=False, default="hide_weight")
    # exhausted_behavior: 'hide_weight' | 'act_as_retry'
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    draws = db.relationship("Draw", backref="prize", lazy=True)

    @property
    def is_exhausted(self):
        """True se este brinde está com quantity=0 (apenas para type=prize)."""
        return self.item_type == "prize" and self.quantity == 0

    def to_dict(self):
        from flask import url_for
        image_url = None
        if self.image_filename:
            image_url = url_for("static", filename=f"uploads/{self.image_filename}")
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "image_url": image_url,
            "item_type": self.item_type,
            "quantity": self.quantity if self.item_type == "prize" else None,
            "is_exhausted": self.is_exhausted,
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<Prize {self.id}: {self.name} ({self.item_type})>"


class Draw(db.Model):
    __tablename__ = "draws"

    id = db.Column(db.Integer, primary_key=True)
    prize_id = db.Column(
        db.Integer, db.ForeignKey("prizes.id", ondelete="SET NULL"), nullable=True
    )
    prize_name = db.Column(db.String(100), nullable=False)
    prize_type = db.Column(db.String(10), nullable=False)
    # prize_type: snapshot do tipo no momento do sorteio
    drawn_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Draw {self.id}: {self.prize_name} @ {self.drawn_at}>"


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @staticmethod
    def get(key, default=None):
        """Retorna o valor de uma configuração ou o default se não existir."""
        setting = Setting.query.get(key)
        return setting.value if setting else default

    @staticmethod
    def set(key, value):
        """Cria ou atualiza uma configuração."""
        setting = Setting.query.get(key)
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(key=key, value=str(value))
            db.session.add(setting)

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"
