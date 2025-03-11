from flask import Flask, request, jsonify
from pymongo import MongoClient
from difflib import get_close_matches
import datetime
import spacy
from flask_cors import CORS
from functools import wraps
import bcrypt

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
        if not auth or auth != "Bearer secrettoken":
            return jsonify({"error": "Unauthorized"}), 401
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
    return jsonify({"token": "secrettoken"})

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

if __name__ == "__main__":
    if not usuarios.find_one({"username": "admin"}):
        hashed_admin = bcrypt.hashpw("admin123".encode('utf8'), bcrypt.gensalt())
        usuarios.insert_one({"username": "admin", "password": hashed_admin.decode('utf8')})
    app.run(debug=True)