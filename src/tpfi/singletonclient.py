"""Cliente SingletonClient para consultar, listar y modificar CorporateData."""

import argparse
import json
import logging
import socket
import sys
import uuid
from typing import Any


def main() -> None:
    """Ejecuta el cliente SingletonClient enviando un JSON al servidor."""
    parser = argparse.ArgumentParser(description="Cliente SingletonClient TPFI")
    parser.add_argument("-i", required=False, help="archivo de entrada JSON")
    parser.add_argument("-o", help="archivo de salida JSON (opcional)")
    parser.add_argument("-s", default="localhost", help="host del servidor")
    parser.add_argument("-p", type=int, default=8080, help="puerto del servidor")
    parser.add_argument("-v", action="store_true", help="modo para trace y debug")
    parser.add_argument("-d", help="JSON de entrada directo (alternativa a -i)")

    args = parser.parse_args()

    if args.d is None and args.i is None:
        parser.error("Se requiere -i o -d")

    if args.v:
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stdout,
            format="%(asctime)s [%(levelname)s] %(message)s",
            force=True,
        )

    try:
        if args.d:
            request: dict[str, Any] = json.loads(args.d)
        else:
            with open(args.i, encoding="utf-8") as file_in:
                request = json.load(file_in)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error leyendo JSON de entrada: {exc}", file=sys.stderr)
        sys.exit(1)

    request.setdefault("UUID", str(uuid.getnode()))
    logging.debug("Enviando requerimiento a %s:%s -> %s", args.s, args.p, request)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((args.s, args.p))
            sock.sendall(json.dumps(request).encode())
            data = sock.recv(65536)
    except (ConnectionRefusedError, OSError) as exc:
        logging.debug("Fallo de conexión con el servidor: %s", exc)
        print("Servidor no disponible")
        sys.exit(1)

    response = data.decode()
    logging.debug("Respuesta recibida del servidor (%d bytes)", len(response))

    if args.o:
        with open(args.o, "w", encoding="utf-8") as file_out:
            file_out.write(response)
        logging.debug("Respuesta guardada en el archivo: %s", args.o)

    formatted = json.dumps(json.loads(response), indent=2, ensure_ascii=False)
    print(formatted)


if __name__ == "__main__":
    main()
