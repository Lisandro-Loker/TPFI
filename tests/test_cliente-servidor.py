"""Pruebas unitarias del protocolo cliente-servidor y cobertura de módulos."""

import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest

from src.tpfi import observerclient, singletonclient, singletonproxyobserver
from src.tpfi.singletonproxyobserver import default_serializer, handle_client
from src.tpfi.soporte.database_singleton import CorporateDataDB, _convert
from src.tpfi.soporte.observer import _default_serializer


class FakeConn:
    """Simula la conexión del cliente para capturar lo que envía el servidor."""

    def __init__(self, request: bytes = b"") -> None:
        """Inicializa el socket simulado."""
        self.request = request
        self.sent = b""
        self.closed = False

    def recv(self, bufsize: int) -> bytes:
        """Devuelve los bytes de la petición simulada."""
        return self.request

    def sendall(self, data: bytes) -> None:
        """Acumula los bytes enviados por el servidor."""
        self.sent += data

    def close(self) -> None:
        """Marca la conexión como cerrada."""
        self.closed = True


def test_handle_client_responde_a_list() -> None:
    """Verifica que la acción list devuelva una respuesta válida."""
    conn = FakeConn(json.dumps({"UUID": "123", "ACTION": "list"}).encode())
    db_data = mock.Mock()
    db_data.list.return_value = [{"id": "1"}]
    handle_client(conn, db_data=db_data, db_log=mock.Mock(), subject=mock.Mock())
    assert json.loads(conn.sent) == [{"id": "1"}]


def test_handle_client_responde_error_si_pedido_invalido() -> None:
    """Verifica que ante un JSON inválido el servidor responda Error."""
    conn = FakeConn(b"no es json")
    handle_client(conn, db_data=mock.Mock(), db_log=mock.Mock(), subject=mock.Mock())
    assert json.loads(conn.sent) == "Error"


def test_handle_client_get_serializa_decimal() -> None:
    """Verifica que la acción get serialice correctamente tipos Decimal."""
    conn = FakeConn(json.dumps({"UUID": "123", "ID": "x", "ACTION": "get"}).encode())
    db_data = mock.Mock()
    db_data.get.return_value = {
        "id": "x",
        "idreq": Decimal("224"),
        "tasa": Decimal("12.5"),
    }
    handle_client(conn, db_data=db_data, db_log=mock.Mock(), subject=mock.Mock())
    respuesta = json.loads(conn.sent)
    assert respuesta["id"] == "x"
    assert respuesta["idreq"] == 224
    assert respuesta["tasa"] == 12.5


def test_serializers_y_convert_bordes() -> None:
    """Verifica la conversión de Decimal y errores de tipo en serializadores."""
    assert _convert([Decimal("10"), Decimal("2.5"), {"k": Decimal("3")}]) == [
        10,
        2.5,
        {"k": 3},
    ]
    assert _default_serializer(Decimal("4")) == 4
    assert _default_serializer(Decimal("4.5")) == 4.5
    with pytest.raises(TypeError):
        default_serializer(object())
    with pytest.raises(TypeError):
        _default_serializer(object())
    with pytest.raises(ValueError):
        CorporateDataDB().set({})


def test_handle_client_casos_borde() -> None:
    """Verifica desconexión vacía, subscribe, acción inválida y set sin ID."""
    empty_conn = FakeConn(b"")
    handle_client(empty_conn, mock.Mock(), mock.Mock(), mock.Mock())
    assert empty_conn.closed is True

    list_json_conn = FakeConn(b"[1, 2, 3]")
    handle_client(list_json_conn, mock.Mock(), mock.Mock(), mock.Mock())
    assert json.loads(list_json_conn.sent) == "Error"

    sub_conn = FakeConn(json.dumps({"UUID": "u1", "ACTION": "subscribe"}).encode())
    subject = mock.Mock()
    handle_client(sub_conn, mock.Mock(), mock.Mock(), subject)
    assert json.loads(sub_conn.sent) == {"status": "subscribed"}
    assert sub_conn.closed is False

    set_root_conn = FakeConn(
        json.dumps({"UUID": "u1", "ID": "id-1", "ACTION": "set", "cp": "3260"}).encode()
    )
    db_data = mock.Mock()
    db_data.set.return_value = {"id": "id-1", "cp": "3260"}
    handle_client(set_root_conn, db_data, mock.Mock(), mock.Mock())
    assert json.loads(set_root_conn.sent)["cp"] == "3260"

    set_no_id = FakeConn(json.dumps({"UUID": "u1", "ACTION": "set"}).encode())
    handle_client(set_no_id, mock.Mock(), mock.Mock(), mock.Mock())
    assert json.loads(set_no_id.sent) == "Error"

    unk_conn = FakeConn(json.dumps({"UUID": "u1", "ACTION": "otra"}).encode())
    handle_client(unk_conn, mock.Mock(), mock.Mock(), mock.Mock())
    assert json.loads(unk_conn.sent) == "Error"


def test_servidor_main_ciclo_y_error_puerto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica el arranque del servidor, atención de conexión y cierre."""
    fake_server_sock = mock.MagicMock()
    fake_conn = FakeConn(b"")
    fake_server_sock.__enter__.return_value = fake_server_sock
    fake_server_sock.accept.side_effect = [
        (fake_conn, ("127.0.0.1", 50000)),
        KeyboardInterrupt(),
    ]

    monkeypatch.setattr(sys, "argv", ["singletonproxyobserver", "-p", "8089", "-v"])
    monkeypatch.setattr(singletonproxyobserver, "CorporateDataDB", mock.Mock())
    monkeypatch.setattr(singletonproxyobserver, "CorporateLogDB", mock.Mock())
    with mock.patch("socket.socket", return_value=fake_server_sock):
        singletonproxyobserver.main()

    fake_err_sock = mock.MagicMock()
    fake_err_sock.__enter__.return_value = fake_err_sock
    fake_err_sock.bind.side_effect = OSError("Puerto ocupado")
    with (
        mock.patch("socket.socket", return_value=fake_err_sock),
        pytest.raises(SystemExit),
    ):
        singletonproxyobserver.main()


def test_singletonclient_main_modos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica singletonclient con archivo, con -d, salida -o y errores."""
    in_file = tmp_path / "in.json"
    out_file = tmp_path / "out.json"
    in_file.write_text(
        json.dumps({"UUID": "u1", "ID": "1", "ACTION": "get"}),
        encoding="utf-8",
    )

    fake_sock = mock.MagicMock()
    fake_sock.__enter__.return_value = fake_sock
    fake_sock.recv.return_value = b'{"id": "1"}'

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "singletonclient",
            "-i",
            str(in_file),
            "-o",
            str(out_file),
            "-v",
        ],
    )
    with mock.patch("socket.socket", return_value=fake_sock):
        singletonclient.main()
    assert json.loads(out_file.read_text(encoding="utf-8")) == {"id": "1"}

    monkeypatch.setattr(
        sys,
        "argv",
        ["singletonclient", "-d", '{"ACTION": "list"}'],
    )
    with mock.patch("socket.socket", return_value=fake_sock):
        singletonclient.main()

    monkeypatch.setattr(
        sys,
        "argv",
        ["singletonclient", "-i", str(tmp_path / "no_existe.json")],
    )
    with pytest.raises(SystemExit):
        singletonclient.main()

    fake_sock.connect.side_effect = ConnectionRefusedError("Caido")
    monkeypatch.setattr(
        sys, "argv", ["singletonclient", "-d", '{"ACTION": "list"}', "-v"]
    )
    with (
        mock.patch("socket.socket", return_value=fake_sock),
        pytest.raises(SystemExit),
    ):
        singletonclient.main()


def test_observerclient_main_ciclo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica suscripción, recepción de avisos y reconexión en observer."""
    out_obs = tmp_path / "obs.json"
    fake_sock = mock.MagicMock()
    fake_sock.__enter__.return_value = fake_sock
    fake_sock.recv.side_effect = [
        b'{"status": "subscribed"}',
        b'{"id": "UADER"}',
        b"",
    ]

    sock_err = mock.MagicMock()
    sock_err.__enter__.return_value = sock_err
    sock_err.connect.side_effect = OSError("Desconectado")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "observerclient",
            "-o",
            str(out_obs),
            "-r",
            "0",
            "-v",
            "-d",
            '{"UUID": "u1", "ACTION": "subscribe"}',
        ],
    )
    with (
        mock.patch("socket.socket", side_effect=[fake_sock, sock_err]),
        mock.patch("time.sleep", side_effect=KeyboardInterrupt()),
    ):
        observerclient.main()

    contenido = out_obs.read_text(encoding="utf-8")
    assert "subscribed" in contenido
    assert "UADER" in contenido


def test_database_singleton_mockeado() -> None:
    """Verifica get, set, list y log usando mocks sin requerir AWS."""
    db_data = CorporateDataDB()
    db_log = singletonproxyobserver.CorporateLogDB()
    with mock.patch.object(db_data, "_table") as mock_table:
        mock_table.get_item.return_value = {"Item": {"id": "1", "cp": "3260"}}
        assert db_data.get("1") == {"id": "1", "cp": "3260"}
        saved = db_data.set({"id": "1", "CUIT": "30-12345678-9"})
        assert saved["CUIT"] == "30-12345678-9"
        assert saved["cp"] == "3260"
        mock_table.scan.return_value = {"Items": [{"id": "1"}]}
        assert db_data.list() == [{"id": "1"}]

    with mock.patch.object(db_log, "_table") as mock_log_table:
        res = db_log.log("u1", "s1", "get", "1", "2026-11-03")
        assert res["accion"] == "get"
        mock_log_table.put_item.assert_called_once()
