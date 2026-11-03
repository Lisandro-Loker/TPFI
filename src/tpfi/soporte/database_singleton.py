"""Módulo Singleton para el acceso físico a CorporateData y CorporateLog."""

from decimal import Decimal
from typing import Any

import boto3
from botocore.config import Config


def _convert(item: Any) -> Any:
    """Convierte objetos Decimal de DynamoDB a int o float para JSON."""
    if isinstance(item, list):
        return [_convert(i) for i in item]
    if isinstance(item, dict):
        return {k: _convert(v) for k, v in item.items()}
    if isinstance(item, Decimal):
        return int(item) if item % 1 == 0 else float(item)
    return item


CAMPOS_CORPORATE_DATA: list[str] = [
    "id",
    "cp",
    "CUIT",
    "domicilio",
    "idreq",
    "idSeq",
    "localidad",
    "provincia",
    "sede",
    "seqID",
    "telefono",
    "web",
]

_CLIENTE_DYNAMODB: Any = boto3.resource(
    "dynamodb",
    config=Config(retries={"max_attempts": 20, "mode": "adaptive"}),
)


class CorporateDataDB:
    """Implementa el patrón Singleton para el acceso a CorporateData."""

    _instance: "CorporateDataDB | None" = None
    _table: Any

    def __new__(cls) -> "CorporateDataDB":
        """Garantiza una única instancia de conexión a CorporateData."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._table = _CLIENTE_DYNAMODB.Table("CorporateData")
        return cls._instance

    def get(self, record_id: str) -> dict[str, Any] | None:
        """Recupera un registro de CorporateData según su identificador."""
        response = self._table.get_item(Key={"id": record_id})
        item = response.get("Item")
        return _convert(item) if item is not None else None

    def set(self, item: dict[str, Any]) -> dict[str, Any]:
        """Inserta o actualiza parcialmente un registro en CorporateData."""
        record_id = item.get("id")
        if not record_id:
            raise ValueError("El registro debe incluir 'id'")

        existente = self.get(str(record_id)) or {}

        registro: dict[str, Any] = {}
        for campo in CAMPOS_CORPORATE_DATA:
            if campo in item:
                registro[campo] = item[campo]
            elif campo in existente:
                registro[campo] = existente[campo]
            else:
                registro[campo] = ""

        self._table.put_item(Item=registro)
        return _convert(registro)

    def list(self) -> list[dict[str, Any]]:
        """Retorna una lista con todos los registros de CorporateData."""
        items = self._table.scan().get("Items", [])
        return _convert(items)


class CorporateLogDB:
    """Implementa el patrón Singleton para el acceso a CorporateLog."""

    _instance: "CorporateLogDB | None" = None
    _table: Any

    def __new__(cls) -> "CorporateLogDB":
        """Garantiza una única instancia de conexión a CorporateLog."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._table = _CLIENTE_DYNAMODB.Table("CorporateLog")
        return cls._instance

    def log(
        self,
        client_uuid: Any,
        sesion: Any,
        accion: str,
        record_id: Any,
        timestamp: Any,
    ) -> dict[str, str]:
        """Registra una entrada de auditoría en la tabla CorporateLog."""
        item = {
            "uuid": str(client_uuid),
            "sesion": str(sesion),
            "accion": str(accion),
            "id": str(record_id),
            "timestamp": str(timestamp),
        }
        self._table.put_item(Item=item)
        return item
