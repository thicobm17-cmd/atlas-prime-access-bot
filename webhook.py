from flask import Flask, request, jsonify
from database import add_or_update_cliente, init_db
from config import (
    CRM_REST_URL,
    CRM_ANON_TOKEN,
    TELEGRAM_BOT_TOKEN,
    GROUP_BALCAO,
    SUPORTE_TELEGRAM,
    BACKEND_JOB_TOKEN,
)
from utils import (
    hoje_str,
    calcular_vigencia,
    identificar_plano,
    identificar_ciclo_por_valor,
)
import requests
import os
import unicodedata

app = Flask(__name__)

init_db()

VIP_APROVACAO_MARKER = "[vip_aprovacao_enviada]"

def crm_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": CRM_ANON_TOKEN,
        "Authorization": f"Bearer {CRM_ANON_TOKEN}",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def normalizar_texto(valor):
    texto = (valor or "").strip().lower()
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def telegram_api_url(method):
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"


def requer_autorizacao_job(req):
    if not BACKEND_JOB_TOKEN:
        return True

    auth = req.headers.get("Authorization", "")
    esperado = f"Bearer {BACKEND_JOB_TOKEN}"
    return auth == esperado


def criar_link_balcao():
    response = requests.post(
        telegram_api_url("createChatInviteLink"),
        json={
            "chat_id": GROUP_BALCAO,
            "member_limit": 1,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Falha ao criar link do balcao: {data}")
    return data["result"]["invite_link"]


def montar_mensagem_aprovacao_vip(link_balcao):
    contato = (
        SUPORTE_TELEGRAM
        if SUPORTE_TELEGRAM
        else "suporte ainda nao configurado"
    )

    return (
        "Sua validacao foi concluida com sucesso.\n\n"
        "Seu acesso VIP foi aprovado e sua ativacao agora esta completa.\n\n"
        "Link de acesso ao balcao:\n"
        f"{link_balcao}\n\n"
        "Regras do Balcao de Milhas Atlas Prime\n\n"
        "1. O balcao e um ambiente exclusivo para clientes VIP com acesso ativo e validado.\n\n"
        "2. Este espaco foi criado para manter negociacoes e oportunidades de forma organizada, objetiva e segura entre os participantes.\n\n"
        "3. Sempre publique suas informacoes com clareza, incluindo programa, quantidade, valor e condicoes da operacao.\n\n"
        "4. Todas as negociacoes devem ser conduzidas com responsabilidade, transparencia e respeito.\n\n"
        "5. Nao serao permitidas mensagens enganosas, informacoes incompletas, spam, flood, repeticao excessiva ou qualquer conduta que prejudique o funcionamento do balcao.\n\n"
        "6. Assuntos que nao estejam relacionados ao objetivo do ambiente devem ser evitados.\n\n"
        "7. A Atlas Prime nao participa diretamente das negociacoes realizadas entre os membros e nao se responsabiliza por acordos firmados entre as partes.\n\n"
        "8. O uso de linguagem ofensiva, desrespeitosa ou qualquer comportamento inadequado podera resultar em advertencia, suspensao ou remocao do acesso.\n\n"
        "9. O acesso ao balcao pode ser cancelado a qualquer momento em caso de descumprimento das regras ou uso indevido do ambiente.\n\n"
        "10. Ao permanecer no balcao, o cliente declara estar ciente e de acordo com estas diretrizes.\n\n"
        "Se precisar de ajuda, suporte ou orientacao, fale comigo no Telegram:\n"
        f"{contato}\n\n"
        "Seja bem-vindo a Atlas Prime."
    )


def enviar_mensagem_telegram(chat_id, texto):
    response = requests.post(
        telegram_api_url("sendMessage"),
        json={
            "chat_id": chat_id,
            "text": texto,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Falha ao enviar mensagem no Telegram: {data}")
    return data["result"]


def listar_vips_aprovados_no_crm():
    response = requests.get(
        CRM_REST_URL,
        headers=crm_headers(),
        params={
            "plano": "eq.vip",
            "select": "*",
            "limit": "200",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def atualizar_cliente_crm(email, campos):
    response = requests.patch(
        CRM_REST_URL,
        headers=crm_headers(),
        params={
            "email": f"eq.{email.lower()}",
        },
        json=campos,
        timeout=20,
    )
    response.raise_for_status()
    return response.ok


def observacoes_com_marker(observacoes):
    texto = (observacoes or "").strip()
    if VIP_APROVACAO_MARKER in texto:
        return texto
    if not texto:
        return VIP_APROVACAO_MARKER
    return f"{texto} {VIP_APROVACAO_MARKER}"


def cliente_vip_pronto_para_notificar(cliente):
    status = normalizar_texto(cliente.get("status_cliente") or cliente.get("status"))
    verificacao = normalizar_texto(cliente.get("verificacao_documental"))
    telegram_id = str(cliente.get("telegram_id") or "").strip()
    observacoes = cliente.get("observacoes") or ""

    if normalizar_texto(cliente.get("plano")) != "vip":
        return False
    if status != "ativo":
        return False
    if verificacao != "validado":
        return False
    if not telegram_id:
        return False
    if VIP_APROVACAO_MARKER in observacoes:
        return False
    return True


def processar_notificacoes_vip_aprovado():
    clientes = listar_vips_aprovados_no_crm()
    enviados = []
    ignorados = []
    erros = []

    for cliente in clientes:
        email = (cliente.get("email") or "").lower()
        if not cliente_vip_pronto_para_notificar(cliente):
            ignorados.append(email)
            continue

        try:
            link_balcao = criar_link_balcao()
            mensagem = montar_mensagem_aprovacao_vip(link_balcao)
            enviar_mensagem_telegram(cliente["telegram_id"], mensagem)
            atualizar_cliente_crm(
                email,
                {
                    "observacoes": observacoes_com_marker(cliente.get("observacoes")),
                },
            )
            enviados.append(email)
        except Exception as e:
            erros.append({
                "email": email,
                "erro": str(e),
            })

    return {
        "enviados": enviados,
        "ignorados": ignorados,
        "erros": erros,
    }


def enviar_para_crm(cliente):
    try:
        payload = {
            "nome": cliente.get("nome") or "",
            "telefone": cliente.get("telefone") or "",
            "email": (cliente.get("email") or "").lower(),
            "telegram_id": cliente.get("telegram_id") or "",
            "plano": cliente.get("plano") or "",
            "ciclo": cliente.get("ciclo") or "",
            "origem": cliente.get("origem") or "",
            "status_cliente": cliente.get("status_cliente") or "",
            "verificacao_documental": cliente.get("verificacao_documental") or "",
            "data_compra": cliente.get("data_compra") or "",
            "ultimo_pagamento": cliente.get("ultimo_pagamento") or "",
            "vigencia_ate": cliente.get("vigencia_ate") or "",
            "data_liberacao": cliente.get("data_liberacao") or "",
            "observacoes": cliente.get("observacoes") or "",
        }

        if cliente.get("regiao"):
            payload["regiao"] = cliente["regiao"]

        response = requests.post(
            f"{CRM_REST_URL}?on_conflict=email",
            json=payload,
            headers=crm_headers(),
            timeout=20
        )
        print("CRM response:", response.status_code, response.text)
        return response.ok
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
            "plano": plano,
            "ciclo": ciclo,
            "origem": "Kiwify",
            "status_cliente": status_inicial,
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


@app.route("/jobs/notificar-vips-aprovados", methods=["POST"])
def job_notificar_vips_aprovados():
    if not requer_autorizacao_job(request):
        return jsonify({
            "ok": False,
            "erro": "nao autorizado"
        }), 401

    try:
        resultado = processar_notificacoes_vip_aprovado()
        return jsonify({
            "ok": True,
            "resultado": resultado,
        }), 200
    except Exception as e:
        return jsonify({
            "ok": False,
            "erro": str(e),
        }), 500


@app.route("/", methods=["GET"])
def home():
    return "Webhook ATLAS PRIME online.", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
