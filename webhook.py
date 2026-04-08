from flask import Flask, request, jsonify
from database import add_or_update_cliente, init_db
from utils import (
    hoje_str,
    calcular_vigencia,
    identificar_plano,
    identificar_ciclo_por_valor,
)

app = Flask(__name__)

init_db()


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

        hoje = hoje_str()
        vigencia = calcular_vigencia(ciclo)

        if not email:
            return jsonify({
                "ok": False,
                "erro": "email não encontrado no payload"
            }), 400

        add_or_update_cliente(
            nome=nome,
            telefone=telefone,
            email=email,
            plano=plano,
            ciclo=ciclo,
            status="aguardando liberação",
            data_compra=hoje,
            ultimo_pagamento=hoje,
            vigencia_ate=vigencia,
            origem=None,
            regiao=None,
            telegram_id=None,
            validacao_documental="pendente" if plano == "vip" else None,
            data_liberacao=None,
            observacoes=None
        )

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


import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)