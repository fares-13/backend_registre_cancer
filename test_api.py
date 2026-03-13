import urllib.request
import json
import os
import django

# Setup Django to get a patient ID
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from patients.models import Patient
patient = Patient.objects.first()

if not patient:
    print("No patient found.")
    exit()

API_URL = "http://localhost:8000/api/cancers/cases/"
payload = {
    "patient_id": str(patient.id_malade)
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(API_URL, data=data, content_type='application/json', method='POST')
req.add_header('Content-Type', 'application/json')

print(f"Sending POST to {API_URL} with payload {payload}")
try:
    with urllib.request.urlopen(req) as f:
        print(f"Status: {f.status}")
        print(f"Response: {f.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
