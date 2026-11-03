# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el versionado [SemVer](https://semver.org/lang/es/).

## Contributors / Autores
- **Augusto M.Sol** ([@PandaAColor](https://github.com/PandaAColor)) — Desarrollo de la arquitectura base, implementación de patrones y suite inicial de pruebas.
- **Lisandro Nahuel Loker Gonzalez** ([@Lisandro-Loker](https://github.com/Lisandro-Loker)) — Corrección de soporte JSON, trazas de depuración, tipado estático, ampliación de cobertura de tests unitarios y configuración CI/CD.

## [1.0.0] - Build 2 - 2026-11-03

### Added
- Archivos JSON de entrada para pruebas manuales de cada operación (`input.json`, `input_set.json`, `input_get.json`, `input_list.json` e `input_error.json`).
- Soporte dual en la acción `set` del servidor para recibir atributos de `CorporateData` tanto en el nivel raíz del JSON (Tabla 1 de la consigna) como anidados en `"data"`.
- Trazas de depuración (`logging`) por salida estándar (`stdout`) al utilizar el argumento `-v` en los tres programas, silenciando el tráfico interno de `boto3`, `botocore` y `urllib3`.
- Nuevas pruebas unitarias en `tests/test_cliente-servidor.py` para `singletonclient`, `observerclient` y `singletonproxyobserver`, elevando la cobertura total de `pytest` al **94.87%**.
- Anotaciones de tipo (`type hints`) y docstrings bajo convención PEP257 en todos los módulos de `src/tpfi/`.

### Changed
- El método `CorporateDataDB.set()` retorna el registro completo fusionado tras impactar en DynamoDB.
- El `set` realiza merge parcial: los campos no informados conservan el valor previo o quedan en blanco si el registro es nuevo.
- El `subscribe` acepta las variantes `subscribe`, `suscribe` y `suscribirse`.
- `mis_logs` limita la cantidad de páginas del scan para reducir carga sobre `CorporateLog`.

### Fixed
- Eliminación del módulo residual de plantilla `src/tpfi/utils.py`.
- Validación estricta de presencia de `UUID`, `ACTION` e `ID` en `handle_client` antes de operar sobre DynamoDB.
- Registro mediante `logging.debug` ante desconexiones en `Subject.notify()` para cumplir las reglas de seguridad de `bandit`.
- El `finally: conn.close()` no cierra el socket de los suscriptores (bandera `mantener_abierta`).
- Alias `#u` en `ExpressionAttributeNames` para el campo reservado `uuid`.
- Formateo consistente validado sin errores con `ruff`, `black`, `mypy`, `pyright` y `bandit`.

## [1.0.0] - Build 1 - 2026-10-21

### Added
- Implementación inicial del servidor proxy con los patrones Singleton, Observer y Proxy por Augusto M.Sol (@PandaAColor).
- `singletonclient` con soporte de `get`, `set` y `list`.
- `observerclient` con reconexión automática cada 30 segundos (`--retry`).
- Auditoría de operaciones en la tabla `CorporateLog` y persistencia en `CorporateData`.
- Tests de aceptación (`tests/test_aceptacion.py`) y de patrones (`tests/test_patrones.py`).
- Estructura de proyecto generada con Cookiecutter, licencia MIT y documentación con `pdoc`.
