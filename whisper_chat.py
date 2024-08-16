import spacy
import odoorpc
import whisper
import sounddevice as sd
import numpy as np

# Conectar a Odoo
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('odoo_db', 'admin', 'admin')

# Cargar el modelo de spaCy
nlp = spacy.load("es_core_news_lg")

# Cargar el modelo de Whisper
whisper_model = whisper.load_model("base")

# Función para capturar audio
def grabar_audio(duracion=5, fs=16000):
    print("Grabando...")
    audio = sd.rec(int(duracion * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()  # Esperar hasta que termine la grabación
    print("Grabación finalizada.")
    return np.squeeze(audio)

# Función para convertir audio a texto
def audio_a_texto(audio, fs=16000):
    # Whisper espera un array de floats en el rango [-1, 1], así que no es necesario convertirlo a int16.
    # Vamos a asegurarnos de que el audio esté en formato float32
    audio_float32 = audio.astype(np.float32)
    result = whisper_model.transcribe(audio_float32, fp16=False)
    return result['text']

# Función para interpretar comandos y ejecutarlos en Odoo
def interpretar_y_ejecutar_comando(texto):
    doc = nlp(texto)
    tokens = [token.text.lower() for token in doc]  # Convertir todos los tokens a minúsculas
    texto_lower = doc.text.lower()
    
    # Crear un contacto
    if any(word in tokens for word in ["crear", "hacer", "generar"]) and "contacto" in tokens:
        nombres = [ent.text for ent in doc.ents if ent.label_ == "PER"]
        if nombres:
            # Verificar que el nombre tenga al menos dos palabras
            if any(len(nombre.split()) >= 2 for nombre in nombres):
                partner_model = odoo.env['res.partner']
                partner_model.create({'name': nombres[0]})
                return f"Contacto '{nombres[0]}' creado."
            else:
                return "No se encontró un nombre válido. Se requiere un nombre y un apellido."
        else:
            return "No se encontró un nombre."
    
    # Actualizar o agregar correo electrónico
    if any(word in tokens for word in ["actualizar", "modificar", "cambiar", "agregar", "añadir"]) and any(correo_word in tokens for correo_word in ["correo", "email", "correo electrónico"]):
        nombre = [ent.text for ent in doc.ents if ent.label_ == "PER"]
        email = next((token.text for token in doc if "@" in token.text), None)
        if nombre and email:
            partner_model = odoo.env['res.partner']
            contacto = partner_model.search([('name', '=', nombre[0])], limit=1)
            if contacto:
                partner_model.write(contacto, {'email': email})
                return f"Correo electrónico de {nombre[0]} actualizado a {email}."
            else:
                return f"No se encontró un contacto con el nombre '{nombre[0]}'."
        else:
            return "No se encontró un nombre o correo electrónico válido."
    
    # Mostrar todos los contactos
    elif any(word in tokens for word in ["mostrar", "ver", "enseñar"]) and "contactos" in tokens:
        partner_model = odoo.env['res.partner']
        contactos = partner_model.search([])
        nombres_contactos = partner_model.read(contactos, ['name'])
        return f"Contactos: {', '.join(contacto['name'] for contacto in nombres_contactos)}"
    
    # Modificar el cargo de un contacto
    elif any(word in tokens for word in ["modificar", "cambiar", "alterar"]) and "cargo" in tokens:
        nombre = [ent.text for ent in doc.ents if ent.label_ == "PER"]
        try:
            index_a = tokens.index("a") + 1
            nuevo_cargo = ' '.join(tokens[index_a:])
            if nombre and nuevo_cargo:
                partner_model = odoo.env['res.partner']
                contacto = partner_model.search([('name', '=', nombre[0])], limit=1)
                if contacto:
                    partner_model.write(contacto, {'function': nuevo_cargo})
                    return f"Cargo de {nombre[0]} cambiado a {nuevo_cargo}."
                else:
                    return f"No se encontró un contacto con el nombre '{nombre[0]}'."
            else:
                return "No se encontró un nombre o cargo válido."
        except ValueError:
            return "No se encontró el nuevo cargo."
    
    # Modificar la dirección de un contacto
    elif any(word in tokens for word in ["modificar", "cambiar", "alterar"]) and "dirección" in tokens:
        nombre = [ent.text for ent in doc.ents if ent.label_ == "PER"]
        try:
            index_a = tokens.index("a") + 1
            direccion = ' '.join(tokens[index_a:])
            if nombre and direccion:
                partner_model = odoo.env['res.partner']
                contacto = partner_model.search([('name', '=', nombre[0])], limit=1)
                if contacto:
                    partner_model.write(contacto, {'street': direccion})
                    return f"Dirección de {nombre[0]} cambiada a {direccion}."
                else:
                    return f"No se encontró un contacto con el nombre '{nombre[0]}'."
            else:
                return "No se encontró un nombre o dirección válida."
        except ValueError:
            return "No se encontró la dirección."
    
    # Eliminar un contacto
    elif "eliminar" in tokens and "contacto" in tokens:
        nombre = [ent.text for ent in doc.ents if ent.label_ == "PER"]
        if nombre:
            partner_model = odoo.env['res.partner']
            contacto = partner_model.search([('name', '=', nombre[0])], limit=1)
            if contacto:
                partner_model.unlink(contacto)
                return f"Contacto '{nombre[0]}' eliminado."
            else:
                return f"No se encontró un contacto con el nombre '{nombre[0]}'."
        else:
            return "No se encontró un nombre válido para eliminar."
    
    return "Comando no reconocido."

# Bucle de chat en la terminal con opción de voz
def iniciar_chat():
    print("Chat de integración con Odoo. Escribe 'salir' para terminar.")
    while True:
        modo = input("Escribe 'voz' para usar comandos de voz o cualquier otra tecla para usar texto: ").lower()
        if modo == 'voz':
            duracion = int(input("Duración de la grabación en segundos: "))
            audio = grabar_audio(duracion=duracion)
            comando = audio_a_texto(audio)
            print(f"Texto reconocido: {comando}")
        else:
            comando = input("Ingresa un comando: ")

        if comando.lower() == "salir":
            print("Terminando el chat...")
            break
        resultado = interpretar_y_ejecutar_comando(comando)
        print(f"Resultado: {resultado}")

# Iniciar el chat
iniciar_chat()
