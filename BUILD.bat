@echo off
title COMPILAR EQUIPOS 6.5
color 0A
cd /d "%~dp0"

echo.
echo ========================================
echo   COMPILANDO EQUIPOS 6.5
echo ========================================
echo.

:: ── Detectar Python automáticamente ────────────────────────────────────────
:: Orden de preferencia: py launcher > python en PATH > rutas conocidas
set PYTHON=

:: 1. Intentar con py launcher (versiones en orden descendente)
for %%V in (3.14 3.13 3.12 3.11 3.10) do (
    if not defined PYTHON (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 (
            set PYTHON=py -%%V
            set PYVER=%%V
        )
    )
)

:: 2. Si no hay py launcher, intentar con "python" directo
if not defined PYTHON (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON=python
        for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYVER=%%V
    )
)

:: 3. Sin Python → salir
if not defined PYTHON (
    echo ERROR: No se encontro ninguna version de Python compatible.
    echo Instala Python 3.10 o superior desde python.org
    pause
    exit /b 1
)

echo Python detectado: %PYTHON%  [version %PYVER%]
echo.

:: ── Verificar PyInstaller ───────────────────────────────────────────────────
%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller no encontrado.
    echo Ejecuta:  %PYTHON% -m pip install pyinstaller
    pause
    exit /b 1
)

:: ── Verificar PyQt6 ─────────────────────────────────────────────────────────
%PYTHON% -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyQt6 no encontrado.
    echo Ejecuta:  %PYTHON% -m pip install PyQt6
    pause
    exit /b 1
)

echo PyInstaller y PyQt6 OK  (exe esperado: ~140-150 MB)
echo.

:: ── Pasos de compilacion ────────────────────────────────────────────────────
echo [1/4] Cerrando procesos anteriores...
taskkill /f /im alquiler_equipos.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo [2/4] Limpiando build anterior...
if exist "dist\alquiler_equipos.exe" del /f /q "dist\alquiler_equipos.exe" >nul 2>&1
if exist "build\alquiler_equipos"    rmdir /s /q "build\alquiler_equipos"  >nul 2>&1

echo [3/4] Preparando...
timeout /t 1 /nobreak >nul

echo [4/4] Compilando EXE (esto puede tardar varios minutos)...
echo.
%PYTHON% -m PyInstaller alquiler_equipos.spec

echo.
if exist "dist\alquiler_equipos.exe" (
    echo ========================================
    echo   BUILD EXITOSO
    echo   dist\alquiler_equipos.exe
    echo ========================================
    echo.
    for %%A in ("dist\alquiler_equipos.exe") do (
        echo Tamanio: %%~zA bytes
    )
    echo.
    set /p ABRIR="Abrir carpeta dist? (S/N): "
    if /i "%ABRIR%"=="S" explorer "%~dp0dist"
) else (
    echo ========================================
    echo   ERROR: Build fallido
    echo   Revisa los mensajes de arriba
    echo ========================================
)

echo.
pause
