# app/services/import_service.py
"""
Servicio de importacion de productos desde Excel (.xlsx / .xls / .csv).

Columnas soportadas (insensible a mayusculas y espacios):
    sku / codigo          → Product.sku          (requerido)
    nombre / name         → Product.name         (requerido)
    descripcion           → Product.description
    unidad / unit         → Product.unit
    precio / price        → Price (lista de precios id=1)
    stock / cantidad      → Stock.quantity
    stock_minimo          → Stock.min_quantity
    categoria / category  → Category.name
    barcode / cod_barras  → Barcode.code

Comportamiento si el producto ya existe (identificado por SKU):
    - Actualiza nombre, descripcion, unidad, categoria
    - Actualiza precio
    - Ajusta stock al valor del Excel
    - Agrega barcodes nuevos (no elimina los existentes)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.product import Category
from app.repository.product_repository import ProductRepository
from app.services.product_service import ProductService
from app.services.stock_service import StockService

logger = get_logger(__name__)

# Mapeo de nombres de columna posibles → campo canonico
COLUMN_ALIASES: dict[str, str] = {
    # SKU
    "sku": "sku", "codigo": "sku", "code": "sku", "cod": "sku",
    "código": "sku",
    # Nombre
    "nombre": "name", "name": "name", "producto": "name", "descripcion_corta": "name",
    # Descripcion
    "descripcion": "description", "description": "description", "detalle": "description",
    "descripción": "description",
    # Unidad
    "unidad": "unit", "unit": "unit", "um": "unit", "unid": "unit",
    # Precio
    "precio": "price", "price": "price", "precio_venta": "price",
    "pvp": "price", "importe": "price",
    # Stock
    "stock": "stock", "cantidad": "stock", "quantity": "stock",
    "existencia": "stock", "existencias": "stock",
    # Stock minimo
    "stock_minimo": "min_stock", "stock minimo": "min_stock",
    "min_stock": "min_stock", "minimo": "min_stock", "mínimo": "min_stock",
    # Categoria
    "categoria": "category", "category": "category", "rubro": "category",
    "categoría": "category",
    # Barcode
    "barcode": "barcode", "cod_barras": "barcode", "codigo_barras": "barcode",
    "ean": "barcode", "ean13": "barcode", "codigo de barras": "barcode",
    "código de barras": "barcode",
}

PRICE_LIST_ID = 1   # ID de la lista de precios principal


@dataclass
class ImportRow:
    """Resultado del procesamiento de una fila del Excel."""
    row_number: int
    sku: str
    name: str
    action: str = ""        # "created" | "updated" | "skipped" | "error"
    error: str  = ""


@dataclass
class ImportResult:
    """Resultado completo de una importacion."""
    total:    int = 0
    created:  int = 0
    updated:  int = 0
    skipped:  int = 0
    errors:   int = 0
    rows: list[ImportRow] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.errors == 0

    def summary(self) -> str:
        return (
            f"Total: {self.total}  •  "
            f"Nuevos: {self.created}  •  "
            f"Actualizados: {self.updated}  •  "
            f"Errores: {self.errors}"
        )


class ImportService:

    def __init__(self, session: Session) -> None:
        self.session       = session
        self.product_svc   = ProductService(session)
        self.stock_svc     = StockService(session)
        self.product_repo  = ProductRepository(session)

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def import_from_file(self, path: Path, mapping: dict[str, str] = None) -> ImportResult:
        """
        Lee el archivo Excel/CSV y procesa cada fila.
        Retorna un ImportResult con el detalle de cada fila.
        Puede recibir un diccionario `mapping` {"Columna Excel": "campo_canonico"}.
        """
        path = Path(path)
        rows = self._read_file(path, mapping)
        return self._process_rows(rows)

    # ── Lectura del archivo ───────────────────────────────────────────────────

    def _read_file(self, path: Path, mapping: dict[str, str] = None) -> list[dict[str, Any]]:
        """Usa pandas para leer el archivo. Retorna lista de dicts."""
        import pandas as pd

        ext = path.suffix.lower()
        if ext in (".xlsx", ".xls", ".xlsm"):
            df = pd.read_excel(path, dtype=str)
        elif ext == ".csv":
            # Intentar con UTF-8, si falla con latin-1
            try:
                df = pd.read_csv(path, dtype=str, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, dtype=str, encoding="latin-1")
        else:
            raise ValueError(f"Formato no soportado: {ext}. Use .xlsx, .xls o .csv")

        if mapping:
            # Usar mapeo manual provisto por la UI
            df = df.rename(columns=mapping)
        else:
            # Auto-mapping
            # Normalizar nombres de columna
            df.columns = [self._normalize_col(c) for c in df.columns]

            # Renombrar usando aliases
            rename_map = {}
            for col in df.columns:
                canonical = COLUMN_ALIASES.get(col)
                if canonical and canonical not in rename_map.values():
                    rename_map[col] = canonical

            df = df.rename(columns=rename_map)

        # Eliminar filas completamente vacias
        df = df.dropna(how="all")

        return df.to_dict(orient="records")

    @staticmethod
    def _normalize_col(name: str) -> str:
        """Minusculas + strip + colapsar espacios."""
        return str(name).strip().lower().replace("  ", " ")

    # ── Procesamiento fila por fila ───────────────────────────────────────────

    def _process_rows(self, rows: list[dict]) -> ImportResult:
        result = ImportResult(total=len(rows))

        for i, raw in enumerate(rows, start=2):  # start=2: fila 1 es encabezado
            row_result = self._process_single_row(i, raw)
            result.rows.append(row_result)

            if row_result.action == "created":
                result.created += 1
            elif row_result.action == "updated":
                result.updated += 1
            elif row_result.action == "skipped":
                result.skipped += 1
            elif row_result.action == "error":
                result.errors += 1

        return result

    def _process_single_row(self, row_num: int, raw: dict) -> ImportRow:
        # Extraer campos
        sku  = self._str(raw.get("sku"))
        name = self._str(raw.get("name"))

        if not sku:
            return ImportRow(row_num, sku or "?", name or "?",
                             action="error", error="SKU vacío")
        if not name:
            return ImportRow(row_num, sku, name or "?",
                             action="error", error="Nombre vacío")

        try:
            price    = self._decimal(raw.get("price"))
            stock    = self._decimal(raw.get("stock"))
            min_stk  = self._decimal(raw.get("min_stock"))
            desc     = self._str(raw.get("description"))
            unit     = self._str(raw.get("unit")) or "unidad"
            cat_name = self._str(raw.get("category"))
            barcode  = self._str(raw.get("barcode"))

            # Resolver categoria
            cat_id = self._get_or_create_category(cat_name) if cat_name else None

            # Buscar si ya existe por SKU
            existing = self.product_repo.get_by_sku(sku)

            if existing is None:
                # ── CREAR ─────────────────────────────────────────────────────
                barcodes = [barcode] if barcode else []
                prices   = {PRICE_LIST_ID: price} if price is not None else {}

                self.product_svc.create_product(
                    sku=sku,
                    name=name,
                    description=desc,
                    unit=unit,
                    category_id=cat_id,
                    barcodes=barcodes,
                    initial_stock=stock if stock is not None else Decimal("0"),
                    min_stock=min_stk if min_stk is not None else Decimal("0"),
                    prices=prices,
                )
                return ImportRow(row_num, sku, name, action="created")

            else:
                # ── ACTUALIZAR ────────────────────────────────────────────────
                self.product_svc.update_product(
                    product_id=existing.id,
                    name=name,
                    description=desc,
                    unit=unit,
                    category_id=cat_id,
                )
                if price is not None:
                    self.product_svc.set_price(existing.id, PRICE_LIST_ID, price)

                if stock is not None:
                    self.stock_svc.adjust_stock(
                        product_id=existing.id,
                        new_quantity=stock,
                        notes=f"Importación Excel — fila {row_num}",
                    )

                if min_stk is not None:
                    self.stock_svc.update_min_stock(existing.id, min_stk)

                if barcode:
                    if not self.product_repo.barcode_exists(barcode):
                        from app.models.barcode import Barcode
                        self.session.add(Barcode(code=barcode, product_id=existing.id))
                        self.session.commit()

                return ImportRow(row_num, sku, name, action="updated")

        except Exception as e:
            logger.warning(f"Error en fila {row_num} (SKU={sku}): {e}")
            return ImportRow(row_num, sku, name, action="error", error=str(e)[:120])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_create_category(self, name: str) -> int:
        """Retorna el id de la categoria, creandola si no existe."""
        cat = self.product_repo.get_category_by_name(name)
        if cat is None:
            cat = Category(name=name)
            self.session.add(cat)
            self.session.flush()   # para obtener cat.id sin commit
        return cat.id

    @staticmethod
    def _str(value: Any) -> str:
        """Convierte a string limpio, None si vacio."""
        if value is None:
            return ""
        s = str(value).strip()
        return s if s.lower() not in ("nan", "none", "") else ""

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        """Convierte a Decimal, None si no es numerico."""
        s = ImportService._str(value)
        if not s:
            return None
        # Normalizar separadores: quitar puntos de miles, cambiar coma a punto
        s = s.replace("$", "").replace(" ", "")
        # Si hay punto Y coma, asumir punto=miles y coma=decimal
        if "." in s and "," in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", ".")
        try:
            return Decimal(s)
        except InvalidOperation:
            return None
