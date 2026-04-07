import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

LINK_REGIONAL = os.getenv("LINK_REGIONAL")
LINK_BRASIL = os.getenv("LINK_BRASIL")
LINK_VIP = os.getenv("LINK_VIP")

GROUPS_REGIONAIS = {
    "norte": int(os.getenv("GROUP_NORTE", "-1000000000001")),
    "nordeste": int(os.getenv("GROUP_NORDESTE", "-1000000000002")),
    "centro-oeste": int(os.getenv("GROUP_CENTRO_OESTE", "-1000000000003")),
    "sudeste": int(os.getenv("GROUP_SUDESTE", "-1000000000004")),
    "sul": int(os.getenv("GROUP_SUL", "-1000000000005")),
}

GROUP_CONTROLE = int(os.getenv("GROUP_CONTROLE", "-1000000000006"))
GROUP_BALCAO = int(os.getenv("GROUP_BALCAO", "-1000000000007"))