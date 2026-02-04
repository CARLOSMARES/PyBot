@echo off
setlocal enabledelayedexpansion

:: --- AUTO-ELEVACIÓN A ADMINISTRADOR ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Cambiar al directorio donde está el script
cd /d "%~dp0"

:: 1. Verificar si Python 3.11 ya está instalado
python --version 2>nul | findstr "3.11" >nul
if %errorlevel% equ 0 (
    echo [+] Python 3.11 detectado.
    goto :venv_setup
)

echo [!] Python 3.11 no encontrado. Intentando instalar con Winget...

:: 2. Verificar si Winget está disponible
winget --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Winget no esta disponible. Instala Python 3.11 manualmente.
    pause
    exit /b 1
)

:: 3. Instalar Python 3.11
echo [+] Instalando Python 3.11...
winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements
if %errorlevel% neq 0 (
    echo [X] Hubo un error al intentar instalar Python.
    pause
    exit /b 1
)

echo [!] Instalacion completada. Reinicia el script para aplicar cambios de PATH.
pause
exit /b 0

:venv_setup
:: 4. Crear entorno virtual
echo [+] Creando entorno virtual en .venv...
python -m venv .venv

:: 5. Activar el entorno virtual
call .venv\Scripts\activate

:: 6. Actualizar herramientas base
echo [+] Actualizando pip, wheel y setuptools...
python -m pip install --upgrade pip wheel setuptools

:: 7. Instalar dependencias
if exist requirements.txt (
    echo [+] Instalando dependencias desde requirements.txt...
    pip install -r requirements.txt
)

:: 8. Forzar version de Numpy (Correccion de incompatibilidad binaria)
echo [+] Ajustando version de numpy a 1.24.3...
pip install --force-reinstall --upgrade numpy==1.24.3

:: 9. Verificar modelo de spaCy
python -c "import en_core_web_sm" 2>nul
if %errorlevel% neq 0 (
    echo [+] Instalando modelo spaCy "en_core_web_sm"...
    python -m spacy download en_core_web_sm
) else (
    echo [+] El modelo de spaCy ya esta presente.
)

echo.
echo ===========================================
echo    PROCESO COMPLETADO EXITOSAMENTE
echo ===========================================
pause