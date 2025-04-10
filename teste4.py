import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import io
from openpyxl import Workbook
import datetime

# === 1. Função para gerar o Excel ===
st.set_page_config(layout="wide")

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
    "18f3a12b396281dd8ea9de22bc06609a": "MKT DE CONTEÚDO",
    "18f3a12b3962807586a4ff9a03c973a1": "MKT DE PRODUTO",
    "1903a12b396280b7a0fecfbefa888f6c": "GROWTH",
    "1903a12b396280a19027fbe1b1fa09f6": "CONTEÚDO",
    "1903a12b396280e286c2ce0ff22e754f": "MÍDIA E PERFORMANCE",
    "1903a12b3962801b85b9def5ecafbdf7": "CX",
    "1963a12b3962809ab3f2d7bc93c259fb": "2024"  
}

REALIZADO_2025_ID = "1d03a12b396280569b55e2d2ba8f2ce4"



NOTION_URL = "https://api.notion.com/v1/databases/{}/query"
headers = {
    "Authorization": f"Bearer {notion_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}


# === 3. Função para extrair valores dinâmicos ===
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
        number = prop.get("number")
        return number if isinstance(number, (int, float)) else 0


    elif prop_type == "date":
        return prop.get("date", {}).get("start", "")

    return str(prop)

def extract_dynamic_value(prop):
    if not prop:
        return ""
    return extract_value(prop, prop.get("type"))

# === 4. Campos desejados ===
desired_fields_text = ["PROJETOS 2025", "CATEGORIA", "TIPO", "CENTRO DE CUSTOS", "MARCA", "PILARES", "FIXO/VARIÁVEL"]
desired_fields_numeric = ["Jan/25", "Fev/25", "Mar/25", "Abr/25", "Mai/25",
                        "Jun/25", "Jul/25", "Ago/25", "Set/25", "Out/25",
                        "Nov/25", "Dez/25"]

desired_fields_numeric_2024 = ["Jan/24", "Fev/24", "Mar/24", "Abr/24", "Mai/24",
                               "Jun/24", "Jul/24", "Ago/24", "Set/24", "Out/24",
                               "Nov/24", "Dez/24"]

desired_fields = desired_fields_text + desired_fields_numeric 

# === 5. Coleta de dados da API ===
@st.cache_data
def carregar_dados_api():
    all_data = []

    for db_id, table_name in database_ids.items():
        has_more = True
        next_cursor = None  # ✅ Adicionado aqui
        if table_name == "2024":
            continue

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

                    # Seleciona os campos corretos para cada base
                    if table_name == "2024":
                        campos_numericos = desired_fields_numeric_2024
                    else:
                        campos_numericos = desired_fields_numeric

                    campos = desired_fields_text + campos_numericos

                    for field in campos:
                        prop = properties.get(field, {})
                        tipo = prop.get("type", "")

                        if tipo == "title":
                            row[field] = " ".join([t["text"]["content"] for t in prop.get("title", [])])
                        elif tipo == "rich_text":
                            row[field] = " ".join([t["text"]["content"] for t in prop.get("rich_text", [])])
                        elif tipo == "select":
                            row[field] = prop.get("select", {}).get("name", "")
                        elif tipo == "multi_select":
                            row[field] = ", ".join([item.get("name", "") for item in prop.get("multi_select", [])])
                        elif tipo == "date":
                            row[field] = prop.get("date", {}).get("start", "")
                        elif tipo == "number":
                            value = prop.get("number")
                            row[field] = value if isinstance(value, (int, float)) else 0
                        elif tipo == "formula":
                            formula = prop.get("formula", {})
                            value = formula.get(formula.get("type", ""), 0)
                            row[field] = value if isinstance(value, (int, float)) else 0
                        else:
                            row[field] = ""

                    all_data.append(row)

                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor", None)

            except Exception as e:
                st.error(f"Erro ao processar {table_name}: {e}")
                break

    if all_data:
        df = pd.DataFrame(all_data)

        # Converter colunas numéricas corretamente
        for col in desired_fields_numeric + desired_fields_numeric_2024:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Criar a coluna de total se possível
        colunas_soma = [col for col in desired_fields_numeric + desired_fields_numeric_2024 if col in df.columns]
        if colunas_soma:
            df["Total_Projeto"] = df[colunas_soma].sum(axis=1)

        if "PROJETOS 2025" in df.columns:
            df = df.sort_values(by="PROJETOS 2025", ascending=True)

        return df
    else:
        return pd.DataFrame()
    
# === 6. Carregar os dados ===
df_dados = carregar_dados_api()


st.title("Dashboard Financeiro - Projetos")
# === 8. Sidebar para Seleção da Área com Radio Button ===
abas_visiveis = [nome for nome in database_ids.values() if nome != "PROJETOS 2025"]
area_selecionada = st.sidebar.radio("Escolha a Área", options=["Todos"] + abas_visiveis + ["Calendário de Projetos"])

def carregar_database_notion(database_id):
    dados = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        response = requests.post(NOTION_URL.format(database_id), headers=headers, json=payload)
        data = response.json()
        results = data.get("results", [])

        for result in results:
            properties = result.get("properties", {})
            linha = {}
            for k, v in properties.items():
                tipo = v.get("type")
                if tipo == "title":
                    linha[k] = " ".join([t["text"]["content"] for t in v["title"]])
                elif tipo == "rich_text":
                    linha[k] = " ".join([t["text"]["content"] for t in v["rich_text"]])
                elif tipo == "select":
                    linha[k] = v["select"]["name"] if v["select"] else ""
                elif tipo == "number":
                    linha[k] = v.get("number", 0)
                elif tipo == "date":
                    linha[k] = v.get("date", {}).get("start", "")
                else:
                    linha[k] = ""
            dados.append(linha)

        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)

    return pd.DataFrame(dados)

# Carregar dados de todas as bases de planejamento (exceto 2024)
dfs_planejado = []
for db_id, nome_base in database_ids.items():
    if nome_base == "2024":
        continue  # pula a base 2024

    df_temp = carregar_database_notion(db_id)
    df_temp["Área"] = nome_base
    dfs_planejado.append(df_temp)

df_planejado = pd.concat(dfs_planejado, ignore_index=True)
df_realizado = carregar_database_notion(REALIZADO_2025_ID)
df_realizado["Área"] = "Todos"  # Adiciona a coluna faltante

ORCAMENTO_2025_ID = "1d13a12b396280d69b2ff63228e2b0bf"
df_orcamento_2025 = carregar_database_notion(ORCAMENTO_2025_ID)

@st.cache_data
def carregar_base_2024():
    df_2024 = carregar_database_notion("1963a12b3962809ab3f2d7bc93c259fb")
    df_2024["Área"] = "2024"

    df_2024.columns = [col.strip().replace(" ", "") if "/24" in col else col for col in df_2024.columns]

    for col in desired_fields_text:
        if col not in df_2024.columns:
            df_2024[col] = ""

    for col in desired_fields_numeric_2024:
        if col in df_2024.columns:
            df_2024[col] = pd.to_numeric(df_2024[col], errors="coerce").fillna(0)
        else:
            df_2024[col] = 0

    return df_2024

# === 6. Selecionar colunas com segurança ===
def selecionar_colunas_existentes(df, meses):
    colunas_base = ["Área"] + desired_fields_text
    colunas_existentes = [col for col in colunas_base + meses if col in df.columns]
    return df[colunas_existentes]

if area_selecionada == "2024":
    df_dados_area = carregar_base_2024()
else:
    df_dados_area = df_dados[df_dados["Área"] == area_selecionada].copy() if area_selecionada != "Todos" else df_dados[df_dados["Área"] != "2024"].copy()

# Aplica filtro final de segurança para remover 2024, mesmo que tenha vindo da origem por erro
df_dados_area = df_dados_area[df_dados_area["Área"] != "2024"]

with st.expander("🔍 Filtros", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    if area_selecionada == "Todos":
        areas_disponiveis = sorted(df_planejado["Área"].dropna().unique())
        areas_disponiveis = [a for a in areas_disponiveis if a != "2024"]
    else:
        areas_disponiveis = [area_selecionada]

    filtro_area = col1.selectbox("Área", ["Todos"] + areas_disponiveis)

    if "CATEGORIA" in df_dados_area.columns:
        filtro_categoria = st.selectbox("Categoria", ["Todos"] + sorted(df_dados_area["CATEGORIA"].dropna().unique()))
    else:
        filtro_categoria = "Todos"

    if "TIPO" in df_dados_area.columns:
        filtro_tipo = col3.selectbox("Tipo", ["Todos"] + sorted(df_dados_area["TIPO"].dropna().unique()) if "TIPO" in df_dados_area.columns else ["Todos"])
    else:
        filtro_tipo = "Todos"

    col4, col5, col6 = st.columns(3)

    if "CENTRO DE CUSTOS" in df_dados_area.columns:
        filtro_centro = col4.selectbox("Centro de Custos", ["Todos"] + sorted(df_dados_area["CENTRO DE CUSTOS"].dropna().unique()))
    else:
        filtro_centro = "Todos"

    if "MARCA" in df_dados_area.columns:
        filtro_marca = col5.selectbox("Marca", ["Todos"] + sorted(df_dados_area["MARCA"].dropna().unique()))
    else:
        filtro_marca = "Todos"

    if "PILARES" in df_dados_area.columns:
        filtro_pilares = col6.selectbox("Pilares", ["Todos"] + sorted(df_dados_area["PILARES"].dropna().unique()))
    else:
        filtro_pilares = "Todos"

    if "FIXO/VARIÁVEL" in df_dados_area.columns:
        filtro_fixo = st.selectbox("Fixo/Variável", ["Todos"] + sorted(df_dados_area["FIXO/VARIÁVEL"].dropna().unique()))
    else:
        filtro_fixo = "Todos"

    meses_disponiveis = desired_fields_numeric_2024 if area_selecionada == "2024" else desired_fields_numeric
    meses_selecionados = st.multiselect("📅 Selecione os meses", meses_disponiveis, default=meses_disponiveis[:12])
# Aplicar filtros nos dataframes

df_filtrado_planejado = df_planejado.copy()
if filtro_area != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["Área"] == filtro_area]
if filtro_categoria != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["CATEGORIA"] == filtro_categoria]
if filtro_tipo != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["TIPO"] == filtro_tipo]
if filtro_centro != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["CENTRO DE CUSTOS"] == filtro_centro]
if filtro_marca != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["MARCA"] == filtro_marca]
if filtro_pilares != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["PILARES"] == filtro_pilares]
if filtro_fixo != "Todos":
    df_filtrado_planejado = df_filtrado_planejado[df_filtrado_planejado["FIXO/VARIÁVEL"] == filtro_fixo]

df_dados_area = df_dados_area[df_dados_area["Área"] != "2024"]


if filtro_area == "Todos":
    df_dados_area = df_dados_area[df_dados_area["Área"] != "2024"]
# Criação do consolidado filtrado dos planejados
df_filtrado = df_filtrado_planejado.copy()

if area_selecionada == "2024":
    meses_disponiveis = desired_fields_numeric_2024
else:
    meses_disponiveis = desired_fields_numeric

# Realizado

df_filtrado_realizado = df_realizado.copy()
if filtro_fixo != "Todos" and "FIXO/VARIÁVEL" in df_filtrado_realizado.columns:
    df_filtrado_realizado = df_filtrado_realizado[df_filtrado_realizado["FIXO/VARIÁVEL"] == filtro_fixo]

# Gráficos comparativos (apenas na aba "Todos")
if area_selecionada == "Todos" and filtro_area == "Todos" and not df_filtrado_planejado.empty and not df_filtrado_realizado.empty:

    meses_ordem = meses_selecionados
    ordem_meses = {m: i for i, m in enumerate(meses_ordem)}


    for tipo_custo in ["Fixo", "Variável"]:
        st.subheader(f"Evolução Mensal de Gastos Planejados - {tipo_custo}")

        df_filtro = df_filtrado_planejado[df_filtrado_planejado["FIXO/VARIÁVEL"] == tipo_custo]
        df_barras = df_filtro.melt(
            id_vars=["CATEGORIA"],
            value_vars=[col for col in df_filtro.columns if col in meses_ordem],
            var_name="MÊS",
            value_name="Planejado"
        ).groupby(["MÊS", "CATEGORIA"])["Planejado"].sum().reset_index()

        df_realizado_match = df_filtrado_realizado.melt(
            id_vars=["TÍTULO"] if "TÍTULO" in df_filtrado_realizado.columns else None,
            value_vars=[col for col in df_filtrado_realizado.columns if col in meses_ordem],
            var_name="MÊS",
            value_name="Realizado"
        ).groupby("MÊS", as_index=False)["Realizado"].sum()

        df_total_planejado = df_barras.groupby("MÊS")["Planejado"].sum().reset_index()

        df_total_planejado["ordem"] = df_total_planejado["MÊS"].map(ordem_meses)
        df_realizado_match["ordem"] = df_realizado_match["MÊS"].map(ordem_meses)

        df_total_planejado = df_total_planejado.sort_values("ordem")
        df_realizado_match = df_realizado_match.sort_values("ordem")
        df_merge = pd.merge(df_total_planejado.drop(columns=["ordem"]),
                            df_realizado_match.drop(columns=["ordem"]),
                            on="MÊS", how="left")
        df_merge["Realizado"] = pd.to_numeric(df_merge["Realizado"], errors="coerce").fillna(0)

        
        fig = px.bar(df_barras, x="MÊS", y="Planejado", color="CATEGORIA",
                     title=f"{tipo_custo} - Planejado por Categoria", barmode="relative",
                     category_orders={"MÊS": meses_ordem})
        fig.add_scatter(
            x=df_merge["MÊS"],
            y=df_merge["Realizado"],
            mode="lines+markers",  # linha + pontos
            name="Realizado",
            line=dict(color="#2F4F4F", width=4),  # linha contínua e mais grossa
            marker=dict(size=7, color="black")  # pontos pretos
        )
        fig.update_layout(
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            legend_title="Legenda"
        )

        st.plotly_chart(fig, use_container_width=True)

    orcado_2025_id = "1d13a12b396280d69b2ff63228e2b0bf"
    df_orcado = carregar_database_notion(orcado_2025_id)

    # Converte colunas para numérico
    for col in desired_fields_numeric:
        if col in df_orcado.columns:
            df_orcado[col] = pd.to_numeric(df_orcado[col], errors="coerce").fillna(0)
        if col in df_realizado.columns:
            df_realizado[col] = pd.to_numeric(df_realizado[col], errors="coerce").fillna(0)

    # Soma por mês
    df_orcado_melt = df_orcado.melt(value_vars=desired_fields_numeric, var_name="Mês", value_name="Orçado")
    df_orcado_melt = df_orcado_melt.groupby("Mês", as_index=False).sum()

    df_realizado_melt = df_realizado.melt(value_vars=desired_fields_numeric, var_name="Mês", value_name="Realizado")
    df_realizado_melt = df_realizado_melt.groupby("Mês", as_index=False).sum()

    # Ordena meses
    ordem_meses = {m: i for i, m in enumerate(desired_fields_numeric)}
    df_realizado_melt["ordem"] = df_realizado_melt["Mês"].map(ordem_meses)
    df_orcado_melt["ordem"] = df_orcado_melt["Mês"].map(ordem_meses)

    df_realizado_melt = df_realizado_melt.sort_values("ordem")
    df_orcado_melt = df_orcado_melt.sort_values("ordem")

    st.subheader("Ano Atual YTD - Real X Planejado")
    # Gráfico
    fig_comp = px.bar(
        df_realizado_melt,
        x="Mês",
        y="Realizado",
        title="Realizado X Orçado - 2025",
        labels={"Realizado": "Valor (R$)"}
    )

    # Atualiza a cor das barras depois da criação
    fig_comp.update_traces(marker_color="#00008B")

    # Adiciona a linha do orçamento
    fig_comp.add_scatter(
        x=df_orcado_melt["Mês"],
        y=df_orcado_melt["Orçado"],
        mode="lines+markers",
        name="Orçado",
        line=dict(color="orange", width=3, dash="dot"),
        marker=dict(size=6, color="orange"),
        fill="tozeroy",  # 👉 isso adiciona o preenchimento até o zero
        fillcolor="rgba(255,165,3.5)"  # cor laranja com transparência
    )

    fig_comp.update_layout(
        xaxis_title="Mês",
        yaxis_title="Total (R$)",
        legend_title="Legenda"
    )

    st.plotly_chart(fig_comp, use_container_width=True)

    # === Cálculo de variação percentual do mês atual ===
    meses_map = {
        "Jan": "Jan/25",
        "Feb": "Fev/25",
        "Mar": "Mar/25",
        "Apr": "Abr/25",
        "May": "Mai/25",
        "Jun": "Jun/25",
        "Jul": "Jul/25",
        "Aug": "Ago/25",
        "Sep": "Set/25",
        "Oct": "Out/25",
        "Nov": "Nov/25",
        "Dec": "Dez/25"
    }

    # Obtem mês atual no formato correto
    mes_ingles = datetime.datetime.today().strftime("%b")
    mes_atual = meses_map.get(mes_ingles)

    if mes_atual in desired_fields_numeric:
        valor_realizado_mes = df_realizado[mes_atual].sum()
        valor_orcado_mes = df_orcado[mes_atual].sum()

        if valor_orcado_mes > 0:
            variacao_percentual = ((valor_realizado_mes - valor_orcado_mes) / valor_orcado_mes) * 100
        else:
            variacao_percentual = 0

        if valor_realizado_mes > valor_orcado_mes:
            texto_variacao = f"📈 {variacao_percentual:.2f}% acima do orçado"
            cor_delta = "normal"
        else:
            texto_variacao = f"📉 {abs(variacao_percentual):.2f}% abaixo do orçado"
            cor_delta = "inverse"

        st.metric(
            label=f"Diferença Realizado x Orçado ({mes_atual})",
            value=f"R$ {valor_realizado_mes:,.2f}",
            delta=texto_variacao,
            delta_color=cor_delta
        )
    else:
        st.warning(f"❗ O mês atual ({mes_atual}) não está disponível nos dados.")
        
# 👉 Exibe os componentes apenas se NÃO for a aba "Calendário de Projetos"
if area_selecionada not in ["Calendário de Projetos", "2024"]:
    colunas_existentes = ["Área"] + desired_fields_text + [col for col in meses_selecionados if col in df_filtrado.columns]
    df_filtrado = df_filtrado[colunas_existentes]

    st.subheader(f"Detalhamento por Área: {area_selecionada}")

    if area_selecionada not in ["Todos", "Calendário de Projetos"]:
        df_filtrado = df_filtrado[df_filtrado["Área"] == area_selecionada]

# Oculta a coluna "PROJETOS 2025" apenas na aba 2024
    if area_selecionada == "2024" and "PROJETOS 2025" in df_filtrado.columns:
        df_filtrado = df_filtrado.drop(columns=["PROJETOS 2025"])

    st.data_editor(df_filtrado, use_container_width=True)

    colunas_validas = ["Área"] + [m for m in meses_selecionados if m in df_filtrado.columns]
    df_gastos_mensais = df_filtrado[colunas_validas].set_index("Área").sum(axis=0)

    st.download_button(
        label="📥 Baixar Planilha (XLSX)",
        data=gerar_excel(df_filtrado),
        file_name="projetos_consolidados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    id_vars = ["Área", "CATEGORIA"]
    if "PROJETOS 2025" in df_filtrado.columns:
        id_vars.append("PROJETOS 2025")

    # 🔁 Realiza o melt com os campos corretos
    meses_existentes = [m for m in meses_selecionados if m in df_filtrado.columns]

    df_long = df_filtrado.melt(
        id_vars=[col for col in id_vars if col in df_filtrado.columns],
        value_vars=meses_existentes,
        var_name="Data",
        value_name="Valor"
    )

    if "PROJETOS 2025" in df_long.columns:
        df_long["Projeto_Área"] = df_long["PROJETOS 2025"] + " - " + df_long["Área"]
    else:
        df_long["Projeto_Área"] = df_long["Área"]

    # Gráfico com cor por CATEGORIA e tooltip detalhado
    fig = px.bar(
        df_long,
        x="Data",
        y="Valor",
        color="CATEGORIA",
        labels={"Data": "Mês", "Valor": "Custo (R$)", "CATEGORIA": "Categoria"},
        title=f"Evolução dos Valores por Categoria - {area_selecionada}",
        hover_data=["CATEGORIA", "Data", "Valor", "Projeto_Área"] 
    )

    fig.update_layout(barmode="relative")  # mantém as barras empilhadas
    st.plotly_chart(fig, use_container_width=True)

    if area_selecionada not in ["2024", "Calendário de Projetos"]:
        # Agrupar por PROJETOS 2025 e Área
        df_ranking = df_long.groupby(["PROJETOS 2025", "Área"]).agg({"Valor": "sum"}).reset_index()

        # Remover projetos em branco
        df_ranking = df_ranking[df_ranking["PROJETOS 2025"] != ""]

        # Criar campo combinando Projeto + Área
        df_ranking["Projeto_Área"] = df_ranking["PROJETOS 2025"] + " - " + df_ranking["Área"]

        # Ordenar do maior para o menor e limitar ao Top 10
        df_ranking = df_ranking.sort_values(by="Valor", ascending=False).head(10)

        # Criar gráfico
        fig_ranking = px.bar(
            df_ranking,
            x="Valor",
            y="Projeto_Área",
            orientation="h",
            title="Maiores Projetos Planejados 2025",
            labels={"Projeto_Área": "Projeto e Área", "Valor": "Custo Total (R$)"}
        )

        fig_ranking.update_traces(marker_color="lightblue", texttemplate='R$ %{x:,.2f}', textposition="inside")
        fig_ranking.update_layout(yaxis=dict(autorange="reversed"))

        # Exibir gráfico
        st.plotly_chart(fig_ranking, use_container_width=True)


if area_selecionada == "Calendário de Projetos":
    # Função para carregar os dados de feriados da API
    notion_database_id = "1983a12b3962803d9b92f07238715e09"

    # === Função para Buscar a Tabela do Notion ===
    colunas_ordenadas = ["PROJETO", "JAN", "FEV", "MAR", "ABR", "MAI", "JUN", 
                        "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

    # === Função para Buscar a Tabela do Notion ===
    @st.cache_data
    def carregar_tabela_notion():
        try:
            response = requests.post(NOTION_URL.format(notion_database_id), headers=headers)
            data = response.json()

            if response.status_code != 200:
                st.error(f"Erro na API: {response.text}")
                return pd.DataFrame()

            results = data.get("results", [])

            registros = []
            for index, result in enumerate(results):  # Captura a ordem original
                properties = result.get("properties", {})

                # Criar um dicionário para armazenar os valores da linha
                linha = {"Ordem_Notion": index}  # Índice numérico para ordenar

                for key, value in properties.items():
                    if "title" in value:
                        linha[key] = " ".join([t["text"]["content"] for t in value["title"]])
                    elif "rich_text" in value:
                        linha[key] = " ".join([t["text"]["content"] for t in value["rich_text"]])
                    elif "select" in value:
                        linha[key] = value["select"]["name"] if value["select"] else ""
                    elif "multi_select" in value:
                        linha[key] = ", ".join([item["name"] for item in value["multi_select"]])
                    elif "number" in value:
                        linha[key] = value["number"]
                    elif "date" in value:
                        linha[key] = value["date"]["start"] if value["date"] else ""
                    else:
                        linha[key] = ""

                registros.append(linha)

            df = pd.DataFrame(registros)

            # ✅ Garantir que a coluna "PROJETO" seja a primeira e manter os meses na ordem correta
            colunas_existentes = [col for col in colunas_ordenadas if col in df.columns]
            df = df[colunas_existentes + ["Ordem_Notion"]]  # Mantém a coluna de ordenação temporária

            # ✅ FORÇAR a ordem original dos projetos do Notion
            df = df.sort_values(by="Ordem_Notion", ascending=True).drop(columns=["Ordem_Notion"])

            return df

        except Exception as e:
            st.error(f"Erro ao buscar os dados do Notion: {e}")
            return pd.DataFrame()

    # === Criar Nova Página no Dashboard ===
    st.title("Calendário de Projetos")

    df_tabela = carregar_tabela_notion()

    if not df_tabela.empty:
        st.dataframe(df_tabela, use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado ou erro ao carregar a tabela.")

@st.cache_data
def carregar_dados_2024_completo():
    dados = []
    notion_geral_id = "1963a12b3962809ab3f2d7bc93c259fb"
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        response = requests.post(NOTION_URL.format(notion_geral_id), headers=headers, json=payload)
        if response.status_code != 200:
            st.error(f"Erro na API (Tabela Geral): {response.text}")
            return pd.DataFrame()

        data = response.json()
        for result in data.get("results", []):
            properties = result.get("properties", {})
            linha = {}
            for k, v in properties.items():
                tipo = v.get("type")
                if tipo == "title":
                    linha[k] = " ".join([t["text"]["content"] for t in v["title"]])
                elif tipo == "rich_text":
                    linha[k] = " ".join([t["text"]["content"] for t in v["rich_text"]])
                elif tipo == "number":
                    linha[k] = v.get("number", 0)
                elif tipo == "select":
                    linha[k] = v.get("select", {}).get("name", "")
                elif tipo == "multi_select":
                    linha[k] = ", ".join([item["name"] for item in v.get("multi_select", [])])
                elif tipo == "date":
                    linha[k] = v.get("date", {}).get("start", "")
                else:
                    linha[k] = ""
            dados.append(linha)

        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)

    return pd.DataFrame(dados)


if area_selecionada == "2024":
    st.title("Retroátivo - Realizado 2024")

    df_geral = carregar_dados_2024_completo()

    if "EMPRESA" not in df_geral.columns:
        df_geral["EMPRESA"] = ""

    if not df_geral.empty:
        # Padroniza nomes de colunas
        df_geral.columns = [col.strip() for col in df_geral.columns]

        # Converte colunas numéricas
        for col in desired_fields_numeric_2024:
            if col in df_geral.columns:
                df_geral[col] = pd.to_numeric(df_geral[col], errors="coerce").fillna(0)

        # Cria a coluna de total
        df_geral["Total"] = df_geral[[col for col in desired_fields_numeric_2024 if col in df_geral.columns]].sum(axis=1)
        df_geral = df_geral.sort_values(by="Total", ascending=False)

        # Remove a coluna PROJETOS 2025 se existir
        if "PROJETOS 2025" in df_geral.columns:
            df_geral = df_geral.drop(columns=["PROJETOS 2025"])

        # Ordena as colunas
        ordem_colunas = ["EMPRESA"] + [col for col in desired_fields_text if col in df_geral.columns] + desired_fields_numeric_2024 + ["Total"]
        df_geral = df_geral[[col for col in ordem_colunas if col in df_geral.columns]]

        st.data_editor(df_geral, use_container_width=True)

        df_melt_2024 = df_geral.melt(
            id_vars=["CATEGORIA"] if "CATEGORIA" in df_geral.columns else [],
            value_vars=desired_fields_numeric_2024,
            var_name="Mês",
            value_name="Valor"
        )

        # ➕ Cria gráfico de barras empilhadas
        fig_2024 = px.bar(
            df_melt_2024,
            x="Mês",
            y="Valor",
            color="CATEGORIA" if "CATEGORIA" in df_melt_2024.columns else None,
            barmode="relative",
            title="📈 Evolução dos Valores por Categoria - 2024",
            labels={"Valor": "Custo (R$)"}
        )

        # ➕ Personalizações (opcional)
        fig_2024.update_layout(
            xaxis_title="Mês",
            yaxis_title="Custo (R$)",
            legend_title="Categoria"
        )

        # ➕ Exibe o gráfico
        st.plotly_chart(fig_2024, use_container_width=True)
    else:
        st.warning("⚠️ Nenhum dado encontrado na tabela geral.")

    # 🔹 2. Top 10 Empresas
    st.subheader("Serviços Contratados com Maior Custo Agregado - 2024")

    notion_top10_id = "1b43a12b3962800c99d1d813c9f6f5d1"
    response_top10 = requests.post(NOTION_URL.format(notion_top10_id), headers=headers)

    if response_top10.status_code == 200:
        data_top10 = response_top10.json()

        if "results" in data_top10 and len(data_top10["results"]) > 0:
            registros = []
            for item in data_top10["results"]:
                properties = item.get("properties", {})
                empresa = ""
                empresa_prop = properties.get("EMPRESA", {})
                if "rich_text" in empresa_prop:
                    empresa = " ".join([t["text"]["content"] for t in empresa_prop["rich_text"] if "text" in t])

                total_anual = 0
                for mes in ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]:
                    prop = properties.get(mes, {})
                    if prop.get("type") == "number" and prop.get("number") is not None:
                        total_anual += prop["number"]

                if empresa and total_anual > 0:
                    registros.append({"EMPRESA": empresa, "Total Anual": total_anual})

            df_top10 = pd.DataFrame(registros)
            df_top10 = df_top10.sort_values(by="Total Anual", ascending=False).head(10)

            st.data_editor(df_top10, use_container_width=True)

            st.write(f"**Total dos Gastos**: **R$ {df_top10['Total Anual'].sum():,.2f}**")

            fig_top10 = px.bar(
                df_top10,
                x="Total Anual",
                y="EMPRESA",
                orientation="h",
                text=df_top10["Total Anual"].apply(lambda x: f"R$ {x:,.2f}"),
                title="Principais Gastos 2024",
                labels={"EMPRESA": "Empresa", "Total Anual": "Custo Total Anual (R$)"}
            )
            fig_top10.update_traces(marker_color="lightskyblue", textposition="inside")
            fig_top10.update_layout(yaxis=dict(autorange="reversed"))

            st.plotly_chart(fig_top10, use_container_width=True)
        else:
            st.warning("⚠️ A API não retornou dados para o Top 10.")
    else:
        st.error(f"Erro na API (Top 10): {response_top10.status_code}")
        st.write(response_top10.text)