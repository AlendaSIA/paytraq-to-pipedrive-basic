import os
import requests
import json
from flask import Flask, request

app = Flask(__name__)

PIPEDRIVE_API_TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN")
PIPEDRIVE_API_URL = 'https://api.pipedrive.com/v1'

@app.route('/', methods=['GET'])
def index():
    return 'Service is up and running!'

@app.route('/sync', methods=['POST'])
def sync_paytraq_to_pipedrive():
    data = request.get_json()

    if not data or not data.get('order_name', '').startswith('test'):
        return json.dumps({'message': 'Not a test order, skipping'}), 200

    email = data.get('email')
    person = search_person_by_email(email)

    if not person:
        person = create_person(data.get('client_name'), email)

    deal = create_deal(data.get('order_name'), person['id'])

    product = add_product_to_pipedrive('Test Product', 2.00)
    attach_product_to_deal(deal['id'], product['id'], 2.00)

    return json.dumps({'message': 'Deal created successfully!'}), 200

def search_person_by_email(email):
    url = f'{PIPEDRIVE_API_URL}/persons/search'
    params = {'term': email, 'fields': 'email', 'api_token': PIPEDRIVE_API_TOKEN}
    response = requests.get(url, params=params).json()
    items = response.get('data', {}).get('items', [])
    return items[0]['item'] if items else None

def create_person(name, email):
    url = f'{PIPEDRIVE_API_URL}/persons'
    payload = {'name': name, 'email': email, 'api_token': PIPEDRIVE_API_TOKEN}
    response = requests.post(url, json=payload).json()
    return response['data']

def create_deal(title, person_id):
    url = f'{PIPEDRIVE_API_URL}/deals'
    payload = {'title': title, 'person_id': person_id, 'api_token': PIPEDRIVE_API_TOKEN}
    response = requests.post(url, json=payload).json()
    return response['data']

def add_product_to_pipedrive(name, price):
    url = f'{PIPEDRIVE_API_URL}/products'
    payload = {'name': name, 'prices': [{'currency': 'EUR', 'price': price}], 'api_token': PIPEDRIVE_API_TOKEN}
    response = requests.post(url, json=payload).json()
    return response['data']

def attach_product_to_deal(deal_id, product_id, price):
    url = f'{PIPEDRIVE_API_URL}/deals/{deal_id}/products'
    payload = {'product_id': product_id, 'item_price': price, 'quantity': 1, 'api_token': PIPEDRIVE_API_TOKEN}
    requests.post(url, json=payload)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
