import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import io
from openpyxl import Workbook

# === 1. Função para gerar o Excel ===
def gerar_excel(df):
    """Cria um arquivo Excel em memória para download usando openpyxl."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Projetos_Consolidados")
    output.seek(0)
    return output

# === 2. Configuração do acesso à API do Notion ===
notion_token = "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"

# IDs das databases (tabelas)
database_ids = {
    "18f3a12b396281dd8ea9de22bc06609a": "MKT DE CONTEUDO",
    "18f3a12b3962807586a4ff9a03c973a1": "MKT DE PRODUTO",
    "1903a12b396280b7a0fecfbefa888f6c": "GROWTH",
    "1903a12b396280a19027fbe1b1fa09f6": "CONTEÚDO",
    "1903a12b396280e286c2ce0ff22e754f": "MÍDIA E PERFORMANCE",
    "1903a12b3962801b85b9def5ecafbdf7": "CX"
}

NOTION_URL = "https://api.notion.com/v1/databases/{}/query"
headers = {
    "Authorization": f"Bearer {notion_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# === 3. Extração dinâmica de valores ===
def extract_value(prop, prop_type):
    if prop is None:
        return "" if prop_type in ["title", "rich_text", "select", "multi_select", "formula", "date"] else 0

    if prop_type == "title":
        return " ".join(frag.get("text", {}).get("content", "") for frag in prop.get("title", []))

    elif prop_type == "rich_text":
        return " ".join(frag.get("text", {}).get("content", "") for frag in prop.get("rich_text", []))

    elif prop_type == "select":
        return prop.get("select", {}).get("name", "")

    elif prop_type == "multi_select":
        return ", ".join(item.get("name", "") for item in prop.get("multi_select", []))

    elif prop_type == "formula":
        formula_obj = prop.get("formula", {})
        return formula_obj.get(formula_obj.get("type", ""), "")

    elif prop_type == "number":
        return prop.get("number", 0)

    elif prop_type == "date":
        return prop.get("date", {}).get("start", "")

    return str(prop)

def extract_dynamic_value(prop):
    if not prop:
        return ""
    return extract_value(prop, prop.get("type"))

# === 4. Campos desejados ===
desired_fields_text = ["Name", "CATEGORIA", "TIPO", "CENTRO DE CUSTOS", "MARCA", "PILARES", "FIXO/VARIÁVEL"]
desired_fields_numeric = ["Jan/25", "Fev/25", "Mar/25", "Abr/25", "Mai/25",
                          "Jun/25", "Jul/25", "Ago/25", "Set/25", "Out/25",
                          "Nov/25", "Dez/25"]
desired_fields = desired_fields_text + desired_fields_numeric

# === 5. Coleta de dados da API ===
@st.cache_data
def carregar_dados_api():
    all_data = []

    for db_id, table_name in database_ids.items():
        has_more = True
        next_cursor = None

        while has_more:
            payload = {"page_size": 100}
            if next_cursor:
                payload["start_cursor"] = next_cursor

            try:
                response = requests.post(NOTION_URL.format(db_id), headers=headers, json=payload)
                if response.status_code != 200:
                    st.error(f"Erro na API para {table_name}: {response.text}")
                    return pd.DataFrame()

                data = response.json()
                results = data.get("results", [])

                for result in results:
                    properties = result.get("properties", {})
                    row = {"Área": table_name}
                    
                    for field in desired_fields:
                        row[field] = extract_dynamic_value(properties.get(field, {}))

                    all_data.append(row)

                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor", None)

            except Exception as e:
                st.error(f"Erro ao processar {table_name}: {e}")
                break

    if all_data:
        df = pd.DataFrame(all_data)

        # Converter colunas numéricas corretamente
        for col in desired_fields_numeric:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df["Total_Projeto"] = df[desired_fields_numeric].sum(axis=1)

        # Ordenação padrão (Exemplo: pelo campo "Name")
        df = df.sort_values(by="Name", ascending=True)

        return df
    else:
        return pd.DataFrame()

# === 6. Carregar os dados ===
df_dados = carregar_dados_api()

# === 7. Criar Dashboard no Streamlit ===
st.title("📊 Dashboard Financeiro - Projetos")

if df_dados.empty:
    st.warning("⚠️ Nenhum dado carregado da API! Verifique as configurações.")
    st.stop()

# === 8. Criando Filtros ===
with st.expander("🔍 Filtros", expanded=False):
    col1, col2, col3 = st.columns(3)
    filtro_area = col1.selectbox("Área", ["Todos"] + df_dados["Área"].dropna().unique().tolist())
    filtro_categoria = col2.selectbox("Categoria", ["Todos"] + df_dados["CATEGORIA"].dropna().unique().tolist())
    filtro_tipo = col3.selectbox("Tipo", ["Todos"] + df_dados["TIPO"].dropna().unique().tolist())

    col4, col5, col6 = st.columns(3)
    filtro_centro = col4.selectbox("Centro de Custos", ["Todos"] + df_dados["CENTRO DE CUSTOS"].dropna().unique().tolist())
    filtro_marca = col5.selectbox("Marca", ["Todos"] + df_dados["MARCA"].dropna().unique().tolist())
    filtro_pilares = col6.selectbox("Pilares", ["Todos"] + df_dados["PILARES"].dropna().unique().tolist())

    filtro_fixo = st.selectbox("Fixo/Variável", ["Todos"] + df_dados["FIXO/VARIÁVEL"].dropna().unique().tolist())

    

# === 9. Aplicação dos filtros ===
df_filtrado = df_dados.copy()

if filtro_area != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Área"] == filtro_area]
if filtro_categoria != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CATEGORIA"] == filtro_categoria]
if filtro_tipo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["TIPO"] == filtro_tipo]
if filtro_centro != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CENTRO DE CUSTOS"] == filtro_centro]
if filtro_marca != "Todos":
    df_filtrado = df_filtrado[df_filtrado["MARCA"] == filtro_marca]
if filtro_pilares != "Todos":
    df_filtrado = df_filtrado[df_filtrado["PILARES"] == filtro_pilares]
if filtro_fixo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["FIXO/VARIÁVEL"] == filtro_fixo]

# === 10. Exibição da Tabela ===
st.subheader("📋 Dados Filtrados")
st.data_editor(df_filtrado, use_container_width=True)

# === 11. Botão de Download do Excel ===
st.download_button(
    label="📥 Baixar Planilha (XLSX)",
    data=gerar_excel(df_filtrado),
    file_name="projetos_consolidados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
