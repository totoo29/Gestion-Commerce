# tests/unit/test_invoice_service.py
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import OperacionInvalidaError, VentaNoEncontradaError
from app.services.invoice_service import InvoiceService
from app.services.sale_service import SaleInput, SaleItemInput, SaleService


def create_completed_sale(session, product_id):
    """Helper: crea una venta completada y retorna el objeto Sale."""
    service = SaleService(session)
    data = SaleInput(
        items=[SaleItemInput(
            product_id=product_id,
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
        )],
        amount_paid=Decimal("100.00"),
    )
    return service.process_sale(data)


class TestInvoiceService:

    def test_generate_ticket(self, session: Session, sample_product):
        """Generar un ticket para una venta completada."""
        sale = create_completed_sale(session, sample_product.id)
        service = InvoiceService(session)

        invoice = service.generate_invoice(sale.id, invoice_type="ticket")

        assert invoice.id is not None
        assert invoice.sale_id == sale.id
        assert invoice.invoice_type == "ticket"
        assert invoice.total == sale.total
        assert invoice.number.startswith("TICKET-")

    def test_generate_invoice_correlative_number(self, session: Session, sample_product):
        """Cada comprobante del mismo tipo tiene numero correlativo unico."""
        service = InvoiceService(session)

        sale1 = create_completed_sale(session, sample_product.id)
        sale2 = create_completed_sale(session, sample_product.id)

        inv1 = service.generate_invoice(sale1.id, invoice_type="ticket")
        inv2 = service.generate_invoice(sale2.id, invoice_type="ticket")

        assert inv1.number != inv2.number
        assert inv1.number == "TICKET-00000001"
        assert inv2.number == "TICKET-00000002"

    def test_generate_invoice_idempotent(self, session: Session, sample_product):
        """Generar comprobante dos veces para la misma venta retorna el mismo."""
        sale = create_completed_sale(session, sample_product.id)
        service = InvoiceService(session)

        inv1 = service.generate_invoice(sale.id, "ticket")
        inv2 = service.generate_invoice(sale.id, "ticket")

        assert inv1.id == inv2.id
        assert inv1.number == inv2.number

    def test_generate_invoice_nonexistent_sale(self, session: Session):
        """Facturar venta inexistente lanza VentaNoEncontradaError."""
        service = InvoiceService(session)

        with pytest.raises(VentaNoEncontradaError):
            service.generate_invoice(99999)

    def test_generate_invoice_cancelled_sale_raises(self, session: Session, sample_product):
        """No se puede facturar una venta cancelada."""
        sale = create_completed_sale(session, sample_product.id)
        sale_service = SaleService(session)
        sale_service.cancel_sale(sale.id)

        invoice_service = InvoiceService(session)
        with pytest.raises(OperacionInvalidaError):
            invoice_service.generate_invoice(sale.id)

    def test_set_pdf_path(self, session: Session, sample_product):
        """Guardar la ruta del PDF generado en el comprobante."""
        sale = create_completed_sale(session, sample_product.id)
        service = InvoiceService(session)
        invoice = service.generate_invoice(sale.id, "ticket")

        service.set_pdf_path(invoice.id, "/reportes/ticket_001.pdf")

        updated = service.get_invoice(invoice.id)
        assert updated.pdf_path == "/reportes/ticket_001.pdf"
