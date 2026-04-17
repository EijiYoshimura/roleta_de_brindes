import os
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app, jsonify,
)
from werkzeug.utils import secure_filename
from PIL import Image
from app import db
from app.models import Prize, Draw, Setting

admin_bp = Blueprint("admin", __name__)

# IDs dos itens especiais padrão que não podem ser excluídos
_PROTECTED_TYPES = {"retry", "no_win"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def _save_image(file):
    """Salva e redimensiona a imagem. Retorna o filename salvo."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    img = Image.open(file)
    img.thumbnail(current_app.config["IMAGE_MAX_SIZE"], Image.LANCZOS)
    # Converter para RGB se necessário (ex: PNG com transparência para JPEG)
    if ext in ("jpg", "jpeg") and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(filepath)
    return filename


def _delete_image(filename):
    """Remove o arquivo de imagem do disco se existir."""
    if filename:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(path):
            os.remove(path)


def _validate_prize_form(form, files, is_edit=False):
    """Valida os dados do formulário. Retorna (errors: list, data: dict)."""
    errors = []
    name = form.get("name", "").strip()
    item_type = form.get("item_type", "prize")
    color = form.get("color", "#3498db")
    quantity = form.get("quantity", "0")
    weight = form.get("weight", "0.15")
    exhausted_behavior = form.get("exhausted_behavior", "hide_weight")

    if not name:
        errors.append("O nome do brinde é obrigatório.")
    elif len(name) > 100:
        errors.append("O nome deve ter no máximo 100 caracteres.")

    if item_type not in ("prize", "retry", "no_win"):
        errors.append("Tipo inválido.")

    if item_type == "prize":
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError
        except ValueError:
            errors.append("A quantidade deve ser um número inteiro maior ou igual a zero.")
            quantity = 0

        if exhausted_behavior not in ("hide_weight", "act_as_retry"):
            exhausted_behavior = "hide_weight"
        weight = 0.0
    else:
        try:
            weight = float(weight)
            if not (0.0 < weight < 1.0):
                raise ValueError
        except ValueError:
            errors.append("O peso deve ser um valor entre 0.01 e 0.99.")
            weight = 0.15
        quantity = 0
        exhausted_behavior = "hide_weight"

    image_file = files.get("image")
    image_filename = None
    if image_file and image_file.filename:
        if not _allowed_file(image_file.filename):
            errors.append("Formato de imagem inválido. Use JPG, PNG, WebP ou GIF.")
        else:
            image_filename = image_file  # arquivo válido para processar

    data = {
        "name": name,
        "item_type": item_type,
        "color": color,
        "quantity": quantity,
        "weight": weight,
        "exhausted_behavior": exhausted_behavior,
        "image_file": image_filename,
    }
    return errors, data


# ── Rotas ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/")
def index():
    tipo = request.args.get("tipo")
    ativo = request.args.get("ativo")

    query = Prize.query
    if tipo in ("prize", "retry", "no_win"):
        query = query.filter_by(item_type=tipo)
    if ativo == "1":
        query = query.filter_by(is_active=True)
    elif ativo == "0":
        query = query.filter_by(is_active=False)

    prizes = query.order_by(
        db.case({"prize": 0, "retry": 1, "no_win": 2}, value=Prize.item_type),
        Prize.name,
    ).all()

    total_prizes = sum(p.quantity for p in prizes if p.item_type == "prize")
    active_prizes = sum(1 for p in prizes if p.item_type == "prize" and p.is_active)

    return render_template(
        "admin/index.html",
        prizes=prizes,
        total_prizes=total_prizes,
        active_prizes=active_prizes,
    )


@admin_bp.route("/prizes/new", methods=["GET", "POST"])
def prize_new():
    if request.method == "POST":
        errors, data = _validate_prize_form(request.form, request.files)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/form.html", prize=None, form_data=request.form)

        saved_filename = None
        if data["image_file"]:
            try:
                saved_filename = _save_image(data["image_file"])
            except Exception:
                flash("Erro ao processar a imagem. Verifique o arquivo.", "error")
                return render_template("admin/form.html", prize=None, form_data=request.form)

        prize = Prize(
            name=data["name"],
            item_type=data["item_type"],
            color=data["color"],
            quantity=data["quantity"],
            weight=data["weight"],
            exhausted_behavior=data["exhausted_behavior"],
            image_filename=saved_filename,
            is_active=True,
        )
        db.session.add(prize)
        db.session.commit()
        flash(f"Brinde '{prize.name}' cadastrado com sucesso!", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/form.html", prize=None, form_data={})


@admin_bp.route("/prizes/<int:prize_id>/edit", methods=["GET", "POST"])
def prize_edit(prize_id):
    prize = Prize.query.get_or_404(prize_id)

    if request.method == "POST":
        errors, data = _validate_prize_form(request.form, request.files, is_edit=True)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/form.html", prize=prize, form_data=request.form)

        # Se enviou nova imagem, deletar a anterior
        if data["image_file"]:
            try:
                new_filename = _save_image(data["image_file"])
                _delete_image(prize.image_filename)
                prize.image_filename = new_filename
            except Exception:
                flash("Erro ao processar a imagem.", "error")
                return render_template("admin/form.html", prize=prize, form_data=request.form)

        prize.name = data["name"]
        prize.item_type = data["item_type"]
        prize.color = data["color"]
        prize.quantity = data["quantity"]
        prize.weight = data["weight"]
        prize.exhausted_behavior = data["exhausted_behavior"]

        db.session.commit()
        flash(f"Brinde '{prize.name}' atualizado com sucesso!", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/form.html", prize=prize, form_data={})


@admin_bp.route("/prizes/<int:prize_id>/delete", methods=["POST"])
def prize_delete(prize_id):
    prize = Prize.query.get_or_404(prize_id)

    if prize.item_type in _PROTECTED_TYPES:
        flash("Itens especiais padrão não podem ser excluídos. Você pode editá-los.", "error")
        return redirect(url_for("admin.index"))

    _delete_image(prize.image_filename)
    db.session.delete(prize)
    db.session.commit()
    flash(f"Brinde '{prize.name}' excluído.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/prizes/<int:prize_id>/toggle", methods=["POST"])
def prize_toggle(prize_id):
    prize = Prize.query.get_or_404(prize_id)
    prize.is_active = not prize.is_active
    db.session.commit()
    return jsonify({"is_active": prize.is_active, "name": prize.name})


@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        retry_weight = request.form.get("retry_weight", "0.15")
        no_win_weight = request.form.get("no_win_weight", "0.10")
        spin_duration = request.form.get("spin_duration_ms", "5000")
        event_name = request.form.get("event_name", "Roleta de Brindes").strip()

        errors = []
        try:
            rw = float(retry_weight)
            nw = float(no_win_weight)
            if not (0.0 <= rw < 1.0):
                raise ValueError
            if not (0.0 <= nw < 1.0):
                raise ValueError
            if rw + nw >= 1.0:
                errors.append(
                    "A soma dos pesos especiais não pode atingir 100% — "
                    "não restariam brindes reais para sortear."
                )
        except ValueError:
            errors.append("Pesos devem ser valores entre 0 e 0.99.")

        try:
            sd = int(spin_duration)
            if not (2000 <= sd <= 10000):
                raise ValueError
        except ValueError:
            errors.append("Duração do giro deve ser entre 2000ms e 10000ms.")

        if not event_name or len(event_name) > 100:
            errors.append("Nome do evento é obrigatório (máx 100 caracteres).")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/settings.html", settings=_get_settings())

        Setting.set("retry_weight", retry_weight)
        Setting.set("no_win_weight", no_win_weight)
        Setting.set("spin_duration_ms", spin_duration)
        Setting.set("event_name", event_name)

        # Atualizar pesos nos itens especiais
        retry_item = Prize.query.filter_by(item_type="retry").first()
        if retry_item:
            retry_item.weight = float(retry_weight)

        no_win_item = Prize.query.filter_by(item_type="no_win").first()
        if no_win_item:
            no_win_item.weight = float(no_win_weight)

        db.session.commit()
        flash("Configurações salvas com sucesso!", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", settings=_get_settings())


def _get_settings():
    return {
        "retry_weight": float(Setting.get("retry_weight", "0.15")),
        "no_win_weight": float(Setting.get("no_win_weight", "0.10")),
        "spin_duration_ms": int(Setting.get("spin_duration_ms", "5000")),
        "event_name": Setting.get("event_name", "Roleta de Brindes"),
    }


@admin_bp.route("/history")
def history():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)

    pagination = Draw.query.order_by(Draw.drawn_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    total = Draw.query.count()
    total_prizes = Draw.query.filter_by(prize_type="prize").count()
    total_special = total - total_prizes

    return render_template(
        "admin/history.html",
        pagination=pagination,
        draws=pagination.items,
        total=total,
        total_prizes=total_prizes,
        total_special=total_special,
    )
