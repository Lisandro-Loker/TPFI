"""Servidor de aplicaciones Proxy, Singleton y Observer para el TPFI."""

import argparse
import json
import logging
import socket
import sys
import threading
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from .soporte.database_singleton import (
    CAMPOS_CORPORATE_DATA,
    CorporateDataDB,
    CorporateLogDB,
)
from .soporte.observer import Subject


def default_serializer(obj: Any) -> int | float:
    """Convierte tipos Decimal de DynamoDB a int o float para JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)}")


def handle_client(
    conn: Any,
    db_data: Any,
    db_log: Any,
    subject: Any,
) -> None:
    """Atiende un requerimiento JSON de un cliente con el patrón Proxy."""
    mantener_abierta = False
    try:
        data = conn.recv(65536)
        if not data:
            return
        request = json.loads(data.decode())
        if not isinstance(request, dict):
            raise ValueError("El requerimiento JSON debe ser un objeto")

        action = request.get("ACTION")
        client_uuid = request.get("UUID")
        if not client_uuid or not action:
            raise ValueError("Faltan datos mínimos requeridos (UUID, ACTION)")

        sesion = uuid.uuid4()
        ts = datetime.now().isoformat()
        logging.debug(
            "Petición recibida: ACTION=%s, UUID=%s, SESION=%s",
            action,
            client_uuid,
            sesion,
        )

        if action == "get":
            record_id = request.get("ID") or request.get("id")
            if not record_id:
                raise ValueError("La acción 'get' requiere 'ID'")
            db_log.log(client_uuid, sesion, "get", record_id, ts)
            item = db_data.get(str(record_id))
            respuesta = item if item is not None else "Error"
            payload = json.dumps(respuesta, default=default_serializer)
            conn.sendall(payload.encode())

        elif action == "list":
            db_log.log(client_uuid, sesion, "list", "-", ts)
            items = db_data.list()
            payload = json.dumps(items, default=default_serializer)
            conn.sendall(payload.encode())

        elif action == "set":
            raw_data = request.get("data")
            item_data: dict[str, Any] = (
                dict(raw_data) if isinstance(raw_data, dict) else {}
            )
            for campo in CAMPOS_CORPORATE_DATA:
                if campo in request and campo not in item_data:
                    item_data[campo] = request[campo]

            record_id = item_data.get("id") or request.get("ID") or request.get("id")
            if not record_id:
                raise ValueError("La acción 'set' requiere 'ID' o 'id'")

            item_data["id"] = str(record_id)
            db_log.log(client_uuid, sesion, "set", item_data["id"], ts)
            saved = db_data.set(item_data)
            payload = json.dumps(saved, default=default_serializer)
            conn.sendall(payload.encode())
            subject.notify(saved)

        elif action in ("subscribe", "suscribirse", "suscribe"):
            db_log.log(client_uuid, sesion, "subscribe", "-", ts)
            subject.subscribe(str(client_uuid), conn)
            mantener_abierta = True
            payload = json.dumps({"status": "subscribed"}, default=default_serializer)
            conn.sendall(payload.encode())

        else:
            payload = json.dumps("Error", default=default_serializer)
            conn.sendall(payload.encode())

    except Exception as exc:
        logging.debug("Error procesando cliente: %s", exc)
        try:
            payload = json.dumps("Error", default=default_serializer)
            conn.sendall(payload.encode())
        except Exception as send_exc:
            logging.debug("No se pudo enviar mensaje de error: %s", send_exc)
    finally:
        if not mantener_abierta:
            conn.close()


def main() -> None:
    """Inicia el servidor TCP y escucha conexiones entrantes."""
    parser = argparse.ArgumentParser(description="Servidor SingletonProxyObserver TPFI")
    parser.add_argument("-p", type=int, default=8080, help="puerto TCP")
    parser.add_argument("-v", action="store_true", help="modo para trace y debug")
    args = parser.parse_args()

    if args.v:
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stdout,
            format="%(asctime)s [%(levelname)s] %(message)s",
            force=True,
        )
        for noisy in ("boto3", "botocore", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    db_data = CorporateDataDB()
    db_log = CorporateLogDB()
    subject = Subject()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(("", args.p))
            server.listen(5)
            logging.debug("Servidor escuchando en el puerto: %s", args.p)

            while True:
                conn, addr = server.accept()
                logging.debug("Conexión aceptada desde: %s", addr)
                threading.Thread(
                    target=handle_client,
                    args=(conn, db_data, db_log, subject),
                    daemon=True,
                ).start()
    except OSError as exc:
        print(
            f"Error al iniciar el servidor en el puerto {args.p}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        logging.debug("Servidor detenido manualmente.")


if __name__ == "__main__":
    main()
