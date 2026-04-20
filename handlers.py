from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from pathlib import Path
import json
from config import (
    LINK_REGIONAL,
    LINK_BRASIL,
    LINK_VIP,
    GROUP_CONTROLE,
    GROUPS_REGIONAIS,
    GROUP_BALCAO,
    SUPORTE_TELEGRAM,
    VIP_WHATSAPP_LINK,
    VIP_DOCUMENTOS_LINK,
    CRM_REST_URL,
    CRM_ANON_TOKEN,
)
from database import add_or_update_cliente, get_cliente_by_email
import requests
import unicodedata

PEDINDO_EMAIL = 1
ESCOLHENDO_ORIGEM = 2
ESCOLHENDO_REGIAO = 3
QUOTATION_CACHE_FILE = Path(__file__).resolve().with_name("quotation_cache.json")

ORIGENS_VALIDAS = [
    "Indicacao",
    "WhatsApp",
    "Facebook",
    "YouTube",
    "Google",
    "Pinterest",
]

STATUS_PERMITIDOS = {
    "ativo",
    "aguardando liberacao",
    "aguardando validacao",
    "aguardando_liberacao",
    "aguardando_validacao",
}


def normalizar_plano(plano):
    valor = (plano or "").strip().lower()

    if "regional" in valor:
        return "regional"
    if "brasil" in valor:
        return "brasil"
    if "vip" in valor or "elite" in valor:
        return "vip"

    return valor


def normalizar_ciclo(ciclo):
    valor = (ciclo or "").strip().lower()

    if "mensal" in valor:
        return "mensal"
    if "anual" in valor:
        return "anual"

    return valor


def normalizar_status(status):
    valor = (status or "").strip().lower()
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caractere)
    )


def normalizar_texto_livre(texto):
    valor = (texto or "").strip().lower()
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(caractere)
    )


def extrair_trecho_cotacao(texto):
    if not texto:
        return None

    linhas = [linha.rstrip() for linha in texto.splitlines()]
    inicio = None
    fim = None

    for indice, linha in enumerate(linhas):
        linha_normalizada = normalizar_texto_livre(linha)
        if inicio is None and "dia anterior" in linha_normalizada:
            inicio = indice
        if "avianca" in linha_normalizada:
            fim = indice

    if inicio is None or fim is None or fim < inicio:
        return None

    trecho = "\n".join(linha for linha in linhas[inicio:fim + 1] if linha.strip())
    return trecho.strip() or None


def mensagem_parece_cotacao(texto):
    texto_normalizado = normalizar_texto_livre(texto)
    return (
        "dia anterior" in texto_normalizado
        and "avianca" in texto_normalizado
        and "latam" in texto_normalizado
    )


def salvar_cotacao_cache(payload):
    QUOTATION_CACHE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def carregar_cotacao_cache():
    if not QUOTATION_CACHE_FILE.exists():
        return None

    try:
        return json.loads(QUOTATION_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def montar_texto_cotacao(cache):
    trecho = cache.get("quotation_text") or ""
    return (
        "Cotacao media mais recente registrada no Atlas Prime Controle.\n\n"
        f"{trecho}"
    )


def crm_headers(prefer=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": CRM_ANON_TOKEN,
        "Authorization": f"Bearer {CRM_ANON_TOKEN}",
    }

    if prefer:
        headers["Prefer"] = prefer

    return headers


def cliente_row_para_dict(cliente):
    return {
        "nome": cliente["nome"] if cliente["nome"] is not None else "",
        "telefone": cliente["telefone"] if cliente["telefone"] is not None else "",
        "email": (cliente["email"] or "").lower(),
        "telegram_id": cliente["telegram_id"],
        "plano": normalizar_plano(cliente["plano"]),
        "ciclo": normalizar_ciclo(cliente["ciclo"]),
        "regiao": cliente["regiao"] if cliente["regiao"] is not None else "",
        "origem": cliente["origem"] if cliente["origem"] is not None else "",
        "status": normalizar_status(cliente["status"]),
        "validacao_documental": (
            cliente["validacao_documental"]
            if cliente["validacao_documental"] is not None else ""
        ),
        "data_compra": cliente["data_compra"] if cliente["data_compra"] is not None else "",
        "ultimo_pagamento": (
            cliente["ultimo_pagamento"]
            if cliente["ultimo_pagamento"] is not None else ""
        ),
        "vigencia_ate": cliente["vigencia_ate"] if cliente["vigencia_ate"] is not None else "",
        "data_liberacao": (
            cliente["data_liberacao"]
            if cliente["data_liberacao"] is not None else ""
        ),
        "observacoes": cliente["observacoes"] if cliente["observacoes"] is not None else "",
    }


def cliente_crm_para_dict(cliente):
    return {
        "nome": cliente.get("nome") or "",
        "telefone": cliente.get("telefone") or "",
        "email": (cliente.get("email") or "").lower(),
        "telegram_id": cliente.get("telegram_id"),
        "plano": normalizar_plano(cliente.get("plano")),
        "ciclo": normalizar_ciclo(cliente.get("ciclo")),
        "regiao": cliente.get("regiao") or "",
        "origem": cliente.get("origem") or "",
        "status": normalizar_status(
            cliente.get("status_cliente") or cliente.get("status")
        ),
        "validacao_documental": (
            cliente.get("validacao_documental")
            or cliente.get("verificacao_documental")
            or ""
        ).strip().lower(),
        "data_compra": cliente.get("data_compra") or "",
        "ultimo_pagamento": cliente.get("ultimo_pagamento") or "",
        "vigencia_ate": cliente.get("vigencia_ate") or "",
        "data_liberacao": cliente.get("data_liberacao") or "",
        "observacoes": cliente.get("observacoes") or "",
    }


def cliente_dict_para_crm(cliente):
    payload = {
        "nome": cliente.get("nome") or "",
        "telefone": cliente.get("telefone") or "",
        "email": (cliente.get("email") or "").lower(),
        "telegram_id": cliente.get("telegram_id"),
        "plano": cliente.get("plano") or "",
        "ciclo": cliente.get("ciclo") or "",
        "origem": cliente.get("origem") or "",
        "status_cliente": cliente.get("status") or "",
        "verificacao_documental": cliente.get("validacao_documental") or "",
        "data_compra": cliente.get("data_compra") or "",
        "ultimo_pagamento": cliente.get("ultimo_pagamento") or "",
        "vigencia_ate": cliente.get("vigencia_ate") or "",
        "data_liberacao": cliente.get("data_liberacao") or "",
        "observacoes": cliente.get("observacoes") or "",
    }

    regiao = cliente.get("regiao")
    if regiao:
        payload["regiao"] = regiao

    return payload


def espelhar_cliente_no_sqlite(cliente):
    if not cliente or not cliente.get("email"):
        return

    add_or_update_cliente(
        nome=cliente.get("nome") or "",
        telefone=cliente.get("telefone") or "",
        email=cliente["email"],
        plano=cliente.get("plano") or "",
        ciclo=cliente.get("ciclo") or "",
        status=cliente.get("status") or "",
        data_compra=cliente.get("data_compra") or "",
        ultimo_pagamento=cliente.get("ultimo_pagamento") or "",
        vigencia_ate=cliente.get("vigencia_ate") or "",
        origem=cliente.get("origem") or "",
        regiao=cliente.get("regiao") or "",
        telegram_id=cliente.get("telegram_id"),
        validacao_documental=cliente.get("validacao_documental") or "",
        data_liberacao=cliente.get("data_liberacao") or "",
        observacoes=cliente.get("observacoes") or "",
    )


def buscar_cliente_no_crm(email):
    try:
        response = requests.get(
            CRM_REST_URL,
            headers=crm_headers(),
            params={
                "email": f"eq.{email.lower()}",
                "select": "*",
                "limit": "1",
            },
            timeout=20,
        )
        print("CRM fetch response:", response.status_code, response.text)

        if not response.ok:
            return None

        data = response.json()
        if not data:
            return None

        cliente = cliente_crm_para_dict(data[0])
        espelhar_cliente_no_sqlite(cliente)
        return cliente
    except Exception as e:
        print("Erro ao buscar cliente no CRM:", e)
        return None


def enviar_para_crm(cliente):
    try:
        payload = cliente_dict_para_crm(cliente)
        response = requests.post(
            f"{CRM_REST_URL}?on_conflict=email",
            json=payload,
            headers=crm_headers("resolution=merge-duplicates,return=representation"),
            timeout=20,
        )
        print("CRM update response:", response.status_code, response.text)

        if response.ok:
            data = response.json()
            if data:
                espelhar_cliente_no_sqlite(cliente_crm_para_dict(data[0]))
            else:
                espelhar_cliente_no_sqlite(cliente)
            return True

        return False
    except Exception as e:
        print("Erro ao atualizar CRM pelo bot:", e)
        return False


def buscar_cliente_principal_por_email(email):
    cliente_crm = buscar_cliente_no_crm(email)
    if cliente_crm:
        return cliente_crm

    cliente_local = get_cliente_by_email(email)
    if not cliente_local:
        return None

    cliente = cliente_row_para_dict(cliente_local)
    espelhar_cliente_no_sqlite(cliente)
    return cliente


def salvar_cliente(cliente):
    if not cliente or not cliente.get("email"):
        return False

    espelhar_cliente_no_sqlite(cliente)
    return enviar_para_crm(cliente)


async def gerar_links_grupos_alerta(context: ContextTypes.DEFAULT_TYPE):
    links = []

    for group_id in GROUPS_REGIONAIS.values():
        invite = await context.bot.create_chat_invite_link(
            chat_id=group_id,
            member_limit=1,
        )
        links.append(invite.invite_link)

    return links


def montar_orientacao_vip(links_alerta):
    texto_links = "\n".join(links_alerta)

    if VIP_WHATSAPP_LINK:
        whatsapp_texto = f"Comunidade WhatsApp VIP:\n{VIP_WHATSAPP_LINK}"
    else:
        whatsapp_texto = "Comunidade WhatsApp VIP:\nlink pendente de configuracao."

    if VIP_DOCUMENTOS_LINK:
        documentos_texto = f"Envio de documentos:\n{VIP_DOCUMENTOS_LINK}"
    else:
        documentos_texto = "Envio de documentos:\nlink pendente de configuracao."

    return (
        "Sua compra VIP foi localizada com sucesso.\n\n"
        "Seus links dos grupos de alerta de passagens estao abaixo:\n"
        f"{texto_links}\n\n"
        "Proximos passos:\n"
        f"1. Entre em todos os grupos de alerta acima.\n"
        f"2. {whatsapp_texto}\n"
        f"3. {documentos_texto}\n"
        "4. Apos a validacao documental, o acesso ao balcao sera liberado."
    )


def montar_contato_suporte():
    if SUPORTE_TELEGRAM:
        return (
            "Se precisar de ajuda, suporte ou orientacao em qualquer etapa, "
            f"fale comigo no Telegram:\n{SUPORTE_TELEGRAM}"
        )

    return (
        "Se precisar de ajuda, suporte ou orientacao em qualquer etapa, "
        "o contato de suporte no Telegram ainda nao foi configurado."
    )


def montar_texto_regional_inicial():
    return (
        "Parabens por escolher a Atlas Prime.\n\n"
        "Sua compra foi confirmada com sucesso. A partir de agora, voce tera "
        "acesso aos alertas da sua regiao, com uma estrutura pensada para "
        "acompanhar oportunidades de forma mais organizada, rapida e pratica.\n\n"
        "Para concluir sua liberacao, selecione abaixo a regiao que deseja "
        "acompanhar. Assim que voce escolher, seu link de acesso sera enviado em "
        "seguida.\n\n"
        f"{montar_contato_suporte()}\n\n"
        "Seja bem-vindo a Atlas Prime."
    )


def montar_texto_regional_final(regiao, link):
    return (
        "Regiao registrada com sucesso.\n\n"
        "Seu acesso ao grupo da regiao escolhida esta abaixo:\n"
        f"{link}\n\n"
        f"{montar_contato_suporte()}\n\n"
        "Seja bem-vindo a Atlas Prime."
    )


def montar_texto_brasil(links):
    texto_links = "\n".join(links)
    return (
        "Parabens por escolher a Atlas Prime.\n\n"
        "Sua compra foi confirmada com sucesso. Voce agora faz parte de uma "
        "estrutura criada para acompanhar oportunidades em escala nacional, com "
        "mais alcance, organizacao e agilidade no acesso as informacoes.\n\n"
        "Seus acessos aos grupos de alerta de passagens:\n"
        f"{texto_links}\n\n"
        "Entre nos grupos acima para comecar a acompanhar as oportunidades.\n\n"
        f"{montar_contato_suporte()}\n\n"
        "Seja bem-vindo a Atlas Prime."
    )


def montar_texto_vip(links_alerta):
    return (
        "Parabens por escolher a Atlas Prime.\n\n"
        "Sua compra VIP foi confirmada com sucesso. Voce acaba de entrar em uma "
        "estrutura pensada para quem quer acompanhar oportunidades com mais "
        "organizacao, agilidade e suporte.\n\n"
        "Seus acessos iniciais aos grupos de alerta de passagens:\n"
        f"{chr(10).join(links_alerta)}\n\n"
        "Para concluir sua ativacao VIP, siga estas etapas:\n"
        f"1. Entre nos grupos de alerta.\n"
        f"2. {'Acesse a comunidade exclusiva no WhatsApp:\\n' + VIP_WHATSAPP_LINK if VIP_WHATSAPP_LINK else 'Acesse a comunidade exclusiva no WhatsApp:\\nlink pendente de configuracao.'}\n"
        f"3. {'Envie sua documentacao para validacao:\\n' + VIP_DOCUMENTOS_LINK if VIP_DOCUMENTOS_LINK else 'Envie sua documentacao para validacao:\\nlink pendente de configuracao.'}\n\n"
        "A liberacao do balcao sera concluida apos a validacao documental.\n\n"
        f"{montar_contato_suporte()}\n\n"
        "Seja bem-vindo a Atlas Prime."
    )


async def responder(update_or_query, texto, reply_markup=None):
    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(texto, reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text(texto, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "Bem-vindo ao ATLAS PRIME.\n\n"
        "Comandos disponiveis:\n"
        "/planos - ver os planos\n"
        "/liberar - liberar seu acesso apos a compra\n"
        "/cotacao - consultar a cotacao media mais recente\n"
        "/status - consultar seu status\n"
        "/id - ver IDs\n"
        "/teste_regional - testar link de grupo regional\n"
        "/teste_balcao - testar link do balcao"
    )
    await update.message.reply_text(texto)


async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Plano Regional", url=LINK_REGIONAL)],
        [InlineKeyboardButton("Plano Brasil", url=LINK_BRASIL)],
        [InlineKeyboardButton("Plano VIP", url=LINK_VIP)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "Escolha seu plano:\n\n"
        "Regional: acesso a 1 grupo de alerta\n"
        "Brasil: acesso a todos os grupos\n"
        "VIP: acesso completo + balcao + comunidade"
    )

    await update.message.reply_text(texto, reply_markup=reply_markup)


async def cotacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cache = carregar_cotacao_cache()
    if not cache or not cache.get("quotation_text"):
        await update.message.reply_text(
            "Ainda nao tenho uma cotacao media registrada no momento."
        )
        return

    await update.message.reply_text(montar_texto_cotacao(cache))


async def capturar_cotacao_controle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or update.effective_chat.id != GROUP_CONTROLE:
        return

    texto = message.text or message.caption or ""
    if not texto or not mensagem_parece_cotacao(texto):
        return

    trecho = extrair_trecho_cotacao(texto)
    if not trecho:
        return

    payload = {
        "message_id": message.message_id,
        "chat_id": update.effective_chat.id,
        "quotation_text": trecho,
    }
    salvar_cotacao_cache(payload)


async def liberar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite o email usado na compra:")
    return PEDINDO_EMAIL


async def receber_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    cliente = buscar_cliente_principal_por_email(email)

    if not cliente:
        await update.message.reply_text(
            "Nao encontrei compra com esse email.\n"
            "Confira o email usado na compra ou acesse /planos."
        )
        return ConversationHandler.END

    cliente["telegram_id"] = update.effective_user.id
    salvar_cliente(cliente)

    context.user_data["email_em_liberacao"] = email

    if not cliente.get("origem"):
        keyboard = [
            [InlineKeyboardButton("Indicacao", callback_data="origem:Indicacao")],
            [InlineKeyboardButton("WhatsApp", callback_data="origem:WhatsApp")],
            [InlineKeyboardButton("Facebook", callback_data="origem:Facebook")],
            [InlineKeyboardButton("YouTube", callback_data="origem:YouTube")],
            [InlineKeyboardButton("Google", callback_data="origem:Google")],
            [InlineKeyboardButton("Pinterest", callback_data="origem:Pinterest")],
        ]
        await update.message.reply_text(
            "Antes de liberar, me diga por onde voce chegou ate o ATLAS PRIME:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ESCOLHENDO_ORIGEM

    return await continuar_liberacao(update, context, email)


async def escolher_origem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    email = context.user_data.get("email_em_liberacao")
    if not email:
        await query.edit_message_text("Sessao expirada. Digite /liberar novamente.")
        return ConversationHandler.END

    origem = query.data.split("origem:", 1)[1]

    if origem not in ORIGENS_VALIDAS:
        await query.edit_message_text("Origem invalida. Digite /liberar novamente.")
        return ConversationHandler.END

    cliente = buscar_cliente_principal_por_email(email)
    if not cliente:
        await query.edit_message_text("Cliente nao encontrado. Digite /liberar novamente.")
        return ConversationHandler.END

    cliente["origem"] = origem
    salvar_cliente(cliente)

    await query.edit_message_text(f"Origem registrada: {origem}")

    return await continuar_liberacao(query, context, email)


async def continuar_liberacao(update_or_query, context: ContextTypes.DEFAULT_TYPE, email: str):
    cliente = buscar_cliente_principal_por_email(email)

    if not cliente:
        await responder(update_or_query, "Cliente nao encontrado.")
        return ConversationHandler.END

    plano = normalizar_plano(cliente.get("plano"))
    status = normalizar_status(cliente.get("status"))

    if status not in STATUS_PERMITIDOS:
        await responder(
            update_or_query,
            f"Seu cadastro foi encontrado, mas o status atual e: {status}."
        )
        return ConversationHandler.END

    if plano == "regional":
        keyboard = [
            [InlineKeyboardButton("Norte", callback_data="regiao:norte")],
            [InlineKeyboardButton("Nordeste", callback_data="regiao:nordeste")],
            [InlineKeyboardButton("Centro-Oeste", callback_data="regiao:centro-oeste")],
            [InlineKeyboardButton("Sudeste", callback_data="regiao:sudeste")],
            [InlineKeyboardButton("Sul", callback_data="regiao:sul")],
        ]

        await responder(
            update_or_query,
            montar_texto_regional_inicial(),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ESCOLHENDO_REGIAO

    if plano == "brasil":
        links = await gerar_links_grupos_alerta(context)

        cliente["data_liberacao"] = cliente.get("data_compra") or cliente.get("data_liberacao") or ""
        salvar_cliente(cliente)

        await responder(
            update_or_query,
            montar_texto_brasil(links)
        )
        return ConversationHandler.END

    if plano == "vip":
        cliente["status"] = "aguardando validacao"
        cliente["data_liberacao"] = cliente.get("data_compra") or cliente.get("data_liberacao") or ""
        salvar_cliente(cliente)
        links = await gerar_links_grupos_alerta(context)

        await responder(
            update_or_query,
            montar_texto_vip(links)
        )
        return ConversationHandler.END

    await responder(update_or_query, "Seu plano nao foi reconhecido.")
    return ConversationHandler.END


async def escolher_regiao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    email = context.user_data.get("email_em_liberacao")
    if not email:
        await query.edit_message_text("Sessao expirada. Digite /liberar novamente.")
        return ConversationHandler.END

    regiao = query.data.split("regiao:", 1)[1]
    group_id = GROUPS_REGIONAIS.get(regiao)

    if not group_id:
        await query.edit_message_text("Regiao invalida.")
        return ConversationHandler.END

    cliente = buscar_cliente_principal_por_email(email)
    if not cliente:
        await query.edit_message_text("Cliente nao encontrado. Digite /liberar novamente.")
        return ConversationHandler.END

    cliente["regiao"] = regiao
    cliente["data_liberacao"] = cliente.get("data_compra") or cliente.get("data_liberacao") or ""
    salvar_cliente(cliente)

    invite = await context.bot.create_chat_invite_link(
        chat_id=group_id,
        member_limit=1,
    )

    await query.edit_message_text(
        montar_texto_regional_final(regiao, invite.invite_link)
    )

    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    await update.message.reply_text(
        f"Seu Telegram ID e: {telegram_id}\n\n"
        "No proximo bloco, este comando vai mostrar seu plano, ciclo e vigencia."
    )


async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    texto = (
        f"Chat ID: {chat_id}\n"
        f"Seu Telegram ID: {user_id}"
    )

    await update.message.reply_text(texto)


async def teste_regional(update: Update, context: ContextTypes.DEFAULT_TYPE):
    regiao = "nordeste"
    group_id = GROUPS_REGIONAIS[regiao]

    invite = await context.bot.create_chat_invite_link(
        chat_id=group_id,
        member_limit=1,
    )

    await update.message.reply_text(
        f"Teste de link do grupo {regiao}:\n{invite.invite_link}"
    )


async def teste_balcao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    invite = await context.bot.create_chat_invite_link(
        chat_id=GROUP_BALCAO,
        member_limit=1,
    )

    await update.message.reply_text(
        f"Teste de link do balcao:\n{invite.invite_link}"
    )
