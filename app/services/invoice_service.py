# app/services/invoice_service.py
from sqlalchemy.orm import Session

from app.core.exceptions import OperacionInvalidaError, VentaNoEncontradaError
from app.core.logging import get_logger
from app.models.invoice import Invoice
from app.repository.invoice_repository import InvoiceRepository
from app.repository.sale_repository import SaleRepository

logger = get_logger(__name__)


class InvoiceService:

    def __init__(self, session: Session):
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.sale_repo = SaleRepository(session)

    def generate_invoice(
        self,
        sale_id: int,
        invoice_type: str = "ticket",
        customer_id: int | None = None,
    ) -> Invoice:
        """
        Genera un comprobante para una venta existente.
        Si la venta ya tiene comprobante, retorna el existente.
        """
        # Verificar que la venta existe
        sale = self.sale_repo.get_with_details(sale_id)
        if sale is None:
            raise VentaNoEncontradaError(sale_id)

        if sale.status != "completed":
            raise OperacionInvalidaError(
                f"No se puede facturar una venta en estado '{sale.status}'."
            )

        # Si ya tiene comprobante, retornarlo sin crear uno nuevo
        existing = self.invoice_repo.get_by_sale_id(sale_id)
        if existing is not None:
            logger.info(f"Comprobante ya existente para venta id={sale_id}: {existing.number}")
            return existing

        # Generar numero correlativo
        number = self.invoice_repo.get_next_number(invoice_type)

        invoice = Invoice(
            sale_id=sale_id,
            customer_id=customer_id or sale.customer_id,
            invoice_type=invoice_type,
            number=number,
            subtotal=sale.subtotal,
            tax=sale.tax,
            total=sale.total,
        )
        self.session.add(invoice)
        self.session.commit()

        logger.info(f"Comprobante generado: {number} para venta id={sale_id}")
        return invoice

    def get_invoice(self, invoice_id: int) -> Invoice | None:
        return self.invoice_repo.get_by_id(invoice_id)

    def get_invoice_by_sale(self, sale_id: int) -> Invoice | None:
        return self.invoice_repo.get_by_sale_id(sale_id)

    def set_pdf_path(self, invoice_id: int, pdf_path: str) -> None:
        """Guarda la ruta del PDF generado en el comprobante."""
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if invoice:
            invoice.pdf_path = pdf_path
            self.session.commit()
