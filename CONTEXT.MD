# CONTEXT — Registro de uso de IA

Documentación de los prompts utilizados con asistentes de IA durante el
desarrollo del TPFI, conforme al requisito de la cátedra.

## Herramientas utilizadas

- Asistentes de IA conversacionales (EcoGPT y Gemini) para diseño, depuración, pruebas y validación de calidad.

## Prompts y resultados

### 1. Diseño inicial del servidor proxy

**Prompt:** "Necesito implementar un servidor proxy en Python que use los
patrones Singleton, Observer y Proxy. El servidor recibe JSON por socket TCP
con UUID, ACTION y datos, y debe auditar cada operación en DynamoDB."

**Resultado:** estructura de módulos (`singletonproxyobserver`,
`singletonclient`, `observerclient`) y separación de responsabilidades entre
`handle_client`, `Subject` y las clases de acceso a datos.

### 2. Merge parcial en `set`

**Prompt:** "El `set` actual reemplaza el registro completo. La consigna pide
que los campos no informados conserven el valor anterior o queden en blanco si
el registro es nuevo. ¿Cómo lo implemento?"

**Resultado:** lectura previa del registro, copia de los campos presentes en
`CAMPOS_CORPORATE_DATA` y completado con `""` para los ausentes.

### 3. Nombre de la acción de suscripción

**Prompt:** "El ObserverClient envía `suscribe` pero el servidor espera
`suscribirse`, y la consigna dice `subscribe`. ¿Cuál uso?"

**Resultado:** aceptar las tres variantes en el servidor para mantener
compatibilidad.

### 4. Cierre de sockets colgados

**Prompt:** "Agregué `finally: conn.close()` para evitar sockets colgados, pero
eso cierra el socket del suscriptor. ¿Cómo lo resuelvo?"

**Resultado:** bandera `mantener_abierta`, que se activa solo en el caso
`subscribe`, conservando el cierre garantizado en las demás acciones.

### 5. `ProvisionedThroughputExceededException`

**Prompt:** "Los scans de `CorporateLog` fallan por throughput excedido. La
tabla tiene 7890 filas y no puedo borrar datos porque el profesor la revisa.
¿Qué opciones tengo?"

**Resultado:** `ProjectionExpression` con alias `#u` para el campo reservado
`uuid`, límite de páginas en `mis_logs` y reintentos adaptativos de boto3
(`Config(retries={"max_attempts": 20, "mode": "adaptive"})`).

### 6. Tests de patrones

**Prompt:** "La consigna pide que los tests verifiquen que las clases se
implementan como los patrones requeridos. ¿Cómo testeo Singleton, Observer y
Proxy?"

**Resultado:** `tests/test_patrones.py` con verificación de identidad de
instancias, notificación a múltiples suscriptores y delegación del proxy.

### 7. Configuración de calidad

**Prompt:** "Ruff marca I001, E701, E741 y falta de newline final. ¿Cómo los
resuelvo?"

**Resultado:** `ruff check . --fix` para los auto-corregibles, separación del
`else` en línea propia y renombrado de `l` a `log` en las comprensiones.

### 8. Compatibilidad del formato JSON en `set` y archivos de prueba manual

**Prompt:** "Al ejecutar `singletonclient.py` con `input.json` para la acción `set`, el archivo `output.json` devuelve `Error` y necesito contar con todos los archivos JSON para realizar las pruebas manuales de `get`, `set`, `list` y casos de error."

**Resultado:** actualización de `handle_client` en `singletonproxyobserver.py` para aceptar los campos de `CorporateData` tanto en la raíz del objeto JSON (según Tabla 1 de la consigna) como dentro de la clave `"data"`, validación de datos mínimos (`UUID`, `ACTION`, `ID`) y generación de `input.json`, `input_set.json`, `input_get.json`, `input_list.json` e `input_error.json`.

### 9. Mensajes de trace/debug (`-v`) y filtrado de librerías de AWS

**Prompt:** "Al activar `-v` en el servidor, la consola se llena con trazas internas de `boto3` y `botocore`, y falta agregar mensajes de debug por salida estándar en los clientes."

**Resultado:** configuración de `logging.basicConfig` hacia `sys.stdout` en `singletonproxyobserver.py`, `singletonclient.py` y `observerclient.py`, y ajuste del nivel de log a `WARNING` para `boto3`, `botocore` y `urllib3`.

### 10. Tipado estático, docstrings PEP257 y seguridad con Bandit

**Prompt:** "Necesito que todos los módulos dentro de `src/tpfi` pasen sin errores `ruff`, `black`, `mypy`, `pyright` y `bandit`, eliminando código plantilla sin uso."

**Resultado:** eliminación del archivo residual `src/tpfi/utils.py`, incorporación de anotaciones de tipos y docstrings PEP257 en todos los módulos y registro con `logging.debug` de excepciones de socket en `observer.py`.

### 11. Ampliación de cobertura de pruebas unitarias (> 85%)

**Prompt:** "`pytest --cov=src/tpfi` reporta 46.72% de cobertura total porque `singletonclient.py` y `observerclient.py` tienen 0%. ¿Cómo amplío los tests unitarios para superar el 85% requerido?"

**Resultado:** incorporación de pruebas unitarias con `unittest.mock` en `tests/test_cliente-servidor.py` para cubrir los flujos principales y casos de borde de los clientes y del servidor, alcanzando un **94.87%** de cobertura total en `pytest`.

## Nota

Todo el código generado con asistencia de IA fue revisado, adaptado y validado
con las herramientas de calidad del proyecto antes de su incorporación.
