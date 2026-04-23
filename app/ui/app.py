# app/ui/app.py
from typing import Callable, Type

import customtkinter as ctk

from app.core.logging import get_logger
from app.ui.theme import COLORS, SIZES

logger = get_logger(__name__)


class DevMontApp(ctk.CTk):
    """
    Ventana raiz de DevMont Commerce.
    Gestiona la navegacion entre vistas destruyendo la vista anterior
    y creando la nueva. Cada vista recibe una funcion `navigate`
    para poder cambiar de pantalla sin conocer la ventana raiz.
    """

    def __init__(self):
        super().__init__()

        # ── Configuracion de la ventana ───────────────────────────────────────
        self.title("DevMont Commerce — Sistema de Gestión")
        self.geometry(f"{SIZES['window_w']}x{SIZES['window_h']}")
        self.minsize(1024, 600)
        self.configure(fg_color=COLORS["bg_main"])

        # Icono (si existe el archivo)
        try:
            self.iconbitmap("assets/icon.ico")
        except Exception:
            pass

        # Centrar ventana en pantalla
        self._center_window()

        # Interceptar cierre para limpieza
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._current_view = None
        self._current_view_name = None
        
        # Caché de vistas para optimización
        self._views_cache = {}

        # Iniciar en login
        self.show_view("login")

    # ── Navegacion ────────────────────────────────────────────────────────────

    def show_view(self, view_name: str, **kwargs) -> None:
        """
        Navega a una vista por nombre.
        Utiliza un caché para evitar destruir y reconstruir las vistas.
        """
        # Excepciones que siempre deberían forzar una destrucción del caché general,
        # como volver al login (logout).
        if view_name == "login":
            # Si vamos a login, destruimos todo el caché menos el login para limpiar la sesión
            for name, view in list(self._views_cache.items()):
                if name != "login":
                    view.destroy()
                    del self._views_cache[name]
                    
            if self._current_view is not None and self._current_view_name != "login":
                self._current_view.pack_forget()

        else:
            # Ocultar vista actual sin destruirla
            if self._current_view is not None:
                self._current_view.pack_forget()

        # Comprobar si la vista ya existe en caché y si no estamos forzando su recarga por kwargs
        if view_name in self._views_cache and not kwargs.get('force_reload', False):
            self._current_view = self._views_cache[view_name]
            self._current_view_name = view_name
            self._current_view.pack(fill="both", expand=True)
            
            # Si la vista tiene un método refresh() o load_data(), lo llamamos para actualizar los datos
            if hasattr(self._current_view, "refresh"):
                self._current_view.refresh()
            elif hasattr(self._current_view, "load_data"):
                self._current_view.load_data()
                
            logger.info(f"Navegando a vista (desde caché): {view_name}")
            return

        # Si no existe, crearla y guardarla en caché
        ViewClass = self._get_view_class(view_name)
        if ViewClass is None:
            logger.error(f"Vista desconocida: '{view_name}'")
            return

        try:
            self._current_view = ViewClass(
                self,
                navigate=self.show_view,
                **kwargs,
            )
            self._views_cache[view_name] = self._current_view
            self._current_view_name = view_name
            self._current_view.pack(fill="both", expand=True)
            logger.info(f"Navegando a vista (nueva): {view_name}")
        except Exception as e:
            logger.error(f"Error al crear vista '{view_name}': {e}")
            raise

    def _get_view_class(self, view_name: str) -> Type | None:
        """Retorna la clase de vista correspondiente al nombre."""
        # Import diferido: cada vista se importa solo cuando se necesita
        if view_name == "login":
            from app.ui.views.login_view import LoginView
            return LoginView

        if view_name == "dashboard":
            from app.ui.views.dashboard_view import DashboardView
            return DashboardView

        if view_name == "pos":
            from app.ui.views.pos_view import POSView
            return POSView

        if view_name == "products":
            from app.ui.views.products_view import ProductsView
            return ProductsView

        if view_name == "stock":
            from app.ui.views.stock_view import StockView
            return StockView

        if view_name == "sales":
            from app.ui.views.sales_view import SalesView
            return SalesView

        if view_name == "purchases":
            from app.ui.views.purchases_view import PurchasesView
            return PurchasesView

        if view_name == "suppliers":
            from app.ui.views.suppliers_view import SuppliersView
            return SuppliersView

        if view_name == "customers":
            from app.ui.views.customers_view import CustomersView
            return CustomersView

        if view_name == "reports":
            from app.ui.views.reports_view import ReportsView
            return ReportsView

        if view_name == "import":
            from app.ui.views.import_view import ImportView
            return ImportView

        if view_name == "settings":
            from app.ui.views.settings_view import SettingsView
            return SettingsView

        return None

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def _center_window(self) -> None:
        """Centra la ventana en el monitor principal."""
        self.update_idletasks()
        w = SIZES["window_w"]
        h = SIZES["window_h"]
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_close(self) -> None:
        """Limpieza al cerrar la ventana."""
        logger.info("Cerrando DevMont Commerce.")
        self.destroy()
