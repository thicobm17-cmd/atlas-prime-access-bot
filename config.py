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
SUPORTE_TELEGRAM = os.getenv("SUPORTE_TELEGRAM", "")
VIP_WHATSAPP_LINK = os.getenv("VIP_WHATSAPP_LINK", "")
VIP_DOCUMENTOS_LINK = os.getenv("VIP_DOCUMENTOS_LINK", "")
BACKEND_JOB_TOKEN = os.getenv("BACKEND_JOB_TOKEN", "")

CRM_BASE_URL = os.getenv(
    "CRM_BASE_URL",
    "https://rubvdwpjundrwthfeewy.supabase.co"
)
CRM_TABLE_NAME = os.getenv("CRM_TABLE_NAME", "clientes")
CRM_ANON_TOKEN = os.getenv(
    "CRM_ANON_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1YnZkd3BqdW5kcnd0aGZlZXd5Iiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3NzU3NDU1NzEsImV4cCI6MjA5MTMyMTU3MX0."
    "SFx0jt3O2ilA1d7iG6M_CopdIQaersUO7TJ8iL9jZPY"
)
CRM_REST_URL = os.getenv(
    "CRM_REST_URL",
    f"{CRM_BASE_URL}/rest/v1/{CRM_TABLE_NAME}"
)
