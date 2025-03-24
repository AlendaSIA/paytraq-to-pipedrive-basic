from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Pipedrive API konfigurācija
api_token = "7f1dec3f4a486b427cedac03293c65053def753b"
base_url = "https://api.pipedrive.com/v1"

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    deal_name = data.get("name")

    if not deal_name or not deal_name.startswith("test"):
        return jsonify({"message": "Darījums nav test!"}), 400

    # Meklējam klientu pēc e-pasta
    email = data.get("email", "raivis.zvejnieks@gmail.com")
    search_url = f"{base_url}/persons/search"
    params = {
        "term": email,
        "fields": "email",
        "api_token": api_token
    }
    response = requests.get(search_url, params=params)
    results = response.json()

    if results['success'] and results['data']['items']:
        clients = [item['item'] for item in results['data']['items']]
        client = min(clients, key=lambda x: x['id'])
        person_id = client['id']

        # Izveidojam Deal
        deal_url = f"{base_url}/deals?api_token={api_token}"
        deal_data = {
            "title": deal_name,
            "person_id": person_id,
            "value": 2.00,
            "currency": "EUR"
        }
        deal_response = requests.post(deal_url, json=deal_data)
        deal_result = deal_response.json()

        if deal_result['success']:
            deal_id = deal_result['data']['id']

            # Meklējam produktu pēc koda
            product_code = "testa11"
            product_search_url = f"{base_url}/products/search"
            params = {
                "term": product_code,
                "fields": "code",
                "api_token": api_token
            }
            product_response = requests.get(product_search_url, params=params)
            product_result = product_response.json()

            if product_result['success'] and product_result['data']['items']:
                product = product_result['data']['items'][0]['item']
                product_id = product['id']

                # Pievienojam produktu Deal
                add_product_url = f"{base_url}/deals/{deal_id}/products?api_token={api_token}"
                product_data = {
                    "product_id": int(product_id),
                    "item_price": 2.00,
                    "quantity": 1
                }
                add_product_response = requests.post(add_product_url, json=product_data)
                return jsonify({"message": "Deal izveidots un produkts pievienots!"})

    return jsonify({"message": "Kaut kas nogāja greizi!"}), 500

@app.route("/", methods=["GET"])
def health_check():
    return "Service running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
