# app/repository/base_repository.py
from typing import Generic, TypeVar, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repositorio generico con operaciones CRUD comunes.
    Todos los repositorios concretos heredan de este.

    Uso:
        class ProductRepository(BaseRepository[Product]):
            def __init__(self, session: Session):
                super().__init__(session, Product)
    """

    def __init__(self, session: Session, model: Type[ModelType]):
        self.session = session
        self.model = model

    def get_by_id(self, id: int) -> ModelType | None:
        """Retorna el registro por PK o None si no existe."""
        return self.session.get(self.model, id)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[ModelType]:
        """Retorna todos los registros con paginacion simple."""
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())

    def create(self, obj: ModelType) -> ModelType:
        """Persiste un nuevo objeto. No hace commit (responsabilidad del service)."""
        self.session.add(obj)
        self.session.flush()  # Genera el ID sin commitear
        return obj

    def update(self, obj: ModelType) -> ModelType:
        """Marca el objeto como modificado y lo sincroniza con la sesion."""
        self.session.flush()
        return obj

    def delete(self, obj: ModelType) -> None:
        """Elimina el objeto de la base de datos."""
        self.session.delete(obj)
        self.session.flush()

    def count(self) -> int:
        """Retorna el total de registros de la tabla."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0
