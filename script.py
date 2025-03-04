from pymongo import MongoClient
from difflib import get_close_matches
import datetime
import spacy

# Cargar modelo de NLP para análisis de intención
nlp = spacy.load("en_core_web_sm")

# Conexión a MongoDB
cliente = MongoClient("mongodb://localhost:27017/")
db = cliente["chatbot"]
coleccion = db["respuestas"]
historial = db["historial"]


def analizar_intencion(prompt: str) -> str:
    """Analiza la intención del usuario usando NLP."""
    doc = nlp(prompt.lower())
    for token in doc:
        if token.lemma_ in ["saludar", "hola"]:
            return "saludo"
        elif token.lemma_ in ["adiós", "salir", "adios", "chao", "hasta luego", "hasta la vista", "nos vemos"]:
            return "despedida"
        elif token.lemma_ in ["gracias", "agradecer"]:
            return "agradecimiento"
        elif token.lemma_ in ["ayuda", "asistir"]:
            return "ayuda"
    return "desconocida"


def obtener_respuesta_intencion(intencion: str) -> str:
    """Responde automáticamente a ciertas intenciones."""
    respuestas_intencion = {
        "saludo": "¡Hola! ¿En qué puedo ayudarte?",
        "despedida": "¡Hasta luego! Que tengas un buen día.",
        "agradecimiento": "¡De nada! Siempre estoy aquí para ayudarte.",
        "ayuda": "Puedo responder preguntas o aprender nuevas respuestas. ¡Solo dime en qué necesitas ayuda!"
    }
    return respuestas_intencion.get(intencion, None)


def guardar_historial(prompt: str, respuesta: str):
    """Guarda el historial de conversaciones en la base de datos."""
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

        nueva_respuesta = input("No sé la respuesta. ¿Cómo debería responder? ")
        guardar_respuesta(prompt, nueva_respuesta)
        guardar_historial(prompt, nueva_respuesta)
        return "Gracias, ahora lo recordaré para la próxima vez."


if __name__ == "__main__":
    print("Chatbot IA con MongoDB, historial y análisis de intención. Escribe 'salir' para terminar.")
    while True:
        prompt = input("Tú: ")
        if prompt.lower() in ["salir", "exit", "quit"]:
            print("Chatbot: Hasta luego!")
            break
        respuesta = generar_respuesta(prompt)
        print(f"Chatbot: {respuesta}")
