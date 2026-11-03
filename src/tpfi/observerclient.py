"""Cliente ObserverClient que se suscribe y escucha notificaciones."""

import argparse
import json
import logging
import socket
import sys
import time
import uuid
from typing import Any


def main() -> None:
    """Conecta al servidor, envía suscripción y escucha cambios continuos."""
    parser = argparse.ArgumentParser(description="Cliente ObserverClient TPFI")
    parser.add_argument("-s", default="localhost", help="hostname")
    parser.add_argument("-p", type=int, default=8080, help="puerto")
    parser.add_argument("-o", help="archivo de salida JSON (opcional)")
    parser.add_argument("-v", action="store_true", help="modo para trace y debug")
    parser.add_argument(
        "-r",
        "--retry",
        type=int,
        default=30,
        help="Segundos entre reintentos de conexión",
    )
    parser.add_argument("-d", help="JSON de entrada directo")

    args = parser.parse_args()

    if args.v:
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stdout,
            format="%(asctime)s [%(levelname)s] %(message)s",
            force=True,
        )

    request: dict[str, Any] = {
        "UUID": str(uuid.getnode()),
        "ACTION": "subscribe",
    }

    if args.d:
        request = json.loads(args.d)

    try:
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    logging.debug("Intentando conectar a %s:%s...", args.s, args.p)
                    sock.connect((args.s, args.p))
                    print(f"Conectado a {args.s}:{args.p} — suscribiendo...")
                    sock.sendall(json.dumps(request).encode())

                    data = sock.recv(65536)
                    text = data.decode()
                    logging.debug("Respuesta de suscripción: %s", text)
                    if "subscribed" in text:
                        print("Suscrito — escuchando notificaciones...")
                    else:
                        print(f"Error al suscribirse: {text}")
                    if args.o:
                        with open(args.o, "a", encoding="utf-8") as file_out:
                            file_out.write(text + "\n")

                    while True:
                        data = sock.recv(65536)
                        if not data:
                            break
                        text = data.decode()
                        logging.debug("Notificación recibida: %s", text)
                        if args.o:
                            with open(args.o, "a", encoding="utf-8") as file_out:
                                file_out.write(text + "\n")
                        print(text)
            except (ConnectionAbortedError, OSError) as exc:
                logging.debug("Conexión interrumpida: %s", exc)
                print(f"Servidor caído, reintentando en {args.retry}s...")
                time.sleep(args.retry)
    except KeyboardInterrupt:
        logging.debug("ObserverClient finalizado manualmente.")


if __name__ == "__main__":
    main()
