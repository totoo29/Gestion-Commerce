# app/services/sale_service.py
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import MovementType
from app.core.exceptions import ProductoNoEncontradoError, StockInsuficienteError
from app.core.logging import get_logger
from app.models.sale import Sale, SaleDetail
from app.repository.product_repository import ProductRepository
from app.repository.sale_repository import SaleRepository
from app.repository.stock_repository import StockRepository

logger = get_logger(__name__)


@dataclass
class SaleItemInput:
    """Datos de un item para procesar una venta."""
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal("0")


@dataclass
class SaleInput:
    """Datos completos de entrada para procesar una venta."""
    items: list[SaleItemInput]
    payment_method: str = "efectivo"
    amount_paid: Decimal = Decimal("0")
    customer_id: int | None = None
    discount: Decimal = Decimal("0")
    notes: str | None = None


class SaleService:

    def __init__(self, session: Session):
        self.session = session
        self.sale_repo = SaleRepository(session)
        self.stock_repo = StockRepository(session)
        self.product_repo = ProductRepository(session)

    def process_sale(self, data: SaleInput, seller_id: int | None = None) -> Sale:
        """
        Procesa una venta de forma ATOMICA:
          1. Verifica stock disponible para cada item (con lock)
          2. Descuenta el stock
          3. Registra el movimiento de stock
          4. Crea la venta y sus detalles
          5. Commit unico al final

        Si cualquier paso falla, se hace rollback total.
        """
        try:
            details = []
            subtotal = Decimal("0")

            for item in data.items:
                # Verificar que el producto existe
                product = self.product_repo.get_by_id(item.product_id)
                if product is None:
                    raise ProductoNoEncontradoError(item.product_id)

                # Obtener stock con bloqueo para evitar doble descuento
                stock = self.stock_repo.get_with_lock(item.product_id)
                if stock is None:
                    raise ProductoNoEncontradoError(item.product_id)

                if stock.quantity < item.quantity:
                    raise StockInsuficienteError(
                        product_id=item.product_id,
                        disponible=int(stock.quantity),
                        requerido=int(item.quantity),
                    )

                # Descontar stock
                stock_before = stock.quantity
                stock.quantity -= item.quantity

                # Registrar movimiento
                self.stock_repo.create_movement(
                    stock_id=stock.id,
                    movement_type=MovementType.SALE,
                    quantity=-item.quantity,
                    stock_before=stock_before,
                    stock_after=stock.quantity,
                    created_by=seller_id,
                    reference_type="sale",
                )

                # Calcular subtotal del item
                item_subtotal = (item.unit_price * item.quantity) - item.discount
                subtotal += item_subtotal

                details.append(SaleDetail(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                    subtotal=item_subtotal,
                ))

            # Calcular totales de la venta
            total = subtotal - data.discount
            change_given = max(Decimal("0"), data.amount_paid - total)

            # Crear cabecera de venta
            sale = Sale(
                seller_id=seller_id,
                customer_id=data.customer_id,
                subtotal=subtotal,
                discount=data.discount,
                tax=Decimal("0"),
                total=total,
                payment_method=data.payment_method,
                amount_paid=data.amount_paid,
                change_given=change_given,
                status="completed",
                notes=data.notes,
            )
            self.session.add(sale)
            self.session.flush()  # Obtener el ID de la venta

            # Asociar detalles a la venta
            for detail in details:
                detail.sale_id = sale.id
                self.session.add(detail)

            # Actualizar referencia en movimientos de stock
            # (ahora que tenemos el sale.id)
            self.session.flush()

            self.session.commit()  # <-- Commit unico

            logger.info(
                f"Venta procesada: id={sale.id}, "
                f"total={total}, items={len(details)}, "
                f"vendedor={seller_id}"
            )
            return sale

        except Exception:
            self.session.rollback()  # <-- Rollback total si algo falla
            raise

    def cancel_sale(self, sale_id: int, user_id: int | None = None) -> Sale:
        """
        Cancela una venta y devuelve el stock a los niveles previos.
        Solo se pueden cancelar ventas en estado 'completed'.
        """
        from app.core.exceptions import OperacionInvalidaError, VentaNoEncontradaError

        sale = self.sale_repo.get_with_details(sale_id)
        if sale is None:
            raise VentaNoEncontradaError(sale_id)

        if sale.status != "completed":
            raise OperacionInvalidaError(
                f"No se puede cancelar una venta en estado '{sale.status}'."
            )

        try:
            # Devolver stock por cada item
            for detail in sale.details:
                stock = self.stock_repo.get_with_lock(detail.product_id)
                if stock:
                    stock_before = stock.quantity
                    stock.quantity += detail.quantity
                    self.stock_repo.create_movement(
                        stock_id=stock.id,
                        movement_type=MovementType.RETURN,
                        quantity=detail.quantity,
                        stock_before=stock_before,
                        stock_after=stock.quantity,
                        created_by=user_id,
                        reference_id=sale_id,
                        reference_type="sale_cancel",
                    )

            sale.status = "cancelled"
            self.session.commit()

            logger.info(f"Venta cancelada: id={sale_id}")
            return sale

        except Exception:
            self.session.rollback()
            raise

    def get_sale(self, sale_id: int) -> Sale:
        from app.core.exceptions import VentaNoEncontradaError
        sale = self.sale_repo.get_with_details(sale_id)
        if sale is None:
            raise VentaNoEncontradaError(sale_id)
        return sale

    def get_today_sales(self) -> list[Sale]:
        return self.sale_repo.get_today_sales()

    def get_today_total(self) -> Decimal:
        return self.sale_repo.get_today_total()

    def get_today_count(self) -> int:
        return self.sale_repo.count_today()
