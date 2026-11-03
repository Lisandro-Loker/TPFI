"""Pruebas que verifican la implementación de los patrones requeridos."""

import json
from unittest import mock

from src.tpfi.singletonproxyobserver import handle_client
from src.tpfi.soporte.database_singleton import CorporateDataDB, CorporateLogDB
from src.tpfi.soporte.observer import Subject


class FakeConn:
    """Simula la conexión de un cliente para capturar lo enviado."""

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


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_corporate_data_db_es_singleton():
    """Dos instanciaciones devuelven el mismo objeto."""
    assert CorporateDataDB() is CorporateDataDB()


def test_corporate_log_db_es_singleton():
    """Dos instanciaciones devuelven el mismo objeto."""
    assert CorporateLogDB() is CorporateLogDB()


def test_singleton_comparte_estado():
    """El estado escrito en una referencia se ve desde otra."""
    db1 = CorporateDataDB()
    db2 = CorporateDataDB()
    db1.set({"id": "test-singleton-estado", "CUIT": "20-12345678-9"})
    assert db2.get("test-singleton-estado")["id"] == "test-singleton-estado"


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------


def test_observer_registra_suscriptos():
    """El subject guarda un socket por cada UUID suscripto."""
    subject = Subject()
    subject.subscribe("uuid-1", FakeConn())
    subject.subscribe("uuid-2", FakeConn())
    assert len(subject._observers) == 2


def test_observer_notifica_a_todos():
    """notify envía el mismo dato a todos los suscriptos."""
    subject = Subject()
    c1, c2 = FakeConn(), FakeConn()
    subject.subscribe("uuid-1", c1)
    subject.subscribe("uuid-2", c2)

    subject.notify({"id": "test-notify", "CUIT": "20-12345678-9"})

    assert json.loads(c1.sent)["id"] == "test-notify"
    assert json.loads(c2.sent)["id"] == "test-notify"


def test_observer_suscriptor_desconectado_no_rompe_notify():
    """Si un suscriptor falla, los demás igual reciben la notificación."""
    subject = Subject()
    roto = mock.Mock()
    roto.sendall.side_effect = OSError("socket cerrado")
    bueno = FakeConn()
    subject.subscribe("uuid-roto", roto)
    subject.subscribe("uuid-bueno", bueno)

    subject.notify({"id": "test-notify-2"})

    assert json.loads(bueno.sent)["id"] == "test-notify-2"


# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------


def test_proxy_intermedia_get():
    """El proxy delega el get en CorporateData y responde al cliente."""
    db_data = mock.Mock()
    db_data.get.return_value = {"id": "test-proxy", "CUIT": "20-12345678-9"}
    conn = FakeConn(
        json.dumps({"UUID": "u", "ID": "test-proxy", "ACTION": "get"}).encode()
    )

    handle_client(conn, db_data=db_data, db_log=mock.Mock(), subject=mock.Mock())

    db_data.get.assert_called_once_with("test-proxy")
    assert json.loads(conn.sent)["id"] == "test-proxy"


def test_proxy_retransmite_set_a_suscriptos():
    """Un set notifica al solicitante y al subject."""
    db_data = mock.Mock()
    db_data.get.return_value = None
    db_data.set.return_value = {"id": "test-proxy-set", "CUIT": "20-12345678-9"}
    subject = mock.Mock()
    conn = FakeConn(
        json.dumps(
            {
                "UUID": "u",
                "ACTION": "set",
                "data": {"id": "test-proxy-set", "CUIT": "20-12345678-9"},
            }
        ).encode()
    )

    handle_client(conn, db_data=db_data, db_log=mock.Mock(), subject=subject)

    db_data.set.assert_called_once()
    subject.notify.assert_called_once()
    assert json.loads(conn.sent)["id"] == "test-proxy-set"


def test_proxy_registra_auditoria_en_cada_accion():
    """Toda acción genera un registro en CorporateLog."""
    db_data = mock.Mock()
    db_data.get.return_value = {"id": "test-audit"}
    db_log = mock.Mock()

    conn = FakeConn(
        json.dumps({"UUID": "u", "ID": "test-audit", "ACTION": "get"}).encode()
    )
    handle_client(conn, db_data=db_data, db_log=db_log, subject=mock.Mock())

    db_log.log.assert_called_once()
