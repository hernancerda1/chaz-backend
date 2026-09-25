import os
import random
import string
import requests
import resend
from flask import Flask, render_template_string, request

app = Flask(__name__)

# --- CONFIGURACIÓN DE CORREO CON RESEND ---
resend.api_key = os.environ.get('RESEND_API_KEY')

# --- CREDENCIALES DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = '8645189972:AAHCxjsGiorRmBs19BwYJIDiteEaQEmKxWg'
TELEGRAM_CHAT_ID = '7798074673'

# Base de datos temporal en memoria
solicitudes_db = {}

def generar_codigo_seguimiento():
    return 'CHAZ-' + ''.join(random.choices(string.digits, k=4))

# HTML PRINCIPAL
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chaz - Solicitud de Servicio</title>
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f4f6f9; display: flex; justify-content: center; }
        .form-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 480px; }
        h2 { color: #1a202c; text-align: center; margin-bottom: 20px; font-size: 24px; }
        label { font-size: 14px; font-weight: 600; color: #4a5568; display: block; margin-bottom: 6px; }
        input, select, textarea { width: 100%; padding: 12px; margin-bottom: 16px; border: 1px solid #cbd5e0; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { background-color: #2b6cb0; color: white; padding: 14px; border: none; border-radius: 6px; width: 100%; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #2c5282; }
    </style>
</head>
<body>
<div class="form-card" x-data="formularioChaz()">
    <h2>⚡ Pedir un servicio en Chaz</h2>
    <form action="/pedir-servicio" method="POST">
        <label>Tu Nombre:</label>
        <input type="text" name="nombre" required placeholder="Ej: Juan Pérez">

        <label>Teléfono de Contacto (WhatsApp):</label>
        <input type="tel" name="telefono" required placeholder="+56912345678">

        <label>Correo Electrónico (para tu comprobante):</label>
        <input type="email" name="email" required placeholder="ejemplo@correo.com">

        <label>Dirección / Comuna:</label>
        <input type="text" name="direccion" required placeholder="Ej: Av. Las Condes 1234, Lo Barnechea">

        <label>Categoría del Servicio:</label>
        <select x-model="categoriaSeleccionada" name="categoria" required>
            <option value="">-- Selecciona qué necesitas --</option>
            <template x-for="(item, index) in Object.keys(opciones)" :key="index">
                <option :value="item" x-text="item"></option>
            </template>
        </select>

        <div x-show="categoriaSeleccionada">
            <label>Problema Específico:</label>
            <select name="subcategoria" required>
                <option value="">-- Detalla tu requerimiento --</option>
                <template x-for="sub in opciones[categoriaSeleccionada]" :key="sub">
                    <option :value="sub" x-text="sub"></option>
                </template>
            </select>
        </div>

        <label>Describe brevemente el problema:</label>
        <textarea name="descripcion" rows="3" required placeholder="Ej: Fuga bajo el lavaplatos / Cortocircuito en la cocina"></textarea>

        <button type="submit">Solicitar Técnico Ahora</button>
    </form>
</div>

<script>
function formularioChaz() {
    return {
        categoriaSeleccionada: '',
        opciones: {
            '⚡ Electricidad e Iluminación': [
                'Cortocircuito / Salto de automáticos',
                'Cambio o instalación de enchufes e interruptores',
                'Instalación de lámparas y luminarias',
                'Termos eléctricos, encimeras o aire acondicionado',
                'Instalación / Cableado completo (SEC)'
            ],
            '🚰 Gasfitería, Gas y Agua': [
                'Reparaciones o mantención de Calefón (Todas las marcas)',
                'Fugas de agua o filtraciones',
                'Fugas de gas (Certificado SEC)',
                'Destape con máquina profesional / Limpieza de cañerías',
                'Cambio de llaves de paso, sifones o grifería'
            ],
            '🎨 Pintura y Terminaciones': [
                'Pintura de muros interiores o cielos',
                'Pintura de fachadas / exterior',
                'Reparación de grietas, pasta muro y enmascarado'
            ],
            '🔨 Reparaciones Estructurales y Proyectos': [
                'Arreglos generales y fijaciones en el hogar',
                'Instalación / Reparación de cerámica y muros',
                'Construcción de quinchos o cobertizos'
            ]
        }
    }
}
</script>
</body>
</html>
"""

# HTML SEGUIMIENTO
HTML_SEGUIMIENTO = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estado de Solicitud - Chaz</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">
    <div class="bg-white p-8 rounded-xl shadow-md max-w-md w-full text-center">
        <h1 class="text-2xl font-bold text-blue-600 mb-2">Chaz - Estado del Servicio</h1>
        <p class="text-gray-500 mb-6">Código: <strong class="text-gray-800">{{ codigo }}</strong></p>

        {% if encontrado %}
            <div class="bg-blue-50 border border-blue-200 p-4 rounded-lg mb-6">
                <p class="text-sm text-blue-800 font-semibold">Estado actual:</p>
                <p class="text-lg font-bold text-blue-900 mt-1">{{ solicitud.estado }}</p>
            </div>
            <div class="text-left text-sm text-gray-600 space-y-2 mb-6">
                <p><strong>Cliente:</strong> {{ solicitud.nombre }}</p>
                <p><strong>Servicio:</strong> {{ solicitud.categoria }}</p>
                <p><strong>Detalle:</strong> {{ solicitud.subcategoria }}</p>
            </div>
        {% else %}
            <div class="bg-red-50 border border-red-200 p-4 rounded-lg mb-6 text-red-700">
                No encontramos ninguna solicitud registrada con este código.
            </div>
        {% endif %}

        <a href="/" class="text-blue-600 hover:underline text-sm font-semibold">← Volver al inicio</a>
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
        print(f"Error enviando Telegram: {e}")

@app.route('/')
def home():
    return render_template_string(HTML_LAYOUT)

@app.route('/pedir-servicio', methods=['POST'])
def pedir_servicio():
    datos = request.form
    nombre = datos.get('nombre')
    telefono = datos.get('telefono')
    email = datos.get('email')
    direccion = datos.get('direccion')
    categoria = datos.get('categoria')
    subcategoria = datos.get('subcategoria')
    descripcion = datos.get('descripcion')

    codigo = generar_codigo_seguimiento()

    solicitudes_db[codigo] = {
        'nombre': nombre,
        'categoria': categoria,
        'subcategoria': subcategoria,
        'estado': 'Buscando técnico calificado en la zona',
        'direccion': direccion
    }

    # 1. Alerta por Telegram
    mensaje_telegram = f"""
🚨 *NUEVA SOLICITUD EN CHAZ [{codigo}]* 🚨

👤 *Cliente:* {nombre}
📞 *Teléfono:* {telefono}
📧 *Email:* {email}
📍 *Dirección:* {direccion}
🛠️ *Categoría:* {categoria}
📌 *Detalle:* {subcategoria}
📝 *Problema:* {descripcion}
"""
    enviar_telegram(mensaje_telegram)

    # 2. Envío de Correo mediante API HTTP de Resend (Rápido e infalible)
    try:
        resend.Emails.send({
            "from": "Chaz Servicios <onboarding@resend.dev>",
            "to": [email],
            "subject": f"Confirmación de Solicitud #{codigo} - Chaz",
            "html": f"""
            <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                <h2 style="color: #2b6cb0; text-align: center;">¡Recibimos tu solicitud en Chaz!</h2>
                <p>Hola <strong>{nombre}</strong>,</p>
                <p>Hemos recibido tu requerimiento para el servicio de <strong>{categoria}</strong> ({subcategoria}). Tu código de seguimiento es:</p>
                <div style="background-color: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 2px; color: #2b6cb0; border-radius: 6px; margin: 20px 0;">
                    {codigo}
                </div>
                <p>Estamos notificando a nuestros técnicos verificados de tu zona. Te contactaremos a la brevedad para coordinar la visita.</p>
                <p>Puedes revisar el estado de tu solicitud en tiempo real haciendo clic en el siguiente enlace:</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="https://{request.host}/seguimiento/{codigo}" style="background-color: #2b6cb0; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Ver Estado de mi Solicitud</a>
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
                <p style="font-size: 12px; color: #6b7280; text-align: center;">Chaz – Asistencia al Hogar On-Demand</p>
            </div>
            """
        })
    except Exception as e:
        print(f"Error enviando correo con Resend: {e}")

    return f"""
    <div style='text-align:center; padding:50px; font-family:sans-serif;'>
        <h1 style='color:#2b6cb0;'>¡Solicitud recibida! ⚡</h1>
        <p>Tu código de seguimiento es: <strong>{codigo}</strong></p>
        <p>Te enviamos un correo de confirmación a <strong>{email}</strong> con los detalles.</p>
        <p><a href='/seguimiento/{codigo}' style='color:#2b6cb0; font-weight:bold;'>Ver avance de mi solicitud</a></p>
    </div>
    """

@app.route('/seguimiento/<codigo>')
def seguimiento(codigo):
    solicitud = solicitudes_db.get(codigo)
    if not solicitud:
        return render_template_string(HTML_SEGUIMIENTO, encontrado=False, codigo=codigo)
    return render_template_string(HTML_SEGUIMIENTO, encontrado=True, solicitud=solicitud, codigo=codigo)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
