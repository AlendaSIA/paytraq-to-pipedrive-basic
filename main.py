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

@app.route('/get-paytraq-orders', methods=['GET'])
def route_exists_check():
    return jsonify({"message": "Use POST to submit PayTraq XML data."}), 405

@app.route('/get-paytraq-orders', methods=['POST'])
def get_paytraq_orders():
    try:
        print("\n==============================")
        print("SAŅEMTS PIEPRASĪJUMS UZ /get-paytraq-orders")
        print("Content-Type:", request.content_type)

        raw_xml = request.data.decode("utf-8")
        print("Raw XML saturs:")
        print(raw_xml)

        if not request.content_type or "xml" not in request.content_type:
            return jsonify({"error": "Unsupported Content-Type. Use application/xml."}), 415

        xml_data = request.data
        root = ET.fromstring(xml_data)

        # Izvilkšana no XML
        document_number = root.findtext(".//DocumentRef")
        registration_number = root.findtext(".//Client//RegistrationNumber")
        client_name = root.findtext(".//Client//Name")
        email = root.findtext(".//Client//Email")

        print("---- Izvilktie lauki ----")
        print("Document number:", document_number)
        print("Registration number:", registration_number)
        print("Client name:", client_name)
        print("Email:", email)

        data = {
            "document_number": document_number,
            "registration_number": registration_number,
            "client_name": client_name,
            "email": email
        }

        print("DEBUG datu struktūra:", data)
        print("==============================\n")

        return sync_internal(data)

    except Exception as e:
        print("\n==== KĻŪDA SAŅEMOT /get-paytraq-orders ====")
        print("KĻŪDA:", str(e))
        traceback.print_exc()
        return jsonify({
            "paytraq_status": "error",
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

    print(">>> START sync_internal")
    org = find_or_create_organization(data)
    print(">>> ORGANIZATION OK:", org.get('name') if org else "Nav")

    person = find_or_create_person(data, org)
    print(">>> PERSON OK:", person.get('name') if person else "Nav")

    deal = create_deal(data.get('document_number', 'Pasūtījums'), org['id'], person['id'])
    print(">>> DEAL izveidots:", deal.get('title'))

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
        "name": data.get('client_name', 'Klients'),
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
        "name": data.get('client_name', 'Kontakts'),
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
