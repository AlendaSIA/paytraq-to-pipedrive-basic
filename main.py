import os
import requests
from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET
import traceback

app = Flask(__name__)

# Pipedrive API dati
PIPEDRIVE_API_TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN")
PIPEDRIVE_API_URL = 'https://api.pipedrive.com/v1'
PIPELINE_ID = 10  # Testa Pipeline
STAGE_ID = 5      # Ienācis Pasūtījums

@app.route('/', methods=['GET'])
def index():
    return "Service is up and running!"

@app.route('/get-paytraq-orders', methods=['POST'])
def get_paytraq_orders():
    try:
        xml_data = request.data
        root = ET.fromstring(xml_data)

        # Izvilkšana no XML
        document_number = root.findtext(".//DocumentRef")
        registration_number = root.findtext(".//Client//RegistrationNumber")
        client_name = root.findtext(".//Client//Name")
        email = root.findtext(".//Client//Email")

        data = {
            "document_number": document_number,
            "registration_number": registration_number,
            "client_name": client_name,
            "email": email
        }

        # Iekšēji padodam uz sync funkciju, lai nav jāsauc ārēji
        return sync_internal(data)

    except Exception as e:
        print("KĻŪDA:", str(e))
        traceback.print_exc()
        return jsonify({
            "paytraq_status": "success",
            "sync_status": 500,
            "sync_response": f"Server error: {str(e)}"
        })

@app.route('/sync', methods=['POST'])
def sync():
    data = request.get_json()
    return sync_internal(data)

def sync_internal(data):
    if not data:
        return jsonify({'message': 'No valid data provided'}), 400

    org = find_or_create_organization(data)
    person = find_or_create_person(data, org)
    deal = create_deal(data['document_number'], org['id'], person['id'])

    return jsonify({'message': 'Deal created successfully', 'deal': deal}), 200

def find_or_create_organization(data):
    reg_nr = data.get('registration_number', '')
    email = data.get('email', '')

    org = None
    if len(reg_nr) > 3:
        org = search_organization_by_custom_field('reg_nr', reg_nr)
    if not org and len(email) > 3:
        org = search_organization_by_email(email)
    if not org:
        org = create_organization(data)
    return org

def search_organization_by_custom_field(field, value):
    url = f"{PIPEDRIVE_API_URL}/organizations/search"
    params = {"term": value, "fields": field, "api_token": PIPEDRIVE_API_TOKEN}
    response = requests.get(url, params=params).json()
    items = response.get('data', {}).get('items', [])
    return items[0]['item'] if items else None

def search_organization_by_email(email):
    url = f"{PIPEDRIVE_API_URL}/organizations/search"
    params = {"term": email, "fields": "email", "api_token": PIPEDRIVE_API_TOKEN}
    response = requests.get(url, params=params).json()
    items = response.get('data', {}).get('items', [])
    return items[0]['item'] if items else None

def create_organization(data):
    url = f"{PIPEDRIVE_API_URL}/organizations"
    payload = {
        "name": data['client_name'],
        "email": data.get('email', ''),
        "custom_fields": {"reg_nr": data.get('registration_number', '')},
        "api_token": PIPEDRIVE_API_TOKEN
    }
    response = requests.post(url, json=payload).json()
    return response['data']

def find_or_create_person(data, org):
    url = f"{PIPEDRIVE_API_URL}/persons/search"
    params = {"term": data.get('email', ''), "fields": "email", "api_token": PIPEDRIVE_API_TOKEN}
    response = requests.get(url, params=params).json()
    items = response.get('data', {}).get('items', [])
    if items:
        return items[0]['item']

    payload = {
        "name": data['client_name'],
        "email": data.get('email', ''),
        "org_id": org['id'],
        "api_token": PIPEDRIVE_API_TOKEN
    }
    url = f"{PIPEDRIVE_API_URL}/persons"
    response = requests.post(url, json=payload).json()
    return response['data']

def create_deal(title, org_id, person_id):
    url = f"{PIPEDRIVE_API_URL}/deals"
    payload = {
        "title": title,
        "org_id": org_id,
        "person_id": person_id,
        "pipeline_id": PIPELINE_ID,
        "stage_id": STAGE_ID,
        "api_token": PIPEDRIVE_API_TOKEN
    }
    response = requests.post(url, json=payload).json()
    return response['data']

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
