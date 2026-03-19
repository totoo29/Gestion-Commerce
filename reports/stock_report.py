# reports/stock_report.py
"""
Generador de reporte de inventario A4.
Lista todos los productos con su stock actual, minimo y estado.

Uso:
    from reports.stock_report import generate_stock_report
    path = generate_stock_report(products, output_dir=settings.REPORTS_DIR)
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
MARGIN_L  = 15 * mm
MARGIN_R  = 15 * mm
MARGIN_T  = 15 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

FONT_NORMAL = "Helvetica"
FONT_BOLD   = "Helvetica-Bold"

COLOR_HEADER  = colors.HexColor("#1a1a2e")
COLOR_ACCENT  = colors.HexColor("#e94560")
COLOR_OK      = colors.HexColor("#27ae60")
COLOR_WARNING = colors.HexColor("#f39c12")
COLOR_CRITICAL= colors.HexColor("#e74c3c")
COLOR_ROW_ALT = colors.HexColor("#f5f5f5")
COLOR_TEXT    = colors.HexColor("#222222")
COLOR_LIGHT   = colors.HexColor("#888888")


def generate_stock_report(
    products: list,
    output_dir: Path | None = None,
) -> Path:
    """
    Genera el reporte de inventario completo en PDF A4.

    Parametros:
        products:   Lista de objetos Product con .stock cargado.
        output_dir: Directorio de salida.

    Retorna:
        Path al archivo PDF generado.
    """
    if output_dir is None:
        output_dir = settings.REPORTS_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = output_dir / f"inventario_{timestamp}.pdf"

    c = canvas.Canvas(str(filename), pagesize=A4)

    def draw_page_header(page_num: int) -> float:
        """Dibuja el encabezado de pagina. Retorna la Y inicial del contenido."""
        # Franja superior
        c.setFillColor(COLOR_HEADER)
        c.rect(0, PAGE_H - 22 * mm, PAGE_W, 22 * mm, fill=True, stroke=False)

        c.setFillColor(colors.white)
        c.setFont(FONT_BOLD, 14)
        c.drawString(MARGIN_L, PAGE_H - 10 * mm, "REPORTE DE INVENTARIO")
        c.setFont(FONT_NORMAL, 8)
        c.drawString(MARGIN_L, PAGE_H - 17 * mm, settings.BUSINESS_NAME)
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 10 * mm,
                          datetime.now().strftime("%d/%m/%Y  %H:%M"))
        c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 17 * mm, f"Pag. {page_num}")

        return PAGE_H - 28 * mm

    def draw_table_header(y: float) -> float:
        """Dibuja encabezado de la tabla. Retorna nueva Y."""
        c.setFillColor(COLOR_HEADER)
        c.rect(MARGIN_L, y - 1 * mm, CONTENT_W, 7 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont(FONT_BOLD, 8)
        c.drawString(MARGIN_L + 2 * mm,      y + 1.5 * mm, "SKU")
        c.drawString(MARGIN_L + 25 * mm,     y + 1.5 * mm, "PRODUCTO")
        c.drawString(MARGIN_L + 105 * mm,    y + 1.5 * mm, "UNIDAD")
        c.drawString(MARGIN_L + 125 * mm,    y + 1.5 * mm, "STOCK ACT.")
        c.drawString(MARGIN_L + 148 * mm,    y + 1.5 * mm, "STOCK MIN.")
        c.drawRightString(PAGE_W - MARGIN_R, y + 1.5 * mm, "ESTADO")
        c.setFillColor(COLOR_TEXT)
        return y - 8 * mm

    # ── Inicio del PDF ────────────────────────────────────────────────────────
    page_num = 1
    y = draw_page_header(page_num)

    # Resumen estadistico
    total_products = len(products)
    critical = sum(1 for p in products
                   if p.stock and p.stock.min_quantity > 0
                   and p.stock.quantity <= p.stock.min_quantity)
    low      = sum(1 for p in products
                   if p.stock and p.stock.min_quantity > 0
                   and p.stock.quantity > p.stock.min_quantity
                   and p.stock.quantity <= p.stock.min_quantity * Decimal("1.5"))
    ok       = total_products - critical - low

    c.setFillColor(COLOR_TEXT)
    c.setFont(FONT_NORMAL, 8)
    summary = (f"Total productos: {total_products}   "
               f"OK: {ok}   "
               f"Stock bajo: {low}   "
               f"Stock crítico: {critical}")
    c.drawString(MARGIN_L, y, summary)
    y -= 6 * mm

    # Leyenda de colores
    for color_item, label in [
        (COLOR_OK,       "OK"),
        (COLOR_WARNING,  "Bajo"),
        (COLOR_CRITICAL, "Critico"),
    ]:
        c.setFillColor(color_item)
        c.rect(MARGIN_L, y - 1 * mm, 3 * mm, 3 * mm, fill=True, stroke=False)
        c.setFillColor(COLOR_TEXT)
        c.setFont(FONT_NORMAL, 7)
        c.drawString(MARGIN_L + 4.5 * mm, y, label)
        MARGIN_L_offset = MARGIN_L + 20 * mm  # Solo para esta iteracion visual
        # Reset y avanzar el margen logicamente con X
        break  # Solo dibujar la leyenda en linea, simplificado

    y -= 5 * mm

    c.setStrokeColor(COLOR_ACCENT)
    c.setLineWidth(0.5)
    c.line(MARGIN_L, y, PAGE_W - MARGIN_R, y)
    y -= 5 * mm

    y = draw_table_header(y)

    # ── Filas de productos ────────────────────────────────────────────────────
    for i, product in enumerate(products):
        # Nueva pagina si falta espacio
        if y < 25 * mm:
            c.showPage()
            page_num += 1
            y = draw_page_header(page_num)
            y = draw_table_header(y)

        stock     = product.stock
        qty       = stock.quantity     if stock else Decimal("0")
        min_qty   = stock.min_quantity if stock else Decimal("0")

        # Determinar estado y color
        if min_qty > 0 and qty <= min_qty:
            estado_txt   = "CRITICO"
            estado_color = COLOR_CRITICAL
        elif min_qty > 0 and qty <= min_qty * Decimal("1.5"):
            estado_txt   = "BAJO"
            estado_color = COLOR_WARNING
        else:
            estado_txt   = "OK"
            estado_color = COLOR_OK

        # Fila alternada
        if i % 2 == 0:
            c.setFillColor(COLOR_ROW_ALT)
            c.rect(MARGIN_L, y - 1.5 * mm, CONTENT_W, 6 * mm, fill=True, stroke=False)

        c.setFillColor(COLOR_TEXT)
        c.setFont(FONT_NORMAL, 8)

        sku_text  = (product.sku[:12] + "..") if len(product.sku) > 14 else product.sku
        name_text = product.name
        if len(name_text) > 34:
            name_text = name_text[:32] + ".."

        c.drawString(MARGIN_L + 2 * mm,      y + 0.5 * mm, sku_text)
        c.drawString(MARGIN_L + 25 * mm,     y + 0.5 * mm, name_text)
        c.drawString(MARGIN_L + 105 * mm,    y + 0.5 * mm, product.unit or "")
        c.drawString(MARGIN_L + 125 * mm,    y + 0.5 * mm, f"{qty:,.0f}")
        c.drawString(MARGIN_L + 148 * mm,    y + 0.5 * mm, f"{min_qty:,.0f}")

        # Badge de estado
        badge_x = PAGE_W - MARGIN_R - 20 * mm
        c.setFillColor(estado_color)
        c.roundRect(badge_x, y - 1 * mm, 18 * mm, 5 * mm, 2, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont(FONT_BOLD, 7)
        c.drawCentredString(badge_x + 9 * mm, y + 0.5 * mm, estado_txt)

        y -= 6.5 * mm

    # ── Pie de pagina final ───────────────────────────────────────────────────
    c.setFillColor(COLOR_HEADER)
    c.rect(0, 0, PAGE_W, 10 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont(FONT_NORMAL, 7)
    c.drawCentredString(PAGE_W / 2, 3 * mm,
                        f"DevMont Commerce  •  Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.save()
    return filename
