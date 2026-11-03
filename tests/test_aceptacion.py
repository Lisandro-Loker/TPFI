"""Pruebas de aceptación según consigna: Validación y Verificación."""

import json
import socket
import subprocess
import sys
from unittest import mock

import boto3
import boto3.dynamodb.conditions

from src.tpfi.singletonproxyobserver import handle_client
from src.tpfi.soporte.database_singleton import CorporateDataDB, CorporateLogDB

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeConn:
    """Simula la conexión de un cliente para capturar la respuesta del servidor."""

    def __init__(self, request=b""):
        self.request = request
        self.sent = b""
        self.closed = False

    def recv(self, bufsize):
        return self.request

    def sendall(self, data):
        self.sent += data

    def close(self):
        self.closed = True


def ejecutar_accion(request, db_data=None, db_log=None, subject=None):
    conn = FakeConn(json.dumps(request).encode())
    print("db_log que llega a handle_client:", db_log)
    handle_client(
        conn,
        db_data=db_data or mock.Mock(),
        db_log=db_log or mock.Mock(),
        subject=subject or mock.Mock(),
    )
    try:
        return json.loads(conn.sent), conn
    except json.JSONDecodeError:
        return conn.sent, conn


def mis_logs(db_log, uuid, max_paginas=3):
    """
    Devuelve los logs de un uuid, filtrando el scan por uuid para
    minimizar el consumo de read units y evitar
    ProvisionedThroughputExceededException en tablas con capacidad
    provisionada baja.
    """
    logs = []
    kwargs = {
        "FilterExpression": boto3.dynamodb.conditions.Attr("uuid").eq(uuid),
        "ProjectionExpression": "#u, accion, id",
        "ExpressionAttributeNames": {"#u": "uuid"},
    }
    paginas = 0
    while True:
        response = db_log._table.scan(**kwargs)
        logs.extend(response.get("Items", []))
        paginas += 1
        if "LastEvaluatedKey" not in response or paginas >= max_paginas:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return logs


def correr_cliente(*args):
    """Corre el cliente como subproceso y devuelve el resultado."""
    return subprocess.run(
        [sys.executable, "-m", "src.tpfi.singletonclient", *args],
        capture_output=True,
        text=True,
    )


def correr_servidor(*args):
    """Corre el servidor como subproceso y devuelve el resultado."""
    return subprocess.run(
        [sys.executable, "-m", "src.tpfi.singletonproxyobserver", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# 1. Camino feliz de cada acción + registro en CorporateLog
# ---------------------------------------------------------------------------


def test_camino_feliz_list_registra_log():
    db_data = CorporateDataDB()
    db_log = CorporateLogDB()
    mi_uuid = "test-list-uuid-unico"

    respuesta, _ = ejecutar_accion(
        {"UUID": mi_uuid, "ACTION": "list"},
        db_data=db_data,
        db_log=db_log,
    )

    assert isinstance(respuesta, list)

    assert any(log.get("accion") == "list" for log in mis_logs(db_log, mi_uuid))


def test_camino_feliz_get_registra_log():
    db_data = CorporateDataDB()
    db_log = CorporateLogDB()
    mi_uuid = "test-get-uuid-unico"

    db_data.set({"id": "test-get", "CUIT": "20-12345678-9"})
    respuesta, _ = ejecutar_accion(
        {"UUID": mi_uuid, "ID": "test-get", "ACTION": "get"},
        db_data=db_data,
        db_log=db_log,
    )

    assert respuesta["id"] == "test-get"
    assert respuesta["CUIT"] == "20-12345678-9"

    assert any(
        log.get("accion") == "get" and log.get("id") == "test-get"
        for log in mis_logs(db_log, mi_uuid)
    )


def test_camino_feliz_set_registra_log():
    db_data = CorporateDataDB()
    db_log = CorporateLogDB()
    mi_uuid = "test-set-uuid-unico"

    respuesta, _ = ejecutar_accion(
        {
            "UUID": mi_uuid,
            "ACTION": "set",
            "data": {"id": "test-set", "CUIT": "20-12345678-9"},
        },
        db_data=db_data,
        db_log=db_log,
    )

    assert respuesta["id"] == "test-set"
    assert respuesta["CUIT"] == "20-12345678-9"

    item = db_data.get("test-set")
    assert item["id"] == "test-set"

    assert any(
        log.get("accion") == "set" and log.get("id") == "test-set"
        for log in mis_logs(db_log, mi_uuid)
    )


# ---------------------------------------------------------------------------
# 2. Argumentos malformados en cada programa
# ---------------------------------------------------------------------------


def test_cliente_argumentos_malformados():
    """El cliente debe fallar si falta -i (archivo de entrada requerido)."""
    resultado = correr_cliente()
    assert resultado.returncode != 0


def test_servidor_argumentos_malformados():
    """El servidor debe fallar si -p no es numérico."""
    resultado = correr_servidor("-p", "abc")
    assert resultado.returncode != 0


# ---------------------------------------------------------------------------
# 3. Requerimiento sin datos mínimos
# ---------------------------------------------------------------------------


def test_get_sin_id_devuelve_error():
    db_data = CorporateDataDB()
    db_log = CorporateLogDB()

    respuesta, _ = ejecutar_accion(
        {"UUID": "test-uuid", "ACTION": "get"},
        db_data=db_data,
        db_log=db_log,
    )
    assert respuesta == "Error"


def test_pedido_sin_action_devuelve_error():
    db_data = CorporateDataDB()
    db_log = CorporateLogDB()

    respuesta, _ = ejecutar_accion(
        {"UUID": "test-uuid"},
        db_data=db_data,
        db_log=db_log,
    )
    assert respuesta == "Error"


# ---------------------------------------------------------------------------
# 4. Manejo en cliente de servidor caído
# ---------------------------------------------------------------------------


def test_cliente_con_servidor_caido():
    """El cliente debe manejar ConnectionRefusedError sin crashear."""
    resultado = correr_cliente("-i", "input.json", "-p", "59999")
    assert "Traceback" not in resultado.stderr


# ---------------------------------------------------------------------------
# 5. Levantar el servidor dos veces
# ---------------------------------------------------------------------------


def test_servidor_dos_veces_mismo_puerto():
    """La segunda instancia debe fallar al intentar bindear el mismo puerto."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", 0))
    puerto = srv.getsockname()[1]

    try:
        resultado = correr_servidor("-p", str(puerto))
        assert resultado.returncode != 0 or "Address already in use" in resultado.stderr
    finally:
        srv.close()
