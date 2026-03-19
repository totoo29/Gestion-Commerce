# tests/unit/test_pos_view.py
from decimal import Decimal

import customtkinter as ctk
import pytest
from sqlalchemy.orm import Session
import os

from app.services.product_service import ProductService


def test_show_search_results_displays_price(
    session: Session,
    default_price_list,
):
    """Verifica que _show_search_results renderiza al menos una fila y no falla.

    Este test reproduce el bug anterior donde la vista intentaba acceder a
    ``Price.price`` en lugar de ``Price.amount`` y generaba una excepcion.
    """

    # crear un producto con precio para que la lista no quede vacia
    svc = ProductService(session)
    product = svc.create_product(
        sku="UITEST-1",
        name="Producto UITEST",
        prices={default_price_list.id: Decimal("123.45")},
    )

    root = ctk.CTk()
    view = None
    try:
        view = ctk.CTkFrame(master=root)  # necesitamos pasar un master valido
        # No usamos la clase completa POSView porque su constructor hace otras
        # llamadas al sistema que no son necesarias aquí; podemos instanciarla
        # normalmente también ya que no usa la db al crearse.
        from app.ui.views.pos_view import POSView

        view = POSView(root, lambda *_: None)

        # Asegurar que el panel de resultados existe antes de usarlo
        assert hasattr(view, "search_results_frame")

        # Llamamos directamente al metodo para no depender de la busqueda
        view._show_search_results([product])

        children = view.search_results_frame.winfo_children()
        assert len(children) == 1, "Deberia renderizar una fila para el producto"

        # la primera etiqueta del row debe contener el nombre del producto
        row = children[0]
        label = row.winfo_children()[0]
        assert label.cget("text") == "Producto UITEST"

    finally:
        if view:
            root.destroy()


@pytest.mark.skipif(os.environ.get('DISPLAY') is None, reason="require display (X11 or similar)")
def test_cart_totals_update(session: Session, default_price_list):
    """Agregar productos al carrito debe actualizar los totales correctamente.

    También se prueba que el campo de descuento se aplica sin romper la suma.
    """
    svc = ProductService(session)
    prod1 = svc.create_product(
        sku="CART-1",
        name="Cart Product 1",
        prices={default_price_list.id: Decimal("10.00")},
    )
    prod2 = svc.create_product(
        sku="CART-2",
        name="Cart Product 2",
        prices={default_price_list.id: Decimal("5.00")},
    )

    root = ctk.CTk()
    view = __import__('app.ui.views.pos_view', fromlist=['POSView']).POSView(root, lambda *_: None)
    try:
        # añadir dos unidades de prod1 y una de prod2
        view._add_to_cart(prod1, prod1.prices[0].amount)
        view._add_to_cart(prod1, prod1.prices[0].amount)
        view._add_to_cart(prod2, prod2.prices[0].amount)

        # subtotal = 2*10 + 1*5 = 25
        assert view.lbl_subtotal.cget("text") == "$25,00"
        assert view.lbl_total.cget("text") == "$25,00"

        # aplicar descuento de 5
        view.disc_var.set("5")
        view._update_totals()
        assert view.lbl_total.cget("text") == "$20,00"
    finally:
        root.destroy()
