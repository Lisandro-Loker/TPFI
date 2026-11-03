# TPFI — Singleton Proxy Observer

Trabajo Práctico Final Integrador de **Ingeniería de Software II**
(UADER — Facultad de Ciencia y Tecnología).

Implementación en Python de tres patrones de diseño —**Singleton**, **Proxy**
y **Observer**— sobre comunicación por sockets TCP, con persistencia en
AWS DynamoDB.

## Descripción

El sistema está compuesto por tres programas:

|   Programa               | Rol                                             |  Patrón  |
|   ---                    |---                                              |   ---    |
| `singletonproxyobserver` | Servidor proxy que atiende a los clientes       | Proxy    |
| `singletonclient`        | Cliente que consulta y modifica datos           |Singleton |
| `observerclient`         | Cliente que se suscribe y recibe notificaciones | Observer |

El servidor expone dos tablas de DynamoDB a través de un singleton:

- **`CorporateData`** — datos corporativos (`id`, `CUIT`, `razon_social`, etc.).
- **`CorporateLog`** — auditoría de cada operación (`uuid`, `sesion`, `accion`, `id`, `timestamp`).

## Acciones soportadas

| Acción | Requiere `ID` | Descripción |
|---|---|---|
| `get` | Sí | Devuelve el registro con ese `id`, o `Error` |
| `set` | No (va en `data`) | Crea o actualiza el registro y notifica a los suscriptos |
| `list` | No | Devuelve un array con todos los registros |
| `subscribe` | No | Registra el socket como suscriptor de cambios |

El `set` hace **merge parcial**: los campos no informados conservan su valor anterior, o quedan en blanco si el registro es nuevo.

## Estructura del proyecto

```text
TPFI/
├── src/tpfi/
│   ├── singletonproxyobserver.py   # servidor proxy
│   ├── singletonclient.py          # cliente get/set/list
│   ├── observerclient.py           # cliente suscriptor
│   └── soporte/
│       ├── database_singleton.py   # Singleton de acceso a DynamoDB
│       └── observer.py             # Subject / Observer
├── tests/
│   ├── test_aceptacion.py
│   └── test_patrones.py
├── docs/
├── CONTEXT.md
├── CHANGELOG.md
├── REQUIREMENTS.TXT
├── VERSION
├── BUILD
├── LICENSE
└── pyproject.toml
```

## Requisitos

- Python 3.12+
- Entorno virtual (`venv`)
- Credenciales de AWS con acceso a DynamoDB (región y nombres de tabla configurables)

## Instalación

```bash
python -m venv entorno_virtual
entorno_virtual\Scripts\activate
pip install -r REQUIREMENTS.TXT
```

## Uso

Todos los comandos se ejecutan desde la raíz del proyecto, con el entorno virtual activado.
El orden de arranque es: primero el servidor, después el cliente y/o el observer.

### Qué comando usar según lo que quieras hacer

# Levantar el servidor en el puerto 8080
python -m src.tpfi.singletonproxyobserver -p=8080 -v

# Consultar un registro por id
python -m src.tpfi.singletonclient -i input.json -o output.json -v

# Crear o actualizar un registro
python -m src.tpfi.singletonclient -i input.json -o output.json -v

# Listar todos los registros
python -m src.tpfi.singletonclient -i input.json -o output.json -v

# Suscribirse y recibir notificaciones
python -m src.tpfi.observerclient -s=localhost -p=8080 -o output_observer.json -v

Nota: el cliente (singletonclient) es el mismo comando para get, set y list.
Lo que cambia es el contenido del archivo de entrada (input.json) o el JSON directo (-d),
donde se indica la ACTION:

# Consultar un registro por id (desde archivo)
python -m src.tpfi.singletonclient -i input.json -o output.json -v

# Consultar un registro por id (con -d)
python -m src.tpfi.singletonclient -d '{\"UUID\":\"123456789\",\"ID\":\"1\",\"ACTION\":\"get\"}' -o output.json -v

# Crear o actualizar un registro (desde archivo)
python -m src.tpfi.singletonclient -i input.json -o output.json -v

# Crear o actualizar un registro (con -d)
python -m src.tpfi.singletonclient -d '{\"UUID\":\"123456789\",\"ID\":\"1\",\"ACTION\":\"set\",\"data\":{\"CUIT\":\"30-12345678-9\"}}' -o output.json -v

# Listar todos los registros (desde archivo)
python -m src.tpfi.singletonclient -i input.json -o output.json -v

# Listar todos los registros (con -d)
python -m src.tpfi.singletonclient -d '{\"UUID\":\"123456789\",\"ACTION\":\"list\"}' -o output.json -v



## Formato de los archivos JSON

### Entrada del cliente

```json
{
  "UUID": "123456789",
  "ID": "1",
  "ACTION": "get"
}
```

### Entrada del observer

```json
{
  "UUID": "123456789",
  "ACTION": "subscribe"
}
```

## Tests
Demostración Manual en Vivo con 3 Terminales CMD:
Terminal 1 (Sevidor): Levantá el servidor con trazas activadas
Bash
python -m src.tpfi.singletonproxyobserver -p 8080 -v

Terminal 2 (ObserverClient): Suscribí al cliente observador para que quede escuchando cambios en tiempo real
Bash
python -m src.tpfi.observerclient -s localhost -p 8080 -o output_observer.json -v

Terminal 3 (SingletonClient con tus archivos JSON): Ejecutá una por una las 4 pruebas
Bash
python -m src.tpfi.singletonclient -i input_set.json -o output.json -v
python -m src.tpfi.singletonclient -i input_get.json -v
python -m src.tpfi.singletonclient -i input_list.json -v
python -m src.tpfi.singletonclient -i input_error.json -v


```bash
pytest -v
pytest --cov=src --cov-report=term-missing
```

## Calidad de código

```bash
ruff check .
black --check .
mypy src/
pyright src/
bandit -r src/
```

## Documentación

```bash
pdoc src/tpfi -o docs/
```

## Versión y build

La versión vigente está en `VERSION` y el número de build en `BUILD`. El historial de cambios se mantiene en [CHANGELOG.md](CHANGELOG.md) y el registro de prompts de IA en [CONTEXT.md](CONTEXT.md).

## Licencia

MIT — ver [LICENSE](LICENSE).
