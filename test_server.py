import unittest
import json
import os
import sys

# Add directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import server

class TestCeci3DCostCalculator(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        server.app.config['TESTING'] = True
        self.client = server.app.test_client()
        
        # Backup existing config path if it exists
        self.original_data_file = server.DATA_FILE
        server.DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Datos_test.json")
        
        # Define test configuration
        self.test_config = {
            "costo_filamento_kg": 20000.0,       # $20.000 ARS per kg ($20 ARS/g)
            "costo_kwh": 500.0,                  # $500 ARS per kWh
            "cotizacion_dolar": 1200.0,          # $1200 ARS/USD
            "impresora_costo_usd": 600.0,        # USD 600
            "impresora_vida_util_hs": 5000.0,    # 5000 hours lifespan (USD 0.12/hr = $144 ARS/hr)
            "mantenimiento_porcentaje": 25.0,    # 25% of amortization ($36 ARS/hr)
            "rentabilidad_defecto": 100.0,
            "gemini_api_key": "test-key"
        }
        server.save_config(self.test_config)

    def tearDown(self):
        # Restore config path and remove test config
        if os.path.exists(server.DATA_FILE):
            os.remove(server.DATA_FILE)
        server.DATA_FILE = self.original_data_file

    def test_get_config(self):
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["costo_filamento_kg"], 20000.0)
        self.assertEqual(data["costo_kwh"], 500.0)

    def test_update_config(self):
        update_data = {
            "costo_filamento_kg": 22000.0,
            "costo_kwh": 600.0
        }
        response = self.client.post('/api/config', json=update_data)
        self.assertEqual(response.status_code, 200)
        
        # Read back config
        response2 = self.client.get('/api/config')
        data = json.loads(response2.data)
        self.assertEqual(data["costo_filamento_kg"], 22000.0)
        self.assertEqual(data["costo_kwh"], 600.0)
        # Check non-updated values remain same
        self.assertEqual(data["cotizacion_dolar"], 1200.0)

    def test_calculate_cost(self):
        # Inputs: 100 grams, 2 hours 30 minutes (2.5 hours)
        # Expected outputs:
        # 1. Filament: 100g * (20000/1000) = $2000.0 ARS
        # 2. Energy: 2.5 hours * 0.09 kW * 500 ARS/kWh = $112.5 ARS
        # 3. Amortization: 2.5 hours * (600 / 5000) USD/hr * 1200 ARS/USD = 2.5 * 0.12 * 1200 = $360.0 ARS
        # 4. Maintenance: 360.0 * 25% = $90.0 ARS
        # Subtotal: 2000.0 + 112.5 + 360.0 + 90.0 = $2562.5 ARS
        
        calc_input = {
            "grams": 100.0,
            "hours": 2,
            "minutes": 30
        }
        response = self.client.post('/api/calculate', json=calc_input)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data["inputs"]["grams"], 100.0)
        self.assertEqual(data["breakdown"]["filament"], 2000.0)
        self.assertEqual(data["breakdown"]["energy"], 112.5)
        self.assertEqual(data["breakdown"]["amortization"], 360.0)
        self.assertEqual(data["breakdown"]["maintenance"], 90.0)
        self.assertEqual(data["subtotal"], 2562.5)

if __name__ == '__main__':
    unittest.main()
