import io
import csv
from datetime import date, datetime
from flask import Blueprint, Response, current_app
from app.models import Draw, Setting

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/csv")
def export_csv():
    """Exporta o histórico completo de sorteios em CSV (UTF-8 com BOM para Excel)."""
    draws = Draw.query.order_by(Draw.drawn_at).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Data/Hora", "Nome do Brinde", "Tipo", "Prêmio Real"])

    for draw in draws:
        writer.writerow([
            draw.id,
            draw.drawn_at.strftime("%d/%m/%Y %H:%M:%S"),
            draw.prize_name,
            draw.prize_type,
            "Sim" if draw.prize_type == "prize" else "Não",
        ])

    output.seek(0)
    # BOM para compatibilidade com Excel no Windows
    content = "\ufeff" + output.getvalue()

    return Response(
        content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=historico_sorteios_{date.today()}.csv"
        },
    )


@reports_bp.route("/pdf")
def export_pdf():
    """Exporta o histórico completo de sorteios em PDF via ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    draws = Draw.query.order_by(Draw.drawn_at).all()
    event_name = Setting.get("event_name", "Roleta de Brindes")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=18, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=11, textColor=colors.grey
    )

    story = []

    # Cabeçalho
    story.append(Paragraph(event_name, title_style))
    story.append(Paragraph("Relatório de Sorteios", subtitle_style))
    story.append(Paragraph(
        f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        subtitle_style,
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 0.3 * cm))

    # Resumo
    total = len(draws)
    total_prizes_won = sum(1 for d in draws if d.prize_type == "prize")
    total_retry = sum(1 for d in draws if d.prize_type == "retry")
    total_no_win = sum(1 for d in draws if d.prize_type == "no_win")

    summary_data = [
        ["Total de sorteios", str(total)],
        ["Prêmios entregues", str(total_prizes_won)],
        ['"Tente Novamente"', str(total_retry)],
        ['"Não Ganhou"', str(total_no_win)],
    ]
    summary_table = Table(summary_data, colWidths=[8 * cm, 4 * cm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # Tabela de sorteios
    type_labels = {"prize": "Prêmio", "retry": "Tente Novamente", "no_win": "Não Ganhou"}
    type_colors = {
        "prize": colors.HexColor("#27ae60"),
        "retry": colors.HexColor("#e67e22"),
        "no_win": colors.HexColor("#7f8c8d"),
    }

    header = ["#", "Data/Hora", "Brinde", "Tipo"]
    table_data = [header]
    for draw in draws:
        table_data.append([
            str(draw.id),
            draw.drawn_at.strftime("%d/%m/%Y %H:%M:%S"),
            draw.prize_name,
            type_labels.get(draw.prize_type, draw.prize_type),
        ])

    col_widths = [1.2 * cm, 4.5 * cm, 9 * cm, 3.8 * cm]
    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    ts = TableStyle([
        # Cabeçalho
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        # Dados
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
    ])
    # Colorir coluna Tipo por tipo
    for i, draw in enumerate(draws, start=1):
        c = type_colors.get(draw.prize_type, colors.grey)
        ts.add("TEXTCOLOR", (3, i), (3, i), c)
        ts.add("FONTNAME", (3, i), (3, i), "Helvetica-Bold")

    main_table.setStyle(ts)
    story.append(main_table)

    # Rodapé via onLaterPages
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        footer_text = f"Página {doc.page} — Roleta Virtual — gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, footer_text)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_sorteios_{date.today()}.pdf"
        },
    )
