# app/core/exceptions.py


class DevMontBaseError(Exception):
    """Clase base para todas las excepciones de dominio de DevMont Commerce."""


class StockInsuficienteError(DevMontBaseError):
    """Stock disponible menor al requerido en una venta."""

    def __init__(self, product_id: int, disponible: int, requerido: int):
        self.product_id = product_id
        self.disponible = disponible
        self.requerido = requerido
        super().__init__(
            f"Stock insuficiente para producto {product_id}: "
            f"disponible={disponible}, requerido={requerido}"
        )


class ProductoNoEncontradoError(DevMontBaseError):
    """Producto inexistente en la base de datos."""

    def __init__(self, identifier: str | int):
        self.identifier = identifier
        super().__init__(f"Producto no encontrado: {identifier}")


class UsuarioNoEncontradoError(DevMontBaseError):
    """Usuario inexistente o credenciales invalidas."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Usuario no encontrado: {username}")


class CredencialesInvalidasError(DevMontBaseError):
    """Contrasena incorrecta."""


class ProveedorNoEncontradoError(DevMontBaseError):
    def __init__(self, identifier: str | int):
        super().__init__(f"Proveedor no encontrado: {identifier}")


class ClienteNoEncontradoError(DevMontBaseError):
    def __init__(self, identifier: str | int):
        super().__init__(f"Cliente no encontrado: {identifier}")


class VentaNoEncontradaError(DevMontBaseError):
    def __init__(self, sale_id: int):
        super().__init__(f"Venta no encontrada: {sale_id}")


class OperacionInvalidaError(DevMontBaseError):
    """Operacion que viola reglas de negocio (ej: cancelar venta ya facturada)."""
