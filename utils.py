from datetime import datetime, timedelta


def hoje_str():
    return datetime.now().strftime("%Y-%m-%d")


def calcular_vigencia(ciclo: str) -> str:
    hoje = datetime.now()

    if ciclo == "mensal":
        return (hoje + timedelta(days=30)).strftime("%Y-%m-%d")

    if ciclo == "anual":
        return (hoje + timedelta(days=365)).strftime("%Y-%m-%d")

    return hoje.strftime("%Y-%m-%d")


def identificar_plano(product_name: str) -> str:
    nome = (product_name or "").lower()

    if "regional" in nome:
        return "regional"
    if "brasil" in nome:
        return "brasil"
    if "elite" in nome or "vip" in nome:
        return "vip"

    return "desconhecido"


def identificar_ciclo_por_valor(product_name: str, amount: float) -> str:
    nome = (product_name or "").lower()
    valor = round(float(amount or 0), 2)

    if "regional" in nome:
        if valor == 19.90:
            return "mensal"
        if valor == 219.00:
            return "anual"

    if "brasil" in nome:
        if valor == 23.90:
            return "mensal"
        if valor == 270.00:
            return "anual"

    if "elite" in nome or "vip" in nome:
        if valor == 39.90:
            return "mensal"
        if valor == 397.00:
            return "anual"

    return "desconhecido"