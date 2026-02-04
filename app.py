from flask import Flask, request, jsonify
from pymongo import MongoClient
from difflib import get_close_matches
import datetime
import spacy
from flask_cors import CORS
from functools import wraps
import bcrypt
import base64
import os  # Importación necesaria para variables de entorno
from openai import OpenAI
import fitz
import requests
from request_oauthlib import OAuth1

# Configuración mediante variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-default-key")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

nlp = spacy.load("en_core_web_sm")

# Uso de la variable MONGO_URI configurada en docker-compose
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot"]
coleccion = db["respuestas"]
historial = db["historial"]
usuarios = db["usuarios"]
qna_collection = db["preguntas_generadas"]

def extract_text_from_pdf(pdf_path: str):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text("text") for page in doc)
    return text

def generate_qna(text, api_key):
    # Se utiliza la API Key pasada por el entorno
    prompt = f"Apartir del siguiente texto, genera preguntas y respuestas útiles:"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en generación de preguntas."},
            {"role": "user", "content": prompt + text[:2000]}
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

def obtener_respuesta_openai(prompt: str) -> str:
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

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
    resultado = coleccion.find_one({"pregunta": prompt.lower()})
    return resultado["respuesta"] if resultado else None

def guardar_respuesta(prompt: str, respuesta: str):
    coleccion.insert_one({"pregunta": prompt.lower(), "respuesta": respuesta})

def sugerir_preguntas(prompt: str):
    preguntas_existentes = [doc["pregunta"] for doc in coleccion.find({}, {"pregunta": 1})]
    sugerencias = get_close_matches(prompt.lower(), preguntas_existentes, n=3, cutoff=0.6)
    return sugerencias

def generar_respuesta(prompt: str) -> str:
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
        except Exception:
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
    token = base64.b64encode(f"{username}:{password}".encode('utf8')).decode('utf8')
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
@token_required
def obtener_historial():
    entries = historial.find().sort("fecha", -1)
    result = []
    for entry in entries:
        entry['_id'] = str(entry['_id'])
        entry['fecha'] = entry['fecha'].strftime("%Y-%m-%d %H:%M:%S")
        result.append(entry)
    return jsonify(result)

@app.route('/chatopenai', methods=['POST'])
@token_required
def openai_endpoint():
    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    respuesta = obtener_respuesta_openai(prompt)
    return jsonify({"respuesta": respuesta})

@app.route("/generate-qna", methods=["POST"])
@token_required
def generate_qna_api():
    if "file" not in request.files:
        return jsonify({"error": "No se ha proporcionado un archivo."}), 400
    
    file = request.files["file"]
    os.makedirs("./uploads", exist_ok=True)
    pdf_path = os.path.join("./uploads", file.filename)
    file.save(pdf_path)
    
    text = extract_text_from_pdf(pdf_path)
    qna = generate_qna(text, OPENAI_API_KEY)
    
    qna_collection.insert_one({"archivo": file.filename, "contenido": qna, "fecha": datetime.datetime.now()})
    return jsonify({"preguntas_y_respuestas": qna})

@app.route("/qna", methods=["GET"])
@token_required
def get_qna():
    preguntas = list(qna_collection.find({}, {"_id": 0}))
    return jsonify({"preguntas_generadas": preguntas})

if __name__ == "__main__":
    if not usuarios.find_one({"username": "admin"}):
        hashed_admin = bcrypt.hashpw("admin123".encode('utf8'), bcrypt.gensalt())
        usuarios.insert_one({"username": "admin", "password": hashed_admin.decode('utf8')})
    # Host 0.0.0.0 es necesario para que Flask sea accesible desde fuera del contenedor Docker
    app.run(host="0.0.0.0", port=5000, debug=True)

    # --- ENDPOINT PARA TELEGRAM ---
@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # Usamos tu lógica existente para obtener respuesta de Mongo o OpenAI
        respuesta = generar_respuesta(text)

        # Enviar respuesta de vuelta a Telegram
        token_telegram = os.getenv("TELEGRAM_TOKEN")
        url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
        payload = {"chat_id": chat_id, "text": respuesta}
        requests.post(url, json=payload)
        
    return jsonify({"status": "ok"}), 200

# --- ENDPOINT PARA WHATSAPP (Meta Cloud API) ---
@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    # Verificación del Webhook (Solo se usa una vez al configurar en Meta)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return challenge, 200
        return "Error de verificación", 403

    # Recepción de mensajes
    data = request.json
    try:
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            mensaje_recibido = data["entry"][0]["changes"][0]["value"]["messages"][0]
            wa_id = mensaje_recibido["from"]
            texto_usuario = mensaje_recibido["text"]["body"]

            # Generar respuesta usando tu lógica de MongoDB
            respuesta = generar_respuesta(texto_usuario)

            # Enviar a WhatsApp
            id_telefono = data["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
            token_wa = os.getenv("WHATSAPP_TOKEN")
            url = f"https://graph.facebook.com/v17.0/{id_telefono}/messages"
            headers = {"Authorization": f"Bearer {token_wa}"}
            payload = {
                "messaging_product": "whatsapp",
                "to": wa_id,
                "type": "text",
                "text": {"body": respuesta}
            }
            requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Error en WhatsApp Webhook: {e}")

    return jsonify({"status": "ok"}), 200

# --- ENDPOINT UNIFICADO PARA FACEBOOK E INSTAGRAM ---
@app.route('/webhook/meta', methods=['GET', 'POST'])
def meta_webhook():
    # Validación del Webhook por Meta
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == os.getenv("META_VERIFY_TOKEN"):
            return challenge, 200
        return "Error de autenticación", 403

    # Procesamiento de Mensajes
    data = request.json
    try:
        for entry in data.get('entry', []):
            for messaging_event in entry.get('messaging', []):
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    user_text = messaging_event['message'].get('text')
                    
                    if user_text:
                        # Usar tu lógica de MongoDB y OpenAI
                        respuesta = generar_respuesta(user_text)
                        
                        token_meta = os.getenv("META_ACCESS_TOKEN")
                        url = f"https://graph.facebook.com/v17.0/me/messages?access_token={token_meta}"
                        payload = {
                            "recipient": {"id": sender_id},
                            "message": {"text": respuesta}
                        }
                        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error en Meta Webhook: {e}")
    return "EVENT_RECEIVED", 200

# --- ENDPOINT PARA X (TWITTER) ---
@app.route('/webhook/twitter', methods=['POST'])
def twitter_webhook():
    data = request.json
    
    # X utiliza el evento 'direct_message_events' para DMs
    if "direct_message_events" in data:
        for event in data["direct_message_events"]:
            if event["type"] == "message_create":
                sender_id = event["message_create"]["sender_id"]
                
                # Seguridad: No responder a los propios mensajes del bot
                if sender_id == os.getenv("X_BOT_ID"):
                    continue
                
                user_text = event["message_create"]["message_data"]["text"]
                respuesta = generar_respuesta(user_text)

                # Autenticación requerida por la API de X
                auth = OAuth1(
                    os.getenv("X_CONSUMER_KEY"),
                    os.getenv("X_CONSUMER_SECRET"),
                    os.getenv("X_ACCESS_TOKEN"),
                    os.getenv("X_ACCESS_TOKEN_SECRET")
                )
                
                url = "https://api.twitter.com/2/direct_messages"
                payload = {
                    "recipient_id": sender_id,
                    "text": respuesta
                }
                requests.post(url, auth=auth, json=payload)
                
    return jsonify({"status": "success"}), 200