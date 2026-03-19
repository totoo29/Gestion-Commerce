# reports/invoice.py
"""
Generador de factura A4 completa.
Layout profesional con encabezado del negocio, datos del cliente,
tabla de items, totales y pie de pagina.

Uso:
    from reports.invoice import generate_invoice
    path = generate_invoice(sale, customer=customer, output_dir=settings.REPORTS_DIR)
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.config import settings

PAGE_W, PAGE_H = A4
MARGIN_L = 20 * mm
MARGIN_R = 20 * mm
MARGIN_T = 20 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

FONT_NORMAL = "Helvetica"
FONT_BOLD   = "Helvetica-Bold"

COLOR_HEADER = colors.HexColor("#1a1a2e")
COLOR_ACCENT = colors.HexColor("#e94560")
COLOR_ROW_ALT = colors.HexColor("#f5f5f5")
COLOR_TEXT  = colors.HexColor("#222222")
COLOR_LIGHT = colors.HexColor("#888888")


def _fmt(amount: Decimal) -> str:
    return f"${amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_invoice(
    sale,
    customer=None,
    output_dir: Path | None = None,
) -> Path:
    """
    Genera una factura A4 en PDF.

    Parametros:
        sale:       Objeto Sale con .details, .seller, etc.
        customer:   Objeto Customer opcional.
        output_dir: Directorio de salida.

    Retorna:
        Path al archivo PDF generado.
    """
    if output_dir is None:
        output_dir = settings.REPORTS_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = output_dir / f"factura_{sale.id}_{timestamp}.pdf"

    c = canvas.Canvas(str(filename), pagesize=A4)

    # ── Franja superior de color ──────────────────────────────────────────────
    c.setFillColor(COLOR_HEADER)
    c.rect(0, PAGE_H - 30 * mm, PAGE_W, 30 * mm, fill=True, stroke=False)

    # Nombre del negocio en la franja
    c.setFillColor(colors.white)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN_L, PAGE_H - 16 * mm, settings.BUSINESS_NAME.upper())

    c.setFont(FONT_NORMAL, 9)
    header_parts = []
    if settings.BUSINESS_ADDRESS:
        header_parts.append(settings.BUSINESS_ADDRESS)
    if settings.BUSINESS_PHONE:
        header_parts.append(f"Tel: {settings.BUSINESS_PHONE}")
    if settings.BUSINESS_TAX_ID:
        header_parts.append(f"CUIT: {settings.BUSINESS_TAX_ID}")
    c.drawString(MARGIN_L, PAGE_H - 24 * mm, "  |  ".join(header_parts))

    # "FACTURA" en el extremo derecho de la franja
    c.setFont(FONT_BOLD, 22)
    c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 16 * mm, "FACTURA")
    c.setFont(FONT_NORMAL, 9)
    c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 24 * mm, "Comprobante de venta")

    # ── Datos de la venta ─────────────────────────────────────────────────────
    y = PAGE_H - 40 * mm

    # Caja izquierda: datos del cliente
    c.setFillColor(COLOR_TEXT)
    c.setFont(FONT_BOLD, 9)
    c.drawString(MARGIN_L, y, "CLIENTE")
    c.setFont(FONT_NORMAL, 9)
    y -= 5 * mm

    if customer:
        c.drawString(MARGIN_L, y, customer.name)
        y -= 4.5 * mm
        if customer.tax_id:
            c.drawString(MARGIN_L, y, f"CUIT/DNI: {customer.tax_id}")
            y -= 4.5 * mm
        if customer.email:
            c.drawString(MARGIN_L, y, f"Email: {customer.email}")
            y -= 4.5 * mm
        if customer.phone:
            c.drawString(MARGIN_L, y, f"Tel: {customer.phone}")
    else:
        c.setFillColor(COLOR_LIGHT)
        c.drawString(MARGIN_L, y, "Consumidor final")
        c.setFillColor(COLOR_TEXT)

    # Caja derecha: datos del comprobante
    box_x = MARGIN_L + CONTENT_W * 0.6
    box_y = PAGE_H - 40 * mm

    c.setFont(FONT_BOLD, 9)
    c.drawString(box_x, box_y, "N° DE COMPROBANTE")
    c.setFont(FONT_BOLD, 14)
    c.setFillColor(COLOR_ACCENT)
    c.drawString(box_x, box_y - 6 * mm, f"{sale.id:08d}")
    c.setFillColor(COLOR_TEXT)

    c.setFont(FONT_NORMAL, 9)
    fecha = sale.created_at.strftime("%d/%m/%Y") if sale.created_at else datetime.now().strftime("%d/%m/%Y")
    hora  = sale.created_at.strftime("%H:%M")    if sale.created_at else ""
    c.drawString(box_x, box_y - 12 * mm, f"Fecha: {fecha}  {hora}")

    method_label = {
        "efectivo": "Efectivo",
        "tarjeta":  "Tarjeta",
        "transferencia": "Transferencia",
    }.get(sale.payment_method, sale.payment_method.capitalize())
    c.drawString(box_x, box_y - 17 * mm, f"Pago: {method_label}")

    if sale.seller:
        c.drawString(box_x, box_y - 22 * mm, f"Vendedor: {sale.seller.full_name or sale.seller.username}")

    # Linea separadora
    y = PAGE_H - 70 * mm
    c.setStrokeColor(COLOR_ACCENT)
    c.setLineWidth(0.8)
    c.line(MARGIN_L, y, PAGE_W - MARGIN_R, y)
    y -= 6 * mm

    # ── Tabla de items ────────────────────────────────────────────────────────
    # Encabezado de tabla
    c.setFillColor(COLOR_HEADER)
    c.rect(MARGIN_L, y - 1 * mm, CONTENT_W, 7 * mm, fill=True, stroke=False)

    col_desc    = MARGIN_L
    col_qty     = MARGIN_L + CONTENT_W * 0.55
    col_price   = MARGIN_L + CONTENT_W * 0.70
    col_disc    = MARGIN_L + CONTENT_W * 0.83
    col_subtot  = PAGE_W - MARGIN_R

    c.setFillColor(colors.white)
    c.setFont(FONT_BOLD, 8)
    c.drawString(col_desc  + 2 * mm, y + 1.5 * mm, "DESCRIPCION")
    c.drawString(col_qty   + 2 * mm, y + 1.5 * mm, "CANT.")
    c.drawString(col_price + 2 * mm, y + 1.5 * mm, "P.UNIT.")
    c.drawString(col_disc  + 2 * mm, y + 1.5 * mm, "DESC.")
    c.drawRightString(col_subtot, y + 1.5 * mm, "SUBTOTAL")

    y -= 7 * mm
    c.setFillColor(COLOR_TEXT)

    for i, detail in enumerate(sale.details or []):
        # Fila alternada
        if i % 2 == 0:
            c.setFillColor(COLOR_ROW_ALT)
            c.rect(MARGIN_L, y - 1.5 * mm, CONTENT_W, 6.5 * mm, fill=True, stroke=False)
            c.setFillColor(COLOR_TEXT)

        product_name = detail.product.name if detail.product else f"Producto #{detail.product_id}"
        if len(product_name) > 45:
            product_name = product_name[:43] + ".."

        c.setFont(FONT_NORMAL, 8)
        c.drawString(col_desc + 2 * mm, y + 1 * mm, product_name)
        c.drawString(col_qty  + 2 * mm, y + 1 * mm, str(int(detail.quantity)))
        c.drawString(col_price + 2 * mm, y + 1 * mm, _fmt(detail.unit_price))
        disc = detail.discount if detail.discount else Decimal("0")
        c.drawString(col_disc + 2 * mm, y + 1 * mm, _fmt(disc) if disc > 0 else "—")
        c.drawRightString(col_subtot, y + 1 * mm, _fmt(detail.subtotal))

        y -= 6.5 * mm

        # Nueva pagina si no hay espacio
        if y < 60 * mm:
            c.showPage()
            y = PAGE_H - MARGIN_T
            c.setFillColor(COLOR_TEXT)

    # Linea final de la tabla
    c.setStrokeColor(COLOR_ACCENT)
    c.setLineWidth(0.5)
    c.line(MARGIN_L, y, PAGE_W - MARGIN_R, y)
    y -= 6 * mm

    # ── Totales ───────────────────────────────────────────────────────────────
    totals_x = MARGIN_L + CONTENT_W * 0.6

    def draw_total_line(label: str, value: str, bold: bool = False, color=None) -> None:
        nonlocal y
        font  = FONT_BOLD if bold else FONT_NORMAL
        size  = 10 if bold else 9
        c.setFont(font, size)
        if color:
            c.setFillColor(color)
        else:
            c.setFillColor(COLOR_TEXT)
        c.drawString(totals_x, y, label)
        c.drawRightString(PAGE_W - MARGIN_R, y, value)
        c.setFillColor(COLOR_TEXT)
        y -= (size * 0.4 + 1.5) * mm

    draw_total_line("Subtotal:", _fmt(sale.subtotal))
    if sale.discount and sale.discount > 0:
        draw_total_line("Descuento:", f"- {_fmt(sale.discount)}", color=COLOR_ACCENT)

    y -= 1 * mm
    # Recuadro para el TOTAL
    c.setFillColor(COLOR_HEADER)
    c.rect(totals_x - 2 * mm, y - 2.5 * mm, PAGE_W - MARGIN_R - totals_x + 4 * mm, 9 * mm,
           fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont(FONT_BOLD, 11)
    c.drawString(totals_x, y, "TOTAL:")
    c.drawRightString(PAGE_W - MARGIN_R, y, _fmt(sale.total))
    c.setFillColor(COLOR_TEXT)
    y -= 10 * mm

    draw_total_line(f"Recibido ({method_label}):", _fmt(sale.amount_paid))
    draw_total_line("Vuelto:", _fmt(sale.change_given))

    # ── Pie de pagina ─────────────────────────────────────────────────────────
    c.setFillColor(COLOR_HEADER)
    c.rect(0, 0, PAGE_W, 14 * mm, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont(FONT_NORMAL, 7)
    footer_text = f"Generado por DevMont Commerce  •  {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if settings.BUSINESS_EMAIL:
        footer_text += f"  •  {settings.BUSINESS_EMAIL}"
    c.drawCentredString(PAGE_W / 2, 5 * mm, footer_text)

    c.save()
    return filename
