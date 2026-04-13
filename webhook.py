from flask import Flask, request, jsonify
from database import add_or_update_cliente, init_db
from utils import (
    hoje_str,
    calcular_vigencia,
    identificar_plano,
    identificar_ciclo_por_valor,
)
import requests
import os

app = Flask(__name__)

init_db()

LOVABLE_WEBHOOK_URL = "https://rubvdwpjundrwthfeewy.supabase.co/functions/v1/bot-webhook"
LOVABLE_ANON_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1YnZkd3BqdW5kcnd0aGZlZXd5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3NDU1NzEsImV4cCI6MjA5MTMyMTU3MX0.SFx0jt3O2ilA1d7iG6M_CopdIQaersUO7TJ8iL9jZPY"


def mapear_plano_para_crm(plano):
    if plano == "regional":
        return "Plano Regional"
    if plano == "brasil":
        return "Plano Brasil"
    if plano == "vip":
        return "Plano VIP"
    return "Plano Regional"


def mapear_ciclo_para_crm(ciclo):
    if ciclo == "mensal":
        return "Mensal"
    if ciclo == "anual":
        return "Anual"
    return "Mensal"


def enviar_para_crm(cliente):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LOVABLE_ANON_TOKEN}"
    }

    try:
        response = requests.post(
            LOVABLE_WEBHOOK_URL,
            json=cliente,
            headers=headers,
            timeout=20
        )
        print("CRM response:", response.status_code, response.text)
        return True
    except Exception as e:
        print("Erro ao enviar para CRM:", e)
        return False


@app.route("/webhook/kiwify", methods=["POST"])
def webhook_kiwify():
    try:
        data = request.get_json(silent=True) or {}

        customer = data.get("Customer", {}) or data.get("customer", {}) or {}
        product = data.get("Product", {}) or data.get("product", {}) or {}
        subscription = data.get("Subscription", {}) or data.get("subscription", {}) or {}
        order = data.get("Order", {}) or data.get("order", {}) or {}

        nome = customer.get("full_name") or customer.get("name") or ""
        email = customer.get("email") or ""
        telefone = customer.get("mobile") or customer.get("phone") or ""

        product_name = product.get("name") or ""
        amount = (
            order.get("full_price")
            or order.get("price")
            or subscription.get("plan_price")
            or 0
        )

        try:
            amount = float(str(amount).replace(",", "."))
        except Exception:
            amount = 0.0

        plano = identificar_plano(product_name)
        ciclo = identificar_ciclo_por_valor(product_name, amount)

        data_compra = hoje_str()
        vigencia_ate = calcular_vigencia(ciclo)

        if not email:
            return jsonify({
                "ok": False,
                "erro": "email não encontrado no payload"
            }), 400

        status_inicial = "Aguardando validação" if plano == "vip" else "Aguardando liberação"
        verificacao_documental = "Pendente" if plano == "vip" else "Validado"

        add_or_update_cliente(
            nome=nome,
            telefone=telefone,
            email=email,
            plano=plano,
            ciclo=ciclo,
            status=status_inicial.lower(),
            data_compra=data_compra,
            ultimo_pagamento=data_compra,
            vigencia_ate=vigencia_ate,
            origem="kiwify",
            regiao=None,
            telegram_id=None,
            validacao_documental=verificacao_documental.lower(),
            data_liberacao=None,
            observacoes=None
        )

        cliente = {
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "telegram_id": "",
            "plano": mapear_plano_para_crm(plano),
            "ciclo": mapear_ciclo_para_crm(ciclo),
            "regiao": "",
            "origem": "Kiwify",
            "status": status_inicial,
            "verificacao_documental": verificacao_documental,
            "data_compra": data_compra,
            "ultimo_pagamento": data_compra,
            "vigencia_ate": vigencia_ate,
            "data_liberacao": "",
            "observacoes": ""
        }

        enviar_para_crm(cliente)

        return jsonify({
            "ok": True,
            "plano": plano,
            "ciclo": ciclo,
            "email": email
        }), 200

    except Exception as e:
        return jsonify({
            "ok": False,
            "erro": str(e)
        }), 500


@app.route("/", methods=["GET"])
def home():
    return "Webhook ATLAS PRIME online.", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)