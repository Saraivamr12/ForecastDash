import requests
import pandas as pd

# === 1. Configuração do acesso à API do Notion ===
notion_token = "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"

# IDs das databases (tabelas)
database_ids = [
    "18f3a12b396281dd8ea9de22bc06609a",  # Tabela A
    "18f3a12b3962807586a4ff9a03c973a1",  # Tabela B
    "1903a12b396280b7a0fecfbefa888f6c",  # Tabela C
    "1903a12b396280a19027fbe1b1fa09f6",  # Tabela D
    "1903a12b396280e286c2ce0ff22e754f",  # Tabela E
    "1903a12b3962801b85b9def5ecafbdf7"   # Tabela F
]

# Mapeamento dos IDs para nomes amigáveis (opcional)
database_names = {
    "18f3a12b396281dd8ea9de22bc06609a": "Tabela A",
    "18f3a12b3962807586a4ff9a03c973a1": "Tabela B",
    "1903a12b396280b7a0fecfbefa888f6c": "Tabela C",
    "1903a12b396280a19027fbe1b1fa09f6": "Tabela D",
    "1903a12b396280e286c2ce0ff22e754f": "Tabela E",
    "1903a12b3962801b85b9def5ecafbdf7": "Tabela F"
}

NOTION_URL = "https://api.notion.com/v1/databases/{}/query"
headers = {
    "Authorization": f"Bearer {notion_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# === 2. Função de extração dinâmica baseada no tipo retornado pela API ===
def extract_value(prop, prop_type):
    """
    Dada uma propriedade (objeto retornado pela API) e seu tipo,
    extrai o valor de forma consistente.
    """
    if prop is None:
        return "" if prop_type in ["title", "rich_text", "select", "multi_select", "formula", "date"] else 0

    if prop_type == "title":
        textos = [frag.get("text", {}).get("content", "") for frag in prop.get("title", [])]
        return " ".join(textos).strip() if textos else ""
    
    elif prop_type == "rich_text":
        textos = [frag.get("text", {}).get("content", "") for frag in prop.get("rich_text", [])]
        return " ".join(textos).strip() if textos else ""
    
    elif prop_type == "select":
        select_obj = prop.get("select")
        return select_obj.get("name", "") if select_obj else ""
    
    elif prop_type == "multi_select":
        multi = prop.get("multi_select", [])
        return ", ".join([item.get("name", "") for item in multi])
    
    elif prop_type == "formula":
        formula_obj = prop.get("formula")
        if formula_obj:
            if formula_obj.get("type") == "string":
                return formula_obj.get("string", "")
            elif formula_obj.get("type") == "number":
                return formula_obj.get("number", 0)
            elif formula_obj.get("type") == "boolean":
                return str(formula_obj.get("boolean", ""))
        return ""
    
    elif prop_type == "number":
        return prop.get("number", 0)
    
    elif prop_type == "date":
        date_obj = prop.get("date")
        return date_obj.get("start", "") if date_obj else ""
    
    # Se o tipo não for reconhecido, retorna o objeto convertido para string
    return str(prop)

def extract_dynamic_value(prop):
    """
    Usa o campo "type" presente no objeto da propriedade para extrair seu valor.
    """
    if not prop:
        return ""
    ptype = prop.get("type")
    return extract_value(prop, ptype)

# === 3. Definição dos Campos Desejados ===
# Liste os nomes das propriedades conforme aparecem nas suas databases.
# (Os nomes devem ser exatamente iguais – case-sensitive)
desired_fields_text = [
    "Name",             # Nome do Projeto
    "PROJETOS 2025",    # Outra forma de nome, se existir
    "CATEGORIA",        # Observe: verifique se o nome realmente é esse
    "TIPO",
    "CENTRO DE CUSTOS",
    "MARCA",
    "PILARES",
    "FIXO/VARIÁVEL"
]
desired_fields_numeric = [
    "Jan/25", "Fev/25", "Mar/25", "Abr/25", "Mai/25",
    "Jun/25", "Jul/25", "Ago/25", "Set/25", "Out/25",
    "Nov/25", "Dez/25"
]
desired_fields = desired_fields_text + desired_fields_numeric

# === 4. Coleta dos Dados via API (com paginação) ===
all_data = []

for db_id in database_ids:
    table_name = database_names.get(db_id, db_id)
    print(f"\nProcessando {table_name}...")
    has_more = True
    next_cursor = None
    total_records = 0

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        try:
            response = requests.post(NOTION_URL.format(db_id), headers=headers, json=payload)
            if response.status_code != 200:
                print(f"Erro em {table_name}: {response.status_code} - {response.text}")
                break

            data = response.json()
            results = data.get("results", [])
            total_records += len(results)
            print(f"Obtidos {len(results)} registros; total acumulado: {total_records}")

            for result in results:
                properties = result.get("properties", {})
                row = {"Tabela": table_name}
                for field in desired_fields:
                    if field in properties:
                        row[field] = extract_dynamic_value(properties[field])
                    else:
                        # Se for campo numérico, preenche com 0; caso contrário, com string vazia
                        row[field] = 0 if field in desired_fields_numeric else ""
                all_data.append(row)

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor", None)
            print("has_more:", has_more)

        except Exception as e:
            print(f"Exceção em {table_name}: {e}")
            break

    print(f"Total de registros coletados em {table_name}: {total_records}")

# === 5. Criação do DataFrame, Ordenação e Exportação para Excel ===
if all_data:
    df = pd.DataFrame(all_data)

    # Converte as colunas numéricas
    for col in desired_fields_numeric:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Ordena – aqui usamos o campo "Tabela" e, se existir, "Name" (ou "PROJETOS 2025")
    sort_col = "Name" if "Name" in df.columns else "PROJETOS 2025"
    df = df.sort_values(by=["Tabela", sort_col])

    # Exporta para Excel
    output_file = "orçamento_2025.xlsx"
    df.to_excel(output_file, index=False)
    print("\n✅ Dados exportados para", output_file)
    print(df)
else:
    print("Nenhum dado foi coletado!")
