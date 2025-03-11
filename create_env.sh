#!/bin/bash
# Verificar si python3.11 está instalado; si no, intentar instalarlo mediante Homebrew
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 no está instalado. Intentando instalarlo con Homebrew..."
    if command -v brew &> /dev/null; then
        brew install python@3.11
    else
        echo "Homebrew no está instalado. Instala Python 3.11 manualmente o instala Homebrew primero."
        exit 1
    fi
fi
# Verificar que la versión de Python sea 3.11
if ! python3.11 --version | grep -q "3.11"; then
    echo "Se requiere Python 3.11 para evitar problemas de compilación con thinc."
    exit 1
fi
# Crear entorno virtual con python3.11
python3.11 -m venv .venv
source .venv/bin/activate
# Actualizar pip, wheel y setuptools
pip install --upgrade pip wheel setuptools
# Instalar dependencias
pip install -r requirements.txt
# Reinstalar numpy con una versión compatible para corregir incompatibilidades binarias
pip install --force-reinstall --upgrade numpy==1.24.3
# Verificar si el modelo de spaCy "en_core_web_sm" está instalado; si no, instalarlo.
if ! python -c "import en_core_web_sm" &> /dev/null; then
    echo "El modelo en_core_web_sm no está instalado, instalándolo..."
    python -m spacy download en_core_web_sm
fi