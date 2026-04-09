from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import (
    LINK_REGIONAL,
    LINK_BRASIL,
    LINK_VIP,
    GROUPS_REGIONAIS,
    GROUP_BALCAO,
)
from database import get_cliente_by_email, update_cliente_field
import requests

PEDINDO_EMAIL = 1
ESCOLHENDO_ORIGEM = 2
ESCOLHENDO_REGIAO = 3

ORIGENS_VALIDAS = [
    "Indicação",
    "WhatsApp",
    "Facebook",
    "YouTube",
    "Google",
    "Pinterest",
]

LOVABLE_WEBHOOK_URL = "https://atlas-prime-agency.lovable.app/functions/v1/bot-webhook"


def cliente_row_para_dict(cliente):
    return {
        "nome": cliente["nome"],
        "telefone": cliente["telefone"],
        "email": cliente["email"],
        "telegram_id": cliente["telegram_id"],
        "plano": cliente["plano"],
        "ciclo": cliente["ciclo"],
        "regiao": cliente["regiao"],
        "origem": cliente["origem"],
        "status": cliente["status"],
        "verificacao_documental": cliente["validacao_documental"],
        "data_compra": cliente["data_compra"],
        "ultimo_pagamento": cliente["ultimo_pagamento"],
        "vigencia_ate": cliente["vigencia_ate"],
        "data_liberacao": cliente["data_liberacao"],
        "observacoes": cliente["observacoes"],
    }


def enviar_para_crm(cliente):
    try:
        response = requests.post(
            LOVABLE_WEBHOOK_URL,
            json=cliente,
            timeout=20
        )
        print("CRM update response:", response.status_code, response.text)
        return True
    except Exception as e:
        print("Erro ao atualizar CRM pelo bot:", e)
        return False


def atualizar_cliente_no_crm_por_email(email):
    cliente = get_cliente_by_email(email)
    if not cliente:
        print("Cliente não encontrado para atualizar CRM:", email)
        return False

    payload = cliente_row_para_dict(cliente)
    return enviar_para_crm(payload)


async def responder(update_or_query, texto, reply_markup=None):
    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(texto, reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text(texto, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "Bem-vindo ao ATLAS PRIME.\n\n"
        "Comandos disponíveis:\n"
        "/planos - ver os planos\n"
        "/liberar - liberar seu acesso após a compra\n"
        "/status - consultar seu status\n"
        "/id - ver IDs\n"
        "/teste_regional - testar link de grupo regional\n"
        "/teste_balcao - testar link do balcão"
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
        "VIP: acesso completo + balcão + comunidade"
    )

    await update.message.reply_text(texto, reply_markup=reply_markup)


async def liberar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite o email usado na compra:")
    return PEDINDO_EMAIL


async def receber_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    cliente = get_cliente_by_email(email)

    if not cliente:
        await update.message.reply_text(
            "Não encontrei compra com esse email.\n"
            "Confira o email usado na compra ou acesse /planos."
        )
        return ConversationHandler.END

    telegram_id = update.effective_user.id
    update_cliente_field(email, "telegram_id", telegram_id)
    atualizar_cliente_no_crm_por_email(email)

    context.user_data["email_em_liberacao"] = email

    cliente = get_cliente_by_email(email)
    origem_atual = cliente["origem"]

    if not origem_atual:
        keyboard = [
            [InlineKeyboardButton("Indicação", callback_data="origem:Indicação")],
            [InlineKeyboardButton("WhatsApp", callback_data="origem:WhatsApp")],
            [InlineKeyboardButton("Facebook", callback_data="origem:Facebook")],
            [InlineKeyboardButton("YouTube", callback_data="origem:YouTube")],
            [InlineKeyboardButton("Google", callback_data="origem:Google")],
            [InlineKeyboardButton("Pinterest", callback_data="origem:Pinterest")],
        ]
        await update.message.reply_text(
            "Antes de liberar, me diga por onde você chegou até o ATLAS PRIME:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ESCOLHENDO_ORIGEM

    return await continuar_liberacao(update, context, email)


async def escolher_origem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    email = context.user_data.get("email_em_liberacao")
    if not email:
        await query.edit_message_text("Sessão expirada. Digite /liberar novamente.")
        return ConversationHandler.END

    origem = query.data.split("origem:", 1)[1]

    if origem not in ORIGENS_VALIDAS:
        await query.edit_message_text("Origem inválida. Digite /liberar novamente.")
        return ConversationHandler.END

    update_cliente_field(email, "origem", origem)
    atualizar_cliente_no_crm_por_email(email)

    await query.edit_message_text(f"Origem registrada: {origem}")

    return await continuar_liberacao(query, context, email)


async def continuar_liberacao(update_or_query, context: ContextTypes.DEFAULT_TYPE, email: str):
    cliente = get_cliente_by_email(email)

    if not cliente:
        await responder(update_or_query, "Cliente não encontrado.")
        return ConversationHandler.END

    plano = cliente["plano"]
    status = cliente["status"]

    if status not in ["ativo", "aguardando liberação", "aguardando validação"]:
        await responder(
            update_or_query,
            f"Seu cadastro foi encontrado, mas o status atual é: {status}."
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
            "Escolha sua região para liberar seu acesso:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ESCOLHENDO_REGIAO

    if plano == "brasil":
        grupos = GROUPS_REGIONAIS.values()
        links = []

        for group_id in grupos:
            invite = await context.bot.create_chat_invite_link(
                chat_id=group_id,
                member_limit=1
            )
            links.append(invite.invite_link)

        update_cliente_field(email, "data_liberacao", cliente["data_compra"])
        atualizar_cliente_no_crm_por_email(email)

        texto_links = "\n".join(links)

        await responder(
            update_or_query,
            "Aqui estão seus acessos aos grupos do plano Brasil:\n\n"
            f"{texto_links}"
        )
        return ConversationHandler.END

    if plano == "vip":
        update_cliente_field(email, "status", "aguardando validação")
        atualizar_cliente_no_crm_por_email(email)

        await responder(
            update_or_query,
            "Sua compra VIP foi localizada com sucesso.\n\n"
            "No próximo passo, você seguirá para a validação documental antes da liberação do balcão."
        )
        return ConversationHandler.END

    await responder(update_or_query, "Seu plano não foi reconhecido.")
    return ConversationHandler.END


async def escolher_regiao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    email = context.user_data.get("email_em_liberacao")
    if not email:
        await query.edit_message_text("Sessão expirada. Digite /liberar novamente.")
        return ConversationHandler.END

    regiao = query.data.split("regiao:", 1)[1]
    group_id = GROUPS_REGIONAIS.get(regiao)

    if not group_id:
        await query.edit_message_text("Região inválida.")
        return ConversationHandler.END

    update_cliente_field(email, "regiao", regiao)
    update_cliente_field(email, "data_liberacao", get_cliente_by_email(email)["data_compra"])
    atualizar_cliente_no_crm_por_email(email)

    invite = await context.bot.create_chat_invite_link(
        chat_id=group_id,
        member_limit=1
    )

    await query.edit_message_text(
        f"Região registrada: {regiao}.\n\n"
        f"Seu link de acesso é:\n{invite.invite_link}"
    )

    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    await update.message.reply_text(
        f"Seu Telegram ID é: {telegram_id}\n\n"
        "No próximo bloco, este comando vai mostrar seu plano, ciclo e vigência."
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
        member_limit=1
    )

    await update.message.reply_text(
        f"Teste de link do grupo {regiao}:\n{invite.invite_link}"
    )


async def teste_balcao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    invite = await context.bot.create_chat_invite_link(
        chat_id=GROUP_BALCAO,
        member_limit=1
    )

    await update.message.reply_text(
        f"Teste de link do balcão:\n{invite.invite_link}"
    )