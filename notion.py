import requests
import time

# === CONFIGURAÇÕES ===
NOTION_TOKEN = "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"  # Substitua pela sua chave da integração
DATABASE_ID = "1963a12b3962809da905d70ca43ec5a1"          # Substitua pelo ID da sua database

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# === FUNÇÃO PARA CRIAR UMA LINHA EM BRANCO ===
def criar_linha_em_branco():
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "ESTAB": {
                "title": [{"text": {"content": ""}}]
            },
            "UNID NEGÓCIOS": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "TITULO": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "FORNECEDOR": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "DATA": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "MÓDULO": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "CENTRO DE CUSTOS": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "VALOR": {
                "rich_text": [{"text": {"content": ""}}]
            },
            "DESCRIÇÃO": {
                "rich_text": [{"text": {"content": ""}}]
            }

        }
    }

    requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)

# === LOOP PARA CRIAR 2000 LINHAS EM BRANCO ===
for _ in range(400):
    criar_linha_em_branco()
    time.sleep(0.4)  # respeita o limite da API
