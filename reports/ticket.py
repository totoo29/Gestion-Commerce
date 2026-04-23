# reports/ticket.py
"""
Generador de ticket de venta para impresora termica (ancho 80mm).
Usa ReportLab con canvas para control total del layout.

Uso:
    from reports.ticket import generate_ticket
    path = generate_ticket(sale, output_dir=settings.REPORTS_DIR)
    # Retorna Path al PDF generado
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.core.logging import get_logger
logger = get_logger(__name__)

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.core.app_settings import ApplicationSettings

# ── Dimensiones del ticket ────────────────────────────────────────────────────
TICKET_W    = 80 * mm       # Ancho del papel termico 80mm
MARGIN      = 4  * mm       # Margen lateral
CONTENT_W   = TICKET_W - 2 * MARGIN

# Fuentes y tamanios
FONT_NORMAL = "Helvetica"
FONT_BOLD   = "Helvetica-Bold"


def _fmt(amount: Decimal) -> str:
    """Formatea un Decimal como moneda con separador de miles."""
    return f"${amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_ticket(
    sale, 
    output_dir: Path | None = None,
    doc_type: str = "TICKET DE VENTA"
) -> Path:
    """
    Genera el ticket de venta en PDF para impresora termica.

    Parametros:
        sale:       Objeto Sale de SQLAlchemy con .details, .seller, etc.
        output_dir: Directorio de salida. Por defecto: settings.REPORTS_DIR
        doc_type:   TItulo principal del ticket

    Retorna:
        Path al archivo PDF generado.
    """
    if output_dir is None:
        output_dir = settings.REPORTS_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_slug = doc_type.lower().split()[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = output_dir / f"{doc_slug}_{sale.id}_{timestamp}.pdf"

    app_set = ApplicationSettings.get_settings()
    logo_path = app_set.get("logo_path", "")
    logo_exists = bool(logo_path and Path(logo_path).exists())

    # Calcular alto dinamico segun cantidad de items y presencia de logo
    n_items    = len(sale.details) if sale.details else 0
    base_height = 110 * mm
    if logo_exists:
        base_height += 40 * mm  # Agregar espacio extra para el logo
    
    item_height = 7  * mm
    page_height = base_height + (n_items * item_height)

    c = canvas.Canvas(str(filename), pagesize=(TICKET_W, page_height))
    y = page_height - 6 * mm   # Cursor vertical (de arriba hacia abajo)

    def draw_text(text: str, font: str, size: float, align: str = "center") -> None:
        nonlocal y
        c.setFont(font, size)
        if align == "center":
            c.drawCentredString(TICKET_W / 2, y, text)
        elif align == "left":
            c.drawString(MARGIN, y, text)
        elif align == "right":
            c.drawRightString(TICKET_W - MARGIN, y, text)
        y -= size * 0.45 * mm + 1 * mm

    def draw_line(dashed: bool = False) -> None:
        nonlocal y
        y -= 1.5 * mm
        if dashed:
            c.setDash(2, 2)
        else:
            c.setDash()
        c.line(MARGIN, y, TICKET_W - MARGIN, y)
        c.setDash()
        y -= 4 * mm  # Salto corregido global para no pisar el tope de nuevas letras

    # ── Logo ──────────────────────────────────────────────────────────────────
    if logo_exists:
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            logo_width = 30 * mm
            logo_height = logo_width * aspect
            y -= logo_height
            c.drawImage(logo_path, (TICKET_W - logo_width) / 2, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask="auto")
            y -= 3 * mm
        except Exception as e:
            logger.error(f"No se pudo cargar el logo del ticket: {e}")

    # ── Encabezado ────────────────────────────────────────────────────────────
    draw_text(app_set.get("company_name", "Mi Empresa").upper(), FONT_BOLD, 12)
    address = app_set.get("address", "")
    if address:
        draw_text(address, FONT_NORMAL, 7)
    phone = app_set.get("phone", "")
    if phone:
        draw_text(f"Tel: {phone}", FONT_NORMAL, 7)
    cuit = app_set.get("company_id", "")
    if cuit:
        draw_text(cuit, FONT_NORMAL, 7)

    draw_line()

    # ── Datos de la venta ─────────────────────────────────────────────────────

    if "PRESUPUESTO" in doc_type:
        c.setFont(FONT_BOLD, 9)
        c.drawCentredString(TICKET_W / 2, y, "PRESUPUESTO")
        y -= 4 * mm
        c.setFont(FONT_BOLD, 6)
        c.drawCentredString(TICKET_W / 2, y, "NO VÁLIDO COMO FACTURA")
        y -= 5 * mm
    else:
        draw_text(doc_type, FONT_BOLD, 9)
        y -= 1 * mm

    if sale.created_at:
        from datetime import timezone
        local_dt = sale.created_at.replace(tzinfo=timezone.utc).astimezone()
        fecha = local_dt.strftime("%d/%m/%Y  %H:%M")
    else:
        fecha = datetime.now().strftime("%d/%m/%Y  %H:%M")

    draw_text(f"N° {sale.id:06d}   {fecha}", FONT_NORMAL, 7)

    if sale.seller:
        draw_text(f"Atendido por: {sale.seller.full_name or sale.seller.username}", FONT_NORMAL, 7)

    draw_line(dashed=True)

    # ── Items ─────────────────────────────────────────────────────────────────
    c.setFont(FONT_BOLD, 7)
    c.drawString(MARGIN, y, "PRODUCTO")
    c.drawRightString(TICKET_W - MARGIN, y, "SUBTOTAL")
    y -= 5 * mm

    for detail in (sale.details or []):
        product_name = detail.product.name if detail.product else f"Prod.#{detail.product_id}"
        # Truncar nombre largo
        if len(product_name) > 28:
            product_name = product_name[:26] + ".."

        qty_price = f"{int(detail.quantity)} x {_fmt(detail.unit_price)}"
        subtotal  = _fmt(detail.subtotal)

        c.setFont(FONT_BOLD, 7)
        c.drawString(MARGIN, y, product_name)
        y -= 4.5 * mm

        c.setFont(FONT_NORMAL, 7)
        c.drawString(MARGIN + 2 * mm, y, qty_price)
        c.drawRightString(TICKET_W - MARGIN, y, subtotal)
        y -= 5 * mm

    draw_line(dashed=True)

    # ── Totales ───────────────────────────────────────────────────────────────
    def draw_total_row(label: str, value: str, bold: bool = False) -> None:
        nonlocal y
        font = FONT_BOLD if bold else FONT_NORMAL
        size = 8 if bold else 7
        c.setFont(font, size)
        c.drawString(MARGIN, y, label)
        c.drawRightString(TICKET_W - MARGIN, y, value)
        y -= (size * 0.45 + 1) * mm

    draw_total_row("Subtotal:", _fmt(sale.subtotal))
    if sale.discount and sale.discount > 0:
        draw_total_row(f"Descuento:", f"- {_fmt(sale.discount)}")

    y -= 1 * mm
    draw_total_row("TOTAL:", _fmt(sale.total), bold=True)
    y -= 1 * mm

    method_label = {
        "efectivo": "Efectivo",
        "tarjeta":  "Tarjeta",
        "transferencia": "Transferencia",
    }.get(sale.payment_method, sale.payment_method.capitalize())

    draw_total_row(f"Recibido ({method_label}):", _fmt(sale.amount_paid))
    draw_total_row("Vuelto:", _fmt(sale.change_given))

    draw_line()

    # ── Pie ───────────────────────────────────────────────────────────────────
    footer = app_set.get("footer_text", "¡Gracias por su compra!")
    if footer:
        draw_text(footer, FONT_NORMAL, 7)

    draw_text("Conserve este ticket", FONT_NORMAL, 7)
    y -= 4 * mm

    c.save()
    return filename
