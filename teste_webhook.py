import requests

url = "http://127.0.0.1:5000/webhook/kiwify"

payload = {
    "customer": {
        "name": "Thiago Bento",
        "email": "thiagoteste@email.com",
        "phone": "81999999999"
    },
    "product": {
        "name": "ATLAS PRIME Brasil – Acesso a Todas as Regiões"
    },
    "order": {
        "full_price": 23.90
    }
}

response = requests.post(url, json=payload)

print("Status code:", response.status_code)
print("Resposta:", response.text)