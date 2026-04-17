import random
from flask import Blueprint, render_template, jsonify, request, url_for, current_app
from app import db
from app.models import Prize, Draw, Setting

roulette_bp = Blueprint("roulette", __name__)


@roulette_bp.route("/")
def index():
    """Tela principal da roleta."""
    spin_duration = int(Setting.get("spin_duration_ms", 5000))
    event_name = Setting.get("event_name", "Roleta de Brindes")
    return render_template(
        "roulette/index.html",
        spin_duration=spin_duration,
        event_name=event_name,
    )


@roulette_bp.route("/api/wheel")
def api_wheel():
    """Retorna os segmentos ativos da roda para o frontend.
    Não expõe pesos — o algoritmo fica exclusivamente no backend.
    """
    prizes = Prize.query.filter_by(is_active=True).order_by(Prize.id).all()
    return jsonify({"segments": [p.to_dict() for p in prizes]})


@roulette_bp.route("/api/spin", methods=["POST"])
def api_spin():
    """Executa o sorteio com peso, decrementa estoque e retorna o vencedor."""
    prizes = Prize.query.filter_by(is_active=True).all()

    if not prizes:
        return jsonify({"error": "no_active_prizes", "message": "Nenhum item ativo na roda."}), 409

    # ── Cálculo de pesos ────────────────────────────────────────────────────
    total_prize_qty = sum(
        p.quantity for p in prizes if p.item_type == "prize" and p.quantity > 0
    )

    weighted_items = []
    for prize in prizes:
        if prize.item_type == "prize":
            if prize.quantity > 0:
                weight = float(prize.quantity)
            elif prize.exhausted_behavior == "act_as_retry":
                weight = 1.0  # peso simbólico mínimo
            else:
                weight = 0.0  # hide_weight — nunca sorteado
        else:
            # retry / no_win: peso relativo ao total de brindes
            weight = prize.weight * max(total_prize_qty, 1)

        if weight > 0:
            weighted_items.append((prize, weight))

    if not weighted_items:
        return jsonify({
            "error": "no_active_prizes",
            "message": "Todos os brindes foram entregues!"
        }), 409

    # ── Sorteio ─────────────────────────────────────────────────────────────
    total_weight = sum(w for _, w in weighted_items)
    pick = random.uniform(0, total_weight)

    winner = None
    accumulated = 0.0
    for prize, weight in weighted_items:
        accumulated += weight
        if pick <= accumulated:
            winner = prize
            break

    if winner is None:
        winner = weighted_items[-1][0]

    # ── Determinar se é resultado "esgotado agindo como retry" ──────────────
    is_exhausted_result = (
        winner.item_type == "prize"
        and winner.quantity == 0
        and winner.exhausted_behavior == "act_as_retry"
    )

    # ── Decrementar estoque ──────────────────────────────────────────────────
    if winner.item_type == "prize" and winner.quantity > 0:
        winner.quantity -= 1

    # ── Gravar no histórico ──────────────────────────────────────────────────
    effective_type = "retry" if is_exhausted_result else winner.item_type
    draw = Draw(
        prize_id=winner.id,
        prize_name=winner.name,
        prize_type=effective_type,
    )
    db.session.add(draw)
    db.session.commit()

    # ── Construir resposta ───────────────────────────────────────────────────
    image_url = None
    if winner.image_filename:
        import os
        upload_path = os.path.join(
            current_app.root_path, "static", "uploads", winner.image_filename
        )
        if os.path.isfile(upload_path):
            image_url = url_for("static", filename=f"uploads/{winner.image_filename}")
    return jsonify({
        "winner_id": winner.id,
        "winner_name": winner.name,
        "winner_type": effective_type,
        "image_url": image_url,
        "is_exhausted_result": is_exhausted_result,
        "remaining_quantity": winner.quantity if winner.item_type == "prize" else None,
    })


# ── Error handlers ───────────────────────────────────────────────────────────

def handle_404(e):
    if request.accept_mimetypes.best == "application/json":
        return jsonify({"error": "not_found", "message": str(e)}), 404
    return render_template("errors/404.html"), 404


def handle_500(e):
    if request.accept_mimetypes.best == "application/json":
        return jsonify({"error": "server_error", "message": "Erro interno do servidor."}), 500
    return render_template("errors/500.html"), 500
