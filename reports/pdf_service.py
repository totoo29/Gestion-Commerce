# reports/pdf_service.py
"""
Capa de orquestacion que combina InvoiceService (registro en DB)
con los generadores de PDF (ReportLab).

Uso desde la UI:
    from reports.pdf_service import print_ticket, print_invoice, print_stock_report
    path = print_ticket(sale_id)          # genera ticket + abre PDF
    path = print_invoice(sale_id)         # genera factura A4 + abre PDF
    path = print_stock_report(products)   # genera reporte de inventario
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.database import SessionLocal
from app.repository.sale_repository import SaleRepository
from app.services.invoice_service import InvoiceService
from app.services.product_service import ProductService
from reports.ticket import generate_ticket
from reports.invoice import generate_invoice
from reports.stock_report import generate_stock_report
from decimal import Decimal

logger = get_logger(__name__)

# ── Clases Mock para Presupuestos ──────────────────────────────────────────────

class MockProduct:
    def __init__(self, name):
        self.name = name

class MockDetail:
    def __init__(self, item):
        self.product_id = item.product_id
        self.product = MockProduct(item.name)
        self.quantity = item.quantity
        self.unit_price = item.unit_price
        self.subtotal = item.subtotal
        self.discount = Decimal("0")

class MockSeller:
    def __init__(self, name):
        self.full_name = name
        self.username = name

class MockSale:
    def __init__(self, cart_items, subtotal, discount, total, seller_name="Vendedor"):
        import random
        self.id = random.randint(1000, 9999) # ID ficticio
        self.details = [MockDetail(i) for i in cart_items]
        self.subtotal = subtotal
        self.discount = discount
        self.total = total
        self.amount_paid = Decimal("0")
        self.change_given = Decimal("0")
        self.payment_method = "A convenir"
        
        from datetime import datetime
        self.created_at = datetime.now()
        self.seller = MockSeller(seller_name)



def _open_pdf(path: Path) -> None:
    """Abre el PDF generado con el visor predeterminado del sistema."""
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        logger.warning(f"No se pudo abrir el PDF automaticamente: {e}")


def print_ticket(sale_id: int, auto_open: bool = True) -> Path:
    """
    Genera el ticket de venta (80mm) para una venta existente.
    Registra el comprobante en la DB y guarda la ruta del PDF.

    Parametros:
        sale_id:   ID de la venta.
        auto_open: Si True, abre el PDF con el visor del sistema.

    Retorna:
        Path al PDF generado.
    """
    with SessionLocal() as session:
        # Obtener la venta con todos sus detalles
        sale_repo = SaleRepository(session)
        sale = sale_repo.get_with_details(sale_id)
        if sale is None:
            raise ValueError(f"Venta #{sale_id} no encontrada.")

        # Generar el PDF fisico
        pdf_path = generate_ticket(sale, output_dir=settings.REPORTS_DIR)

        # Registrar comprobante en DB y guardar ruta del PDF
        try:
            invoice_svc = InvoiceService(session)
            invoice = invoice_svc.generate_invoice(sale_id, invoice_type="ticket")
            invoice_svc.set_pdf_path(invoice.id, str(pdf_path))
        except Exception as e:
            # El PDF ya fue generado; loguear el error pero no fallar
            logger.warning(f"No se pudo registrar el comprobante en DB: {e}")

    logger.info(f"Ticket generado: {pdf_path}")

    if auto_open:
        _open_pdf(pdf_path)

    return pdf_path


def print_invoice(
    sale_id: int,
    customer_id: int | None = None,
    auto_open: bool = True,
) -> Path:
    """
    Genera la factura A4 para una venta.

    Parametros:
        sale_id:     ID de la venta.
        customer_id: ID del cliente (opcional, puede estar en la venta).
        auto_open:   Si True, abre el PDF con el visor del sistema.

    Retorna:
        Path al PDF generado.
    """
    with SessionLocal() as session:
        sale_repo = SaleRepository(session)
        sale = sale_repo.get_with_details(sale_id)
        if sale is None:
            raise ValueError(f"Venta #{sale_id} no encontrada.")

        # Cliente: prioridad al parametro, luego al de la venta
        customer = None
        cid = customer_id or sale.customer_id
        if cid:
            from app.repository.customer_repository import CustomerRepository
            customer = CustomerRepository(session).get_by_id(cid)

        pdf_path = generate_invoice(sale, customer=customer, output_dir=settings.REPORTS_DIR)

        try:
            invoice_svc = InvoiceService(session)
            invoice = invoice_svc.generate_invoice(
                sale_id, invoice_type="factura", customer_id=cid
            )
            invoice_svc.set_pdf_path(invoice.id, str(pdf_path))
        except Exception as e:
            logger.warning(f"No se pudo registrar la factura en DB: {e}")

    logger.info(f"Factura generada: {pdf_path}")

    if auto_open:
        _open_pdf(pdf_path)

    return pdf_path


def print_stock_report(auto_open: bool = True) -> Path:
    """
    Genera el reporte de inventario completo.

    Retorna:
        Path al PDF generado.
    """
    with SessionLocal() as session:
        products = ProductService(session).get_all_products(limit=2000)

    pdf_path = generate_stock_report(products, output_dir=settings.REPORTS_DIR)
    logger.info(f"Reporte de inventario generado: {pdf_path}")

    if auto_open:
        _open_pdf(pdf_path)

    return pdf_path


def print_estimate(
    cart_items: list, 
    subtotal: Decimal, 
    discount: Decimal, 
    total: Decimal, 
    seller_name: str, 
    auto_open: bool = True
) -> Path:
    """
    Genera un presupuesto en PDF (A4 o Ticket) sin alterar la base de datos.
    """
    from app.core.app_settings import ApplicationSettings
    
    sale = MockSale(cart_items, subtotal, discount, total, seller_name)
    app_set = ApplicationSettings.get_settings()
    fmt = app_set.get("print_format", "80mm")
    
    if fmt == "A4":
        pdf_path = generate_invoice(
            sale, 
            output_dir=settings.REPORTS_DIR, 
            doc_type="PRESUPUESTO", 
            doc_subtitle="NO VÁLIDO COMO FACTURA"
        )
    else:
        pdf_path = generate_ticket(
            sale, 
            output_dir=settings.REPORTS_DIR, 
            doc_type="PRESUPUESTO"
        )
        
    logger.info(f"Presupuesto generado: {pdf_path}")
    if auto_open:
        _open_pdf(pdf_path)
    return pdf_path
