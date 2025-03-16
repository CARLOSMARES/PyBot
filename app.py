#####
# Creación de un chatbot con Flask y MongoDB
# Autor: Carlos Ignacio Olano Mares
# Fecha: 04 de Marzo de 2025
# Fecha Ultima Actualización: 15 de Marzo de 2025
# Descripción: Código fuente de un chatbot que utiliza Flask y MongoDB para almacenar respuestas y preguntas.
#              El chatbot puede responder preguntas previamente registradas y aprender nuevas respuestas.
#              Se incluye un sistema de autenticación con tokens para proteger ciertos endpoints.
#              El chatbot también guarda un historial de las conversaciones.
#              Para ejecutar el chatbot, se debe instalar Flask, pymongo, spacy y bcrypt.
#              Para instalar las dependencias, ejecutar el siguiente comando:
#              pip install -r requirements.txt
#              Para ejecutar el chatbot, ejecutar el siguiente comando:
#              python app.py
#              El chatbot estará disponible en http://
#              Para interactuar con el chatbot, se pueden utilizar las siguientes rutas:
#              - /chat: Para enviar una pregunta al chatbot.
#              - /respuesta: Para registrar una nueva pregunta y respuesta en el chatbot.
#              - /historial: Para obtener el historial de conversaciones del chatbot.
#              - /login: Para autenticarse y obtener un token de acceso.
#              - /register: Para registrar un nuevo usuario en el chatbot.
#              El chatbot incluye un usuario administrador con las credenciales admin:admin123.
#              Para autenticarse como administrador, se puede utilizar el siguiente comando:
#              curl -X POST http://localhost:5000/login -H "Content-Type: application/json" -d '{"username": "admin", "password": "admin123"}'
#              El token de acceso se puede utilizar para acceder a los endpoints protegidos.
#              Para registrar un nuevo usuario, se puede utilizar el siguiente comando:
#              curl -X POST http://localhost:5000/register -H "Content-Type: application/json" -d '{"username": "usuario", "password": "contraseña"}'
#              El chatbot se puede utilizar para responder preguntas o aprender nuevas respuestas.
#              Para enviar una pregunta al chatbot, se puede utilizar el siguiente comando:
#              curl -X POST http://localhost:5000/chat -H "Content-Type: application/json" -d '{"prompt": "pregunta"}'
#              Para registrar una nueva pregunta y respuesta en el chatbot, se puede utilizar el siguiente comando:
#              curl -X POST http://localhost:5000/respuesta -H "Content-Type: application
#              Para obtener el historial de conversaciones del chatbot, se puede utilizar el siguiente comando:
#              curl -X GET http://localhost:5000/historial
#              El chatbot responde a preguntas previamente registradas y aprende nuevas respuestas.
#              Si no se encuentra una respuesta exacta, el chatbot sugiere preguntas similares.
#              El chatbot también responde a saludos, despedidas, agradecimientos y solicitudes de ayuda.
#              El chatbot utiliza un modelo de lenguaje de spaCy para analizar las intenciones del usuario.
#              El chatbot utiliza una base de datos MongoDB para almacenar las preguntas y respuestas.
#              El chatbot utiliza bcrypt para almacenar contraseñas de forma segura.
#              El chatbot utiliza tokens de acceso para proteger ciertos endpoints.
#              El chatbot utiliza CORS para permitir solicitudes desde cualquier origen.
#              El chatbot utiliza decoradores de Python para proteger los endpoints.
#              El chatbot utiliza funciones de Python para manejar las solicitudes HTTP.
#              El chatbot utiliza funciones de Python para interactuar con la base de datos MongoDB.
#              El chatbot utiliza funciones
#              de Python para analizar las intenciones del usuario y generar respuestas.
#              El chatbot utiliza funciones de Python para manejar la autenticación y el registro de usuarios.
#              El chatbot utiliza funciones de Python para manejar el historial de conversaciones.
#              El chatbot utiliza funciones de Python para manejar las sugerencias de preguntas similares.
#              El chatbot utiliza funciones de Python para manejar las respuestas a saludos, despedidas, agradecimientos y solicitudes de ayuda.
#              El chatbot utiliza funciones de Python para manejar las respuestas a preguntas previamente registradas y aprende nuevas respuestas.
#####

from flask import Flask, request, jsonify
from pymongo import MongoClient
from difflib import get_close_matches
import datetime
import spacy
from flask_cors import CORS
from functools import wraps
import bcrypt
import base64  # nueva importación

app = Flask(__name__)
CORS(app)

nlp = spacy.load("en_core_web_sm")

cliente = MongoClient("mongodb://localhost:27017/")
db = cliente["chatbot"]
coleccion = db["respuestas"]
historial = db["historial"]
usuarios = db["usuarios"]

def analizar_intencion(prompt: str) -> str:
    doc = nlp(prompt.lower())
    for token in doc:
        if token.lemma_ in ["saludar", "hola"]:
            return "saludo"
        elif token.lemma_ in ["salir", "adios", "chao", "hasta luego", "hasta la vista", "nos vemos"]:
            return "despedida"
        elif token.lemma_ in ["gracias", "agradecer"]:
            return "agradecimiento"
        elif token.lemma_ in ["ayuda", "asistir"]:
            return "ayuda"
    return "desconocida"

def obtener_respuesta_intencion(intencion: str) -> str:
    respuestas_intencion = {
        "saludo": "¡Hola! ¿En qué puedo ayudarte?",
        "despedida": "¡Hasta luego! Que tengas un buen día.",
        "agradecimiento": "¡De nada! Siempre estoy aquí para ayudarte.",
        "ayuda": "Puedo responder preguntas o aprender nuevas respuestas. ¡Solo dime en qué necesitas ayuda!"
    }
    return respuestas_intencion.get(intencion, None)

def guardar_historial(prompt: str, respuesta: str):
    historial.insert_one({
        "fecha": datetime.datetime.now(),
        "pregunta": prompt,
        "respuesta": respuesta
    })

def obtener_respuesta(prompt: str) -> str:
    """Obtiene una respuesta de la base de datos."""
    resultado = coleccion.find_one({"pregunta": prompt.lower()})
    return resultado["respuesta"] if resultado else None

def guardar_respuesta(prompt: str, respuesta: str):
    """Guarda una nueva pregunta y respuesta en la base de datos."""
    coleccion.insert_one({"pregunta": prompt.lower(), "respuesta": respuesta})

def sugerir_preguntas(prompt: str):
    """Sugiere preguntas similares si no se encuentra una respuesta exacta."""
    preguntas_existentes = [doc["pregunta"] for doc in coleccion.find({}, {"pregunta": 1})]
    sugerencias = get_close_matches(prompt.lower(), preguntas_existentes, n=3, cutoff=0.6)
    return sugerencias

def generar_respuesta(prompt: str) -> str:
    """Genera una respuesta basada en preguntas previas o aprende nuevas respuestas."""
    intencion = analizar_intencion(prompt)
    respuesta_intencion = obtener_respuesta_intencion(intencion)
    if respuesta_intencion:
        guardar_historial(prompt, respuesta_intencion)
        return respuesta_intencion

    respuesta = obtener_respuesta(prompt)
    if respuesta:
        guardar_historial(prompt, respuesta)
        return respuesta
    else:
        sugerencias = sugerir_preguntas(prompt)
        if sugerencias:
            return f"No encontré una respuesta exacta. ¿Quisiste decir?: {', '.join(sugerencias)}"

        return "No sé la respuesta. Por favor, proporciona una respuesta."

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth.split(" ")[1]
        try:
            decoded = base64.b64decode(token.encode('utf8')).decode('utf8')
            username, password = decoded.split(":", 1)
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401
        user = usuarios.find_one({"username": username})
        if not user or not bcrypt.checkpw(password.encode('utf8'), user["password"].encode('utf8')):
            return jsonify({"error": "Invalid token credentials"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    user = usuarios.find_one({"username": username})
    if not user or not bcrypt.checkpw(password.encode('utf8'), user["password"].encode('utf8')):
        return jsonify({"error": "Invalid credentials"}), 401
    token = base64.b64encode(f"{username}:{password}".encode('utf8')).decode('utf8')  # generación del token
    return jsonify({"token": token})

@app.route('/register', methods=['POST'])
@token_required
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if usuarios.find_one({"username": username}):
        return jsonify({"error": "User already exists"}), 400
    hashed = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
    usuarios.insert_one({"username": username, "password": hashed.decode('utf8')})
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    respuesta = generar_respuesta(prompt)
    return jsonify({"respuesta": respuesta})

@app.route('/respuesta', methods=['POST'])
@token_required
def nueva_respuesta():
    data = request.json
    prompt = data.get('prompt')
    respuesta = data.get('respuesta')
    if not prompt or not respuesta:
        return jsonify({"error": "Prompt and respuesta are required"}), 400

    guardar_respuesta(prompt, respuesta)
    return jsonify({"message": "Respuesta guardada correctamente"}), 201

@app.route('/historial', methods=['GET'])
@token_required  # nuevo decorador para proteger el endpoint
def obtener_historial():
    # Obtener historial de chat ordenado por fecha descendente
    entries = historial.find().sort("fecha", -1)
    result = []
    for entry in entries:
        # Convertir los datos para hacerlos JSON serializables
        entry['_id'] = str(entry['_id'])
        entry['fecha'] = entry['fecha'].strftime("%Y-%m-%d %H:%M:%S")
        result.append(entry)
    return jsonify(result)

if __name__ == "__main__":
    if not usuarios.find_one({"username": "admin"}):
        hashed_admin = bcrypt.hashpw("admin123".encode('utf8'), bcrypt.gensalt())
        usuarios.insert_one({"username": "admin", "password": hashed_admin.decode('utf8')})
    app.run(debug=True)