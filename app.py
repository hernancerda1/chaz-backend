import os
from flask import Flask, render_template_string, request
import requests

app = Flask(__name__)

# CONFIGURA TUS DATOS REALES DE TELEGRAM AQUÍ:
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chaz - Solicitud de Servicio</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f4f6f9; display: flex; justify-content: center; }
        .form-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 420px; }
        h2 { color: #1a202c; text-align: center; margin-bottom: 24px; font-size: 24px; }
        label { font-size: 14px; font-weight: 600; color: #4a5568; display: block; margin-bottom: 6px; }
        input, select, textarea { width: 100%; padding: 12px; margin-bottom: 18px; border: 1px solid #cbd5e0; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { background-color: #2b6cb0; color: white; padding: 14px; border: none; border-radius: 6px; width: 100%; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #2c5282; }
    </style>
</head>
<body>
<div class="form-card">
    <h2>⚡ Pedir un servicio en Chaz</h2>
    <form action="/pedir-servicio" method="POST">
        <label>Tu Nombre:</label>
        <input type="text" name="nombre" required placeholder="Ej: Juan Pérez">

        <label>Teléfono de Contacto:</label>
        <input type="tel" name="telefono" required placeholder="+56912345678">

        <label>Dirección / Comuna:</label>
        <input type="text" name="direccion" required placeholder="Ej: Av. Las Condes 1234">

        <label>Tipo de Servicio:</label>
        <select name="servicio">
            <option value="Gasfitería">Gasfitería</option>
            <option value="Electricidad">Electricidad</option>
            <option value="Reparación General">Reparación General / Todoterreno</option>
        </select>

        <label>Describe el problema:</label>
        <textarea name="descripcion" rows="3" required placeholder="Ej: El lavaplatos pierde agua."></textarea>

        <button type="submit">Solicitar Técnico Ahora</button>
    </form>
</div>
</body>
</html>
"""

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

@app.route('/')
def home():
    return render_template_string(HTML_LAYOUT)

@app.route('/pedir-servicio', methods=['POST'])
def pedir_servicio():
    datos = request.form
    mensaje = f"""
🚨 *NUEVA SOLICITUD EN CHAZ* 🚨

👤 *Cliente:* {datos.get('nombre')}
📞 *Teléfono:* {datos.get('telefono')}
📍 *Dirección:* {datos.get('direccion')}
🛠️ *Servicio:* {datos.get('servicio')}
📝 *Problema:* {datos.get('descripcion')}
"""
    enviar_telegram(mensaje)
    return "<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>¡Solicitud recibida! ⚡</h1><p>En breve un ejecutivo de Chaz te contactará para confirmar a tu técnico.</p></div>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
