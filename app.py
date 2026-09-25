import os
import random
import string
import sqlite3
import requests
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# --- CREDENCIALES DE TELEGRAM (Desde variables de entorno de Render) ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- BASE DE DATOS SQLITE ---
DB_FILE = 'chaz_database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitudes (
            codigo TEXT PRIMARY KEY,
            nombre TEXT,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            categoria TEXT,
            subcategoria TEXT,
            descripcion TEXT,
            estado TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def generar_codigo_seguimiento():
    return 'CHAZ-' + ''.join(random.choices(string.digits, k=4))

# --- VISTA CLIENTE: FORMULARIO PRINCIPAL Y BUSCADOR ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chaz - Asistencia al Hogar</title>
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f4f6f9; display: flex; flex-direction: column; align-items: center; }
        .top-bar { width: 100%; max-width: 480px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .top-bar a { font-size: 13px; color: #2b6cb0; text-decoration: none; font-weight: bold; background: #e2e8f0; padding: 8px 12px; border-radius: 20px; }
        .top-bar a:hover { background: #cbd5e0; }
        .form-card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 480px; box-sizing: border-box; }
        h2 { color: #1a202c; text-align: center; margin-bottom: 20px; font-size: 24px; }
        label { font-size: 14px; font-weight: 600; color: #4a5568; display: block; margin-bottom: 6px; }
        input, select, textarea { width: 100%; padding: 12px; margin-bottom: 16px; border: 1px solid #cbd5e0; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { background-color: #2b6cb0; color: white; padding: 14px; border: none; border-radius: 6px; width: 100%; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background-color: #2c5282; }
    </style>
</head>
<body>

<div class="top-bar">
    <span style="font-size: 14px; font-weight: bold; color: #2b6cb0;">⚡ Chaz</span>
    <a href="/buscar-seguimiento">🔍 Consultar mi pedido</a>
</div>

<div class="form-card" x-data="formularioChaz()">
    <h2>Pedir un servicio</h2>
    <form action="/pedir-servicio" method="POST">
        <label>Tu Nombre:</label>
        <input type="text" name="nombre" required placeholder="Ej: Juan Pérez">

        <label>Teléfono de Contacto (WhatsApp):</label>
        <input type="tel" name="telefono" required placeholder="+56912345678">

        <label>Correo Electrónico:</label>
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

# --- VISTA CLIENTE: BUSCADOR MANUAL DE CÓDIGO ---
HTML_BUSCAR = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consultar Estado - Chaz</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">
    <div class="bg-white p-8 rounded-xl shadow-md max-w-md w-full text-center">
        <h1 class="text-2xl font-bold text-blue-600 mb-2">⚡ Chaz - Seguimiento</h1>
        <p class="text-gray-500 mb-6 text-sm">Ingresa el código de 4 números que te dimos al solicitar el servicio (Ej: CHAZ-1234).</p>

        <form action="/buscar-seguimiento" method="POST" class="space-y-4">
            <input type="text" name="codigo" required placeholder="Ej: CHAZ-1234" class="w-full text-center uppercase font-bold tracking-widest text-lg p-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500">
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition">Buscar Estado</button>
        </form>

        <div class="mt-6">
            <a href="/" class="text-xs text-gray-500 hover:underline">← Volver al formulario principal</a>
        </div>
    </div>
</body>
</html>
"""

# --- VISTA CLIENTE: SEGUIMIENTO DETALLADO ---
HTML_SEGUIMIENTO = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estado de Solicitud - Chaz</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">
    <div class="bg-white p-8 rounded-xl shadow-md max-w-md w-full text-center">
        <h1 class="text-2xl font-bold text-blue-600 mb-2">Chaz - Estado del Servicio</h1>
        <p class="text-gray-500 mb-6">Código de seguimiento: <strong class="text-gray-800">{{ codigo }}</strong></p>

        {% if encontrado %}
            <div class="bg-blue-50 border border-blue-200 p-4 rounded-lg mb-6">
                <p class="text-xs text-blue-600 font-semibold uppercase tracking-wider">Estado actual</p>
                <p class="text-xl font-bold text-blue-900 mt-1">{{ solicitud.estado }}</p>
            </div>
            <div class="text-left text-sm text-gray-600 space-y-2 mb-6 bg-gray-50 p-4 rounded-lg">
                <p><strong>Cliente:</strong> {{ solicitud.nombre }}</p>
                <p><strong>Servicio:</strong> {{ solicitud.categoria }}</p>
                <p><strong>Detalle:</strong> {{ solicitud.subcategoria }}</p>
                <p><strong>Dirección:</strong> {{ solicitud.direccion }}</p>
            </div>
        {% else %}
            <div class="bg-red-50 border border-red-200 p-4 rounded-lg mb-6 text-red-700 text-sm">
                No encontramos ninguna solicitud registrada con el código <strong>{{ codigo }}</strong>.
            </div>
        {% endif %}

        <div class="flex gap-2 justify-center">
            <a href="/buscar-seguimiento" class="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold px-4 py-2 rounded-lg text-xs transition">Probar otro código</a>
            <a href="/" class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg text-xs transition">Inicio</a>
        </div>
    </div>
</body>
</html>
"""

# --- VISTA ADMIN: GESTIÓN DE SOLICITUDES ---
HTML_ADMIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Chaz - Administración</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-6">
    <div class="max-w-6xl mx-auto bg-white p-6 rounded-xl shadow-md">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl font-bold text-blue-600">⚡ Panel de Control - Chaz</h1>
            <a href="/" class="text-sm text-blue-500 hover:underline">Ir a la Web</a>
        </div>

        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-gray-200 text-gray-700 text-sm">
                        <th class="p-3">Código</th>
                        <th class="p-3">Cliente</th>
                        <th class="p-3">Contacto</th>
                        <th class="p-3">Servicio</th>
                        <th class="p-3">Estado Actual</th>
                        <th class="p-3 text-center">Cambiar Estado</th>
                    </tr>
                </thead>
                <tbody class="divide-y text-sm">
                    {% for row in solicitudes %}
                    <tr class="hover:bg-gray-50">
                        <td class="p-3 font-bold text-blue-600">{{ row[0] }}</td>
                        <td class="p-3 font-semibold">{{ row[1] }}<br><span class="text-xs text-gray-500">{{ row[4] }}</span></td>
                        <td class="p-3">
                            <a href="https://wa.me/{{ row[2].replace('+', '').replace(' ', '') }}" target="_blank" class="text-green-600 font-bold hover:underline">💬 {{ row[2] }}</a><br>
                            <span class="text-xs text-gray-500">{{ row[3] }}</span>
                        </td>
                        <td class="p-3">
                            <strong>{{ row[5] }}</strong><br>
                            <span class="text-xs text-gray-600">{{ row[6] }}</span>
                        </td>
                        <td class="p-3">
                            <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-bold">{{ row[8] }}</span>
                        </td>
                        <td class="p-3 text-center">
                            <form action="/admin/actualizar-estado" method="POST" class="flex gap-1 justify-center">
                                <input type="hidden" name="codigo" value="{{ row[0] }}">
                                <select name="nuevo_estado" class="text-xs border rounded p-1">
                                    <option value="🔎 Buscando técnico calificado en la zona">Buscando técnico</option>
                                    <option value="👨‍🔧 Técnico asignado (En coordinación)">Técnico asignado</option>
                                    <option value="🚗 Técnico en camino">En camino</option>
                                    <option value="✅ Servicio Finalizado con éxito">Finalizado</option>
                                    <option value="❌ Cancelado">Cancelado</option>
                                </select>
                                <button type="submit" class="bg-blue-600 text-white px-2 py-1 rounded text-xs font-bold hover:bg-blue-700">Guardar</button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" class="p-6 text-center text-gray-500">No hay solicitudes registradas aún.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

def enviar_telegram(mensaje):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Faltan variables TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en Render")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

@app.route('/')
def home():
    return render_template_string(HTML_LAYOUT)

@app.route('/buscar-seguimiento', methods=['GET', 'POST'])
def buscar_seguimiento():
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo', '').strip().upper()
        if not codigo_ingresado.startswith('CHAZ-') and codigo_ingresado.isdigit():
            codigo_ingresado = 'CHAZ-' + codigo_ingresado
        return redirect(url_for('seguimiento', codigo=codigo_ingresado))
    return render_template_string(HTML_BUSCAR)

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
    estado_inicial = "🔎 Buscando técnico calificado en la zona"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO solicitudes (codigo, nombre, telefono, email, direccion, categoria, subcategoria, descripcion, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (codigo, nombre, telefono, email, direccion, categoria, subcategoria, descripcion, estado_inicial))
    conn.commit()
    conn.close()

    tel_limpio = "".join(filter(str.isdigit, telefono))
    link_wa = f"https://wa.me/{tel_limpio}"

    mensaje_telegram = f"""
<b>🚨 NUEVA SOLICITUD EN CHAZ [{codigo}] 🚨</b>

👤 <b>Cliente:</b> {nombre}
📞 <b>Teléfono:</b> <a href="{link_wa}">{telefono}</a>
📧 <b>Email:</b> {email}
📍 <b>Dirección:</b> {direccion}
🛠️ <b>Categoría:</b> {categoria}
📌 <b>Detalle:</b> {subcategoria}
📝 <b>Problema:</b> {descripcion}

👉 <a href="{link_wa}"><b>Haz clic aquí para hablar por WhatsApp con el cliente</b></a>
"""
    enviar_telegram(mensaje_telegram)

    return f"""
    <div style='max-width:500px; margin: 40px auto; text-align:center; padding:30px; font-family:sans-serif; background:#fff; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.1);'>
        <h1 style='color:#2b6cb0; margin-bottom:10px;'>¡Solicitud recibida! ⚡</h1>
        <p style='color:#4a5568;'>Hola <strong>{nombre}</strong>, ingresamos tu requerimiento con éxito.</p>
        
        <div style='background:#edf2f7; padding:15px; border-radius:8px; margin:20px 0;'>
            <p style='margin:0; font-size:14px; color:#718096;'>Tu código de seguimiento:</p>
            <span style='font-size:26px; font-weight:bold; color:#2b6cb0;'>{codigo}</span>
        </div>

        <p style='color:#2d3748; font-size:15px;'>📱 <strong>Te contactaremos a la brevedad por WhatsApp</strong> para coordinar los detalles y la visita del técnico.</p>
        
        <div style='margin-top:25px;'>
            <a href='/seguimiento/{codigo}' style='background-color:#2b6cb0; color:white; padding:12px 20px; text-decoration:none; border-radius:6px; font-weight:bold; font-size:14px;'>Ver Estado de mi Solicitud</a>
        </div>
    </div>
    """

@app.route('/seguimiento/<codigo>')
def seguimiento(codigo):
    codigo = codigo.upper()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM solicitudes WHERE codigo = ?', (codigo,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return render_template_string(HTML_SEGUIMIENTO, encontrado=False, codigo=codigo)

    solicitud = {
        'nombre': row[1],
        'telefono': row[2],
        'email': row[3],
        'direccion': row[4],
        'categoria': row[5],
        'subcategoria': row[6],
        'descripcion': row[7],
        'estado': row[8]
    }
    return render_template_string(HTML_SEGUIMIENTO, encontrado=True, solicitud=solicitud, codigo=codigo)

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM solicitudes ORDER BY rowid DESC')
    solicitudes = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_ADMIN, solicitudes=solicitudes)

@app.route('/admin/actualizar-estado', methods=['POST'])
def actualizar_estado():
    codigo = request.form.get('codigo')
    nuevo_estado = request.form.get('nuevo_estado')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE solicitudes SET estado = ? WHERE codigo = ?', (nuevo_estado, codigo))
    conn.commit()
    conn.close()

    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
