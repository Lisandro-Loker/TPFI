@echo off
echo ============================================================
echo [1/6] Ejecutando Ruff (Linter y reglas de formato)...
echo ============================================================
call ruff check src/ tests/

echo.
echo ============================================================
echo [2/6] Ejecutando Black (Validacion de formato consistente)...
echo ============================================================
call black --check src/ tests/

echo.
echo ============================================================
echo [3/6] Ejecutando MyPy (Verificacion de tipado estatico)...
echo ============================================================
call mypy src/

echo.
echo ============================================================
echo [4/6] Ejecutando PyRight (Verificacion de tipos)...
echo ============================================================
call pyright src/

echo.
echo ============================================================
echo [5/6] Ejecutando Bandit (Evaluacion basica de seguridad)...
echo ============================================================
call bandit -r src/

echo.
echo ============================================================
echo [6/6] Ejecutando Pytest (Pruebas y cobertura de codigo)...
echo ============================================================
call pytest --cov=src/tpfi --cov-report=term-missing