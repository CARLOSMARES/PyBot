# Utilizar una imagen base oficial de Python 3.11 ligera
FROM python:3.11-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar algunas librerías de Python
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requisitos primero para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Forzar la versión de numpy para evitar incompatibilidades binarias (según tus scripts de entorno)
RUN pip install --force-reinstall --upgrade numpy==1.24.3

# El modelo en_core_web_sm ya debería estar en requirements.txt, 
# pero nos aseguramos de que esté disponible para spaCy
RUN python -m spacy download en_core_web_sm

# Copiar el resto del código de la aplicación
COPY . .

# Crear la carpeta de uploads para el procesamiento de PDFs
RUN mkdir -p uploads

# Exponer el puerto que utiliza Flask
EXPOSE 5000

# Definir variables de entorno (puedes sobrescribirlas al ejecutar el contenedor)
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]