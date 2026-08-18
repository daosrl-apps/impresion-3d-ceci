import os
import json
import re
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

# Initialize Flask app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
DATA_FILE = os.path.join(DATA_DIR, "Datos.json")

app = Flask(__name__)
app.secret_key = "ceci_3d_secret_key_2026"

# Ensure data and upload directory exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    try:
        os.chmod(DATA_DIR, 0o777)
        os.chmod(UPLOAD_FOLDER, 0o777)
    except Exception as e:
        print(f"Advertencia al configurar permisos de directorios de datos: {e}")

# Default application settings
DEFAULT_CONFIG = {
    "costo_filamento_kg": 18000.0,       # ARS por kg de PLA
    "costo_kwh": 400.0,                  # ARS por kWh
    "cotizacion_dolar": 1000.0,          # ARS por USD
    "impresora_costo_usd": 600.0,        # USD costo de la máquina
    "impresora_vida_util_hs": 5000.0,    # Horas de impresión amortización
    "mantenimiento_porcentaje": 20.0,    # Mantenimiento como % de la amortización
    "rentabilidad_defecto": 100.0,       # % Rentabilidad por defecto
    "gemini_api_key": ""                 # API Key de Gemini
}

def load_config():
    """Loads configuration from Datos.json, or creates it with defaults if it doesn't exist."""
    if not os.path.exists(DATA_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all keys exist
            updated = False
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
                    updated = True
            if updated:
                save_config(data)
            return data
    except Exception as e:
        print(f"Error al leer Datos.json: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Saves configuration to Datos.json safely."""
    try:
        # Save temp file first to prevent corruption
        temp_file = DATA_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        os.rename(temp_file, DATA_FILE)
    except Exception as e:
        print(f"Error al guardar Datos.json: {e}")

# --- API ENDPOINTS ---

@app.route('/api/config', methods=['GET'])
def get_config():
    config = load_config()
    # Mask API key for security in client view if requested (or return it for editing)
    # Since Cecilia needs to edit it, we can return the actual value, but obfuscated slightly in presentation.
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        new_data = request.json
        if not new_data:
            return jsonify({"error": "No se recibieron datos"}), 400
        
        config = load_config()
        # Update editable values
        for key in DEFAULT_CONFIG.keys():
            if key in new_data:
                if key == "gemini_api_key":
                    config[key] = str(new_data[key]).strip()
                else:
                    config[key] = float(new_data[key])
                    
        save_config(config)
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"error": f"Error al guardar configuración: {str(e)}"}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate_cost():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Datos faltantes"}), 400
        
        grams = float(data.get("grams", 0))
        hours = int(data.get("hours", 0))
        minutes = int(data.get("minutes", 0))
        
        config = load_config()
        
        # Update and save filament cost if provided by client on main screen
        if "costo_filamento_kg" in data:
            config["costo_filamento_kg"] = float(data["costo_filamento_kg"])
            save_config(config)
        
        # 1. Costo de filamento (PLA)
        cost_filament = grams * (config["costo_filamento_kg"] / 1000.0)
        
        # 2. Costo de Energía
        # Bambu Lab A1 consume en promedio 90W (0.09 kW)
        time_hours = hours + (minutes / 60.0)
        cost_energy = time_hours * 0.09 * config["costo_kwh"]
        
        # 3. Amortización de Impresora
        # (Costo Impresora USD / Vida útil Horas) * Horas impresas * Cotización Dolar
        hourly_amortization_usd = config["impresora_costo_usd"] / config["impresora_vida_util_hs"]
        cost_amortization = time_hours * hourly_amortization_usd * config["cotizacion_dolar"]
        
        # 4. Mantenimiento
        # % de la amortización
        cost_maintenance = cost_amortization * (config["mantenimiento_porcentaje"] / 100.0)
        
        # Totales
        cost_subtotal = cost_filament + cost_energy + cost_amortization + cost_maintenance
        
        return jsonify({
            "inputs": {
                "grams": grams,
                "hours": hours,
                "minutes": minutes
            },
            "breakdown": {
                "filament": round(cost_filament, 2),
                "energy": round(cost_energy, 2),
                "amortization": round(cost_amortization, 2),
                "maintenance": round(cost_maintenance, 2)
            },
            "subtotal": round(cost_subtotal, 2)
        })
    except Exception as e:
        return jsonify({"error": f"Error en el cálculo: {str(e)}"}), 500

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    if 'file' not in request.files:
        return jsonify({"error": "No se subió ningún archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    
    config = load_config()
    api_key = config.get("gemini_api_key", "").strip()
    
    if not api_key:
        return jsonify({
            "error": "La API Key de Gemini no está configurada. Por favor, configúrala en la sección de Ajustes.",
            "needs_api_key": True
        }), 400

    try:
        # Save file safely
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Initialize Gemini API
        try:
            import google.generativeai as genai
        except ImportError:
            return jsonify({"error": "La librería google-generativeai no está instalada en el servidor."}), 500
        
        genai.configure(api_key=api_key)
        
        # Open image with Pillow
        img = Image.open(filepath)
        
        # Gemini Prompt
        prompt = """
        Analiza la imagen adjunta, la cual es para un calculador de costos de impresión 3D para un emprendimiento premium de Cecilia ("Impresión 3D Ceci").
        
        Determina si la imagen es:
        1) Una captura de pantalla de un software de laminación como Bambu Studio o Bambu Handy.
           - En este caso, busca y extrae los gramos de filamento (PLA/filamento) y el tiempo estimado de impresión (horas y minutos).
        2) Una foto de una pieza física real impresa en 3D.
           - En este caso, identifica qué objeto es. Estima los gramos típicos de material que usaría (suponiendo parámetros estándar: 0.2mm altura de capa, 15% de relleno) impreso en una Bambu Lab A1 Combo, y el tiempo estimado de impresión en horas y minutos.
           - También realiza una estimación del rango de precios comerciales de venta (en pesos argentinos, ARS) para este tipo de objeto en Argentina (comparando con plataformas como MercadoLibre o tiendas de diseño), y proporciona una breve explicación de tu benchmarking de precios del mercado argentino.

        Responde ÚNICAMENTE con un objeto JSON válido con la siguiente estructura (no agregues texto antes ni después, no utilices markdown de código):
        {
          "detected_type": "screenshot" o "photo",
          "object_name": "nombre descriptivo del objeto",
          "weight_grams": número flotante con los gramos detectados o estimados,
          "time_hours": número entero con las horas detectadas o estimadas,
          "time_minutes": número entero con los minutos detectados o estimados (entre 0 y 59),
          "price_benchmark_min": número entero con el precio de mercado mínimo en ARS,
          "price_benchmark_max": número entero con el precio de mercado máximo en ARS,
          "benchmark_explanation": "explicación detallada del benchmark de mercado argentino"
        }
        """
        
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = model.generate_content([img, prompt])
        
        # Clean response and parse JSON
        resp_text = response.text.strip()
        # Strip markdown json block wrappers if present
        resp_text = re.sub(r"^```json\s*", "", resp_text, flags=re.IGNORECASE)
        resp_text = re.sub(r"\s*```$", "", resp_text)
        resp_text = resp_text.strip()
        
        try:
            analysis_result = json.loads(resp_text)
            return jsonify({
                "success": True,
                "analysis": analysis_result,
                "image_url": f"/uploads/{filename}"
            })
        except json.JSONDecodeError as jde:
            print(f"Error al decodificar JSON de Gemini: {jde}. Raw text: {resp_text}")
            return jsonify({
                "error": "La IA no retornó un formato de datos legible. Inténtalo nuevamente o ingresa los datos a mano.",
                "raw_response": resp_text
            }), 500
            
    except Exception as e:
        return jsonify({"error": f"Error al procesar la imagen con Gemini: {str(e)}"}), 500

# Serve uploaded pictures
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# Root static routing
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# Catch-all route to serve other frontend static files
@app.route('/<path:path>')
def send_static(path):
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(BASE_DIR, path)

# Start development server
if __name__ == '__main__':
    # Listen on port 8085 to avoid conflicts with port 8080 or 3000
    app.run(host='0.0.0.0', port=8085, debug=True)
