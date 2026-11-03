"""Módulo Observer para gestionar clientes suscriptos a cambios."""

import json
import logging
from decimal import Decimal
from typing import Any


def _default_serializer(obj: Any) -> int | float:
    """Serializa objetos Decimal al convertir notificaciones a JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)}")


class Subject:
    """Sujeto observado que administra los sockets TCP suscriptos."""

    def __init__(self) -> None:
        """Inicializa el diccionario de observadores suscriptos."""
        self._observers: dict[str, Any] = {}

    def subscribe(self, client_uuid: str, client_socket: Any) -> None:
        """Registra o actualiza el socket asociado al UUID de un cliente."""
        self._observers[str(client_uuid)] = client_socket
        logging.debug("Suscriptor registrado con UUID: %s", client_uuid)

    def notify(self, data: Any) -> None:
        """Envía los datos actualizados en formato JSON a los suscriptos."""
        payload = json.dumps(data, default=_default_serializer).encode()
        for client_uuid, sock in list(self._observers.items()):
            try:
                sock.sendall(payload)
            except Exception as exc:
                logging.debug(
                    "No se pudo notificar al suscriptor %s: %s",
                    client_uuid,
                    exc,
                )
