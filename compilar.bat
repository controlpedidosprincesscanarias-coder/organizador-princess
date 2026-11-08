@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Compilador Organizador Princess

echo.
echo  ============================================================
echo   Organizador Princess - Compilacion con PyInstaller
echo   Central Compras Princess Canarias - VAMA 2026
echo  ============================================================
echo.

set "RED_DIR=%~dp0"
set "LOCAL_DIR=C:\build_temp\OrganizadorPrincess"

echo  [1/5] Cerrando OrganizadorPrincess.exe si esta abierto...
taskkill /F /IM OrganizadorPrincess.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo        Proceso cerrado correctamente.
    timeout /t 3 /nobreak >nul
) else (
    echo        No habia ninguna instancia abierta.
)
echo.

python -m pip install requests "python-socketio[client]" websocket-client cryptography

echo  [2/5] Copiando proyecto a carpeta local para compilar...
echo        Origen : %RED_DIR%
echo        Destino: %LOCAL_DIR%
if exist "%LOCAL_DIR%" rmdir /s /q "%LOCAL_DIR%"
xcopy "%RED_DIR%." "%LOCAL_DIR%" /E /I /Q >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: No se pudo copiar el proyecto a %LOCAL_DIR%
    echo  Comprueba que tienes permisos de escritura en C:\
    echo.
    pause
    exit /b 1
)
echo        Copia completada.
echo.

echo  [3/5] Limpiando compilaciones y cache anteriores...
if exist "%LOCAL_DIR%\build" rmdir /s /q "%LOCAL_DIR%\build"
if exist "%LOCAL_DIR%\dist"  rmdir /s /q "%LOCAL_DIR%\dist"
for /d /r "%LOCAL_DIR%" %%C in (__pycache__) do (
    if exist "%%C" rmdir /s /q "%%C"
)
if exist "%LOCALAPPDATA%\pyinstaller" (
    echo        Limpiando tambien la cache global de PyInstaller...
    rmdir /s /q "%LOCALAPPDATA%\pyinstaller"
)
echo        Listo.
echo.

echo  [3b/5] Verificando dependencias del chat en este Python...
python -c "import requests, socketio, engineio, websocket, cryptography; print('        requests OK'); print('        python-socketio OK'); print('        python-engineio OK'); print('        websocket-client OK'); print('        cryptography OK')"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Faltan dependencias del chat en ESTE Python ^(el mismo que
    echo  usara PyInstaller, que es el que resuelve el comando "python" aqui^).
    echo  Ejecuta antes de compilar:
    echo      python -m pip install requests "python-socketio[client]" websocket-client cryptography
    echo.
    pause
    exit /b 1
)
echo.

echo  [4/5] Iniciando compilacion con PyInstaller ^(en local^)...
echo        Este proceso puede tardar varios minutos.
echo.
cd /d "%LOCAL_DIR%"
python -m PyInstaller main.spec
echo.

timeout /t 4 /nobreak >nul

echo  [5/5] Comprobando resultado y copiando a carpeta de red...
if exist "%LOCAL_DIR%\dist\OrganizadorPrincess.exe" (
    for %%A in ("%LOCAL_DIR%\dist\OrganizadorPrincess.exe") do set EXE_SIZE=%%~zA
    if not exist "%RED_DIR%dist" mkdir "%RED_DIR%dist"
    copy /Y "%LOCAL_DIR%\dist\OrganizadorPrincess.exe" "%RED_DIR%dist\OrganizadorPrincess.exe" >nul
    if exist "%RED_DIR%dist\OrganizadorPrincess.exe" (
        echo  ============================================================
        echo   COMPILACION EXITOSA
        echo   Ejecutable local : %LOCAL_DIR%\dist\OrganizadorPrincess.exe
        echo   Ejecutable en red: %RED_DIR%dist\OrganizadorPrincess.exe
        echo   Tamano: !EXE_SIZE! bytes
        echo  ============================================================
    ) else (
        echo  ============================================================
        echo   COMPILACION OK pero ERROR al copiar a la red.
        echo   El .exe esta en: %LOCAL_DIR%\dist\OrganizadorPrincess.exe
        echo   Copialo manualmente a %RED_DIR%dist\
        echo  ============================================================
    )
) else (
    echo  ============================================================
    echo   ERROR: No se encontro el ejecutable tras la compilacion.
    echo   Causa probable: antivirus elimino el .exe al crearse.
    echo   Excluye %LOCAL_DIR% en Windows Defender e intentalo de nuevo.
    echo  ============================================================
)

echo.
pause
