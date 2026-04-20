import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, GROUP_CONTROLE
from database import init_db
from handlers import (
    start,
    planos,
    cotacao,
    capturar_cotacao_controle,
    liberar,
    receber_email,
    status,
    id_handler,
    teste_regional,
    teste_balcao,
    escolher_origem,
    escolher_regiao,
    PEDINDO_EMAIL,
    ESCOLHENDO_ORIGEM,
    ESCOLHENDO_REGIAO,
)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Erro enquanto processava um update:", exc_info=context.error)


def main():
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("planos", planos))
    app.add_handler(CommandHandler("cotacao", cotacao))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("id", id_handler))
    app.add_handler(CommandHandler("teste_regional", teste_regional))
    app.add_handler(CommandHandler("teste_balcao", teste_balcao))
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/cotação(?:@[\w_]+)?$"),
            cotacao,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=GROUP_CONTROLE) & (filters.TEXT | filters.CAPTION),
            capturar_cotacao_controle,
        )
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("liberar", liberar)],
        states={
            PEDINDO_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_email)
            ],
            ESCOLHENDO_ORIGEM: [
                CallbackQueryHandler(escolher_origem, pattern="^origem:")
            ],
            ESCOLHENDO_REGIAO: [
                CallbackQueryHandler(escolher_regiao, pattern="^regiao:")
            ],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)

    print("Bot de acesso ATLAS PRIME rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
