import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp

# Configurações iniciais
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")
st.title("📊 Dashboard Financeiro")

# Função para carregar e processar as abas relevantes
@st.cache_data
def carregar_dados(arquivo_excel, abas_relevantes):
    dfs = []
    for aba in abas_relevantes:
        df = pd.read_excel(arquivo_excel, sheet_name=aba, header=1)

        # Renomear colunas fixas
        df = df.rename(columns={
            df.columns[1]: "Projeto",
            df.columns[2]: "Categoria",
            df.columns[3]: "Tipo",
            df.columns[4]: "Centro de Custo",
            df.columns[5]: "Marca",
            df.columns[6]: "Pilares",
            df.columns[7]: "Fixo/Variável"
        })

        # Remover linhas incompletas
        df.dropna(subset=["Projeto", "Categoria", "Tipo", "Centro de Custo", "Marca", "Pilares", "Fixo/Variável"], inplace=True)

        # Conversão segura para int
        df["Centro de Custo"] = pd.to_numeric(df["Centro de Custo"], errors='coerce').fillna(0).astype(int)

        # Identificar as colunas dos meses
        colunas_meses = [col for col in df.columns[8:] if 'TOTAL' not in str(col).upper()]

        # Transformar os dados em formato longo (melt)
        df_melt = df.melt(
            id_vars=["Projeto", "Categoria", "Tipo", "Centro de Custo", "Marca", "Pilares", "Fixo/Variável"],
            value_vars=colunas_meses,
            var_name="Data",
            value_name="Valor"
        )

        df_melt.dropna(subset=["Valor"], inplace=True)
        df_melt["Fonte"] = aba.strip()
        dfs.append(df_melt)

    return pd.concat(dfs, ignore_index=True)
# Função para carregar a aba Calendário
@st.cache_data
def carregar_calendario(arquivo_excel):
    df_calendario = pd.read_excel(arquivo_excel, sheet_name="Calendario")
    df_calendario.columns = ["Mês", "Campanha", "Área"]
    df_calendario.dropna(subset=["Mês", "Campanha"], inplace=True)
    return df_calendario

# Função para normalizar meses
def normalizar_meses(mes):
    meses_ref = {
        "JAN": "JAN", "JANEIRO": "JAN",
        "FEV": "FEB", "FEVEREIRO": "FEB",
        "MAR": "MAR", "MARÇO": "MAR",
        "ABR": "APR", "ABRIL": "APR",
        "MAI": "MAY", "MAIO": "MAY",
        "JUN": "JUN", "JUNHO": "JUN",
        "JUL": "JUL", "JULHO": "JUL",
        "AGO": "AUG", "AGOSTO": "AUG",
        "SET": "SEP", "SETEMBRO": "SEP",
        "OUT": "OCT", "OUTUBRO": "OCT",
        "NOV": "NOV", "NOVEMBRO": "NOV",
        "DEZ": "DEC", "DEZEMBRO": "DEC"
    }
    
    meses = mes.replace(" ", "").split("/")
    return [meses_ref.get(m.upper(), "") for m in meses]

# Função para criar tabela estilo calendário
def criar_tabela_calendario(df):
    meses_ordem = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", 
                   "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    linhas = []
    for campanha in df["Campanha"].unique():
        linha = {"Projeto": campanha}
        meses_campanha = df[df["Campanha"] == campanha]["Mês"].apply(normalizar_meses).explode().unique()
        for mes in meses_ordem:
            linha[mes] = "✔️" if mes in meses_campanha else ""
        linhas.append(linha)

    return pd.DataFrame(linhas)

@st.cache_data
def carregar_valores_centro_custo(caminho_arquivo):
    df = pd.read_excel(caminho_arquivo, sheet_name="Valores por Centro de Custo")
    df.dropna(how="all", inplace=True)  # Remove linhas completamente vazias
    return df

def calcular_soma_por_mes(arquivo_excel, abas_relevantes):
    dfs = []
    for aba in abas_relevantes:
        df = pd.read_excel(arquivo_excel, sheet_name=aba, header=1)
        df.rename(columns={
            df.columns[1]: "Projeto",
            df.columns[2]: "Categoria",
            df.columns[3]: "Tipo",
            df.columns[4]: "Centro de Custo",
            df.columns[5]: "Marca",
            df.columns[6]: "Pilares",
            df.columns[7]: "Fixo/Variável"
        }, inplace=True)

        colunas_meses = [col for col in df.columns[8:] if "TOTAL" not in str(col).upper()]
        df = df.melt(
            id_vars=["Projeto", "Categoria", "Tipo", "Centro de Custo", "Marca", "Pilares", "Fixo/Variável"],
            value_vars=colunas_meses,
            var_name="Data",
            value_name="Valor"
        )
        df.dropna(subset=["Valor"], inplace=True)
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df.dropna(subset=["Data"], inplace=True)
        df["Fonte"] = aba.strip()
        dfs.append(df)

    df_unificado = pd.concat(dfs, ignore_index=True)
    df_unificado["Mês"] = df_unificado["Data"].dt.to_period("M").astype(str)

    return df_unificado.groupby(["Mês", "Fonte"])["Valor"].sum().reset_index()

# Carregar dados
arquivo_excel = "Orçamento - 2025 - Base (2).xlsx"
abas_relevantes = ["2025 - MKT DE CONTEUDO", "2025 - MKT DE PRODUTO", "2025 - Growth", "2025 - Content HUB", "2025 - MÍDIA E PERFORMANCE", "2025 - CX"]

df_geral = carregar_dados(arquivo_excel, abas_relevantes) 
df_calendario = carregar_calendario(arquivo_excel)

# Sidebar com navegação
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Escolha a visualização:", ["Visão Geral", "Calendário de Projetos"] + abas_relevantes)

# Filtro de Meses (exclusivo para Calendário de Projetos)
meses_opcoes = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", 
                "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
if pagina == "Calendário de Projetos":
    filtro_meses = st.sidebar.multiselect("Selecione os meses:", options=meses_opcoes, default=meses_opcoes)
else:
    # Filtros Globais para as demais páginas
    st.sidebar.header("Filtros Globais")
    projetos = df_geral["Projeto"].dropna().unique()
    categorias = df_geral["Categoria"].dropna().unique()
    marcas = df_geral["Marca"].dropna().unique()
    centroCusto = df_geral["Centro de Custo"].dropna().unique()
    pilares = df_geral["Pilares"].dropna().unique()
    tipoCusto = df_geral["Fixo/Variável"].dropna().unique()

    filtro_projeto = st.sidebar.selectbox("Projeto", ["Todos"] + list(projetos))
    filtro_categoria = st.sidebar.selectbox("Categoria", ["Todos"] + list(categorias))
    filtro_marca = st.sidebar.selectbox("Marca", ["Todos"] + list(marcas))
    filtro_centro_custo = st.sidebar.selectbox("Centro de Custo", ["Todos"] + list(centroCusto))
    filtro_pilares = st.sidebar.selectbox("Pilares", ["Todos"] + list(pilares))
    filtro_tipo_custo = st.sidebar.selectbox("Fixo/Variável", ["Todos"] + list(tipoCusto))

    # Aplicação dos filtros
    df_filtrado = df_geral.copy()
    if filtro_projeto != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Projeto"] == filtro_projeto]
    if filtro_categoria != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Categoria"] == filtro_categoria]
    if filtro_marca != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Marca"] == filtro_marca]
    if filtro_centro_custo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Centro de Custo"] == int(filtro_centro_custo)]
    if filtro_pilares != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Pilares"] == filtro_pilares]
    if filtro_tipo_custo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Fixo/Variável"] == filtro_tipo_custo]


def calcular_totais_area(df, area=None):
    """
    Calcula os valores totais, fixos e variáveis para uma área específica.
    Se nenhuma área for especificada, calcula o total geral.
    """
    if area:
        df_area = df[df["Fonte"] == area.strip()]
    else:
        df_area = df

    total_area = df_area["Valor"].sum() if not df_area.empty else 0
    total_fixo = df_area[df_area["Fixo/Variável"] == "Fixo"]["Valor"].sum() if not df_area.empty else 0
    total_variavel = df_area[df_area["Fixo/Variável"] == "Variável"]["Valor"].sum() if not df_area.empty else 0

    return total_area, total_fixo, total_variavel
# VISÃO GERAL
if pagina == "Visão Geral":
    @st.cache_data
    def carregar_big_numbers(caminho_arquivo):
        df = pd.read_excel(caminho_arquivo, sheet_name="Geral")
        big_numbers = {
            "Total Gasto por Todas as Áreas": df.iloc[0, 0],
            "Total Fixo para Todas as Áreas": df.iloc[0, 1],
            "Total Variável em Todas as Áreas": df.iloc[0, 2],
        }
        return big_numbers


    # Carregar os dados usando a variável arquivo_excel
    big_numbers = carregar_big_numbers(arquivo_excel)

    # Exibir os BIG NUMBERS com layout em colunas
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="💰 Total Previsto para Todas as Áreas", 
                value=f"R$ {big_numbers['Total Gasto por Todas as Áreas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    with col2:
        st.metric(label="📈 Total Fixo Previsto para Todas as Áreas", 
                value=f"R$ {big_numbers['Total Fixo para Todas as Áreas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    with col3:
        st.metric(label="📉 Total Variável Previsto em Todas as Áreas", 
                value=f"R$ {big_numbers['Total Variável em Todas as Áreas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


    st.subheader("📊 Projetos 2025 - Ordenados por Gasto")
    st.dataframe(df_filtrado, use_container_width=True)

    # Carregar os dados da planilha
    arquivo_excel = "Orçamento - 2025 - Base (2).xlsx"
    abas_relevantes = ["2025 - MKT DE CONTEUDO", "2025 - MKT DE PRODUTO", "2025 - Growth", "2025 - Content HUB", "2025 - MÍDIA E PERFORMANCE", "2025 - CX" ]

    # Calcular a soma dos valores por mês e aba
    df_agrupado = calcular_soma_por_mes(arquivo_excel, abas_relevantes)

    # Ordenar os meses para garantir a exibição cronológica
    df_agrupado = df_agrupado.sort_values("Mês")

    # Gerar o gráfico de evolução de gastos
# Aplicar os filtros no dataframe consolidado para o gráfico
    df_agrupado_filtrado = df_agrupado.copy()
 

    # Garantir que o dataframe não está vazio após os filtros
    if not df_agrupado_filtrado.empty:

        # Gerar o gráfico de barras atualizado com os filtros aplicados
        st.subheader("📈 Evolução dos ValoreS Projetado por Mês e Área")
        fig_bar_filtrado = px.bar(
            df_agrupado_filtrado,
            x="Mês",
            y="Valor",
            color="Fonte",
            barmode="group",
            labels={
                "Mês": "Mês",
                "Valor": "Total Gasto",
                "Fonte": "Área"
            },
            title="Evolução dos Gastos Totais por Área "
        )
        st.plotly_chart(fig_bar_filtrado, use_container_width=True)
    else:
        st.warning("Nenhum dado corresponde aos filtros aplicados.")

    total_geral, fixo_geral, variavel_geral = calcular_totais_area(df_filtrado)

    # Criar a figura com subplots
    fig = sp.make_subplots(
        rows=1, cols=2,  # Dois gráficos lado a lado
        specs=[[{"type": "polar"}, {"type": "polar"}]],  # Ambos são gráficos polares
        subplot_titles=["Gastos Fixos", "Gastos Variáveis"]  # Títulos de cada gráfico
    )

    # Adicionar ponto para "Fixo"
    fig.add_trace(
        go.Scatterpolar(
            r=[fixo_geral],  # Valor de "Fixo"
            theta=["Fixo"],
            mode="markers",
            marker=dict(size=20, color="#636EFA", symbol="circle"),  # Azul para fixo
            name="Fixo"
        ),
        row=1, col=1
    )

    # Adicionar ponto para "Variável"
    fig.add_trace(
        go.Scatterpolar(
            r=[variavel_geral],  # Valor de "Variável"
            theta=["Variável"],
            mode="markers",
            marker=dict(size=20, color="#00CC96", symbol="circle"),  # Verde para variável
            name="Variável"
        ),
        row=1, col=2
    )

    # Configurar layout do gráfico polar
    fig.update_layout(
        title="📊 Gastos Fixo e Variável - Pontos no Polar",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, total_geral * 1.2],  # Ajustar escala radial com margem de 20%
                showline=True,  # Mostrar linha da grade
                color="black",  # Cor das linhas da grade
                tickfont=dict(color="black")  # Cor dos ticks e valores
            ),
            angularaxis=dict(
                color="black",  # Cor das linhas angulares
                tickfont=dict(color="black")  # Cor dos ticks e valores
            )
        ),
        polar2=dict(  # Configurações para o segundo gráfico polar
            radialaxis=dict(
                visible=True,
                range=[0, total_geral * 1.2],  # Ajustar escala radial com margem de 20%
                showline=True,  # Mostrar linha da grade
                color="black",  # Cor das linhas da grade
                tickfont=dict(color="black")  # Cor dos ticks e valores
            ),
            angularaxis=dict(
                color="black",  # Cor das linhas angulares
                tickfont=dict(color="black")  # Cor dos ticks e valores
            )
        ),
        height=400,
        template="plotly_white"
    )

    # Exibir no Streamlit
    st.plotly_chart(fig, use_container_width=True)

elif pagina == "Calendário de Projetos":
    st.subheader("📅 Calendário de Projetos 2025")
    tabela_calendario = criar_tabela_calendario(df_calendario)
    colunas_exibir = ["Projeto"] + filtro_meses
    tabela_filtrada = tabela_calendario[colunas_exibir]
    st.dataframe(tabela_filtrada, use_container_width=True)

elif pagina in abas_relevantes:

    # Filtrar apenas os dados da aba específica
    df_area_filtrado = df_filtrado[df_filtrado["Fonte"] == pagina.strip()]

    # Calcular os totais para a aba atual
    total_area, fixo_area, variavel_area = calcular_totais_area(df_area_filtrado)

    # Exibir os Big Numbers da aba
    st.subheader(f"📊 Análise Detalhada - {pagina.strip()}")
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        st.metric(label=f"Total Previsto - {pagina.strip()}",
                  value=f"R$ {total_area:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with col_b2:
        st.metric(label=f"Total Fixo - {pagina.strip()}",
                  value=f"R$ {fixo_area:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with col_b3:
        st.metric(label=f"Total Variável - {pagina.strip()}",
                  value=f"R$ {variavel_area:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Filtrar apenas os dados da aba específica
    df_pagina = df_filtrado[df_filtrado["Fonte"] == pagina.strip()]

    # Exibir tabela dinâmica dos projetos da aba selecionada
    st.subheader("📋 Tabela Dinâmica de Projetos")
    st.dataframe(df_pagina, use_container_width=True)

    # Gerar o gráfico para a aba selecionada
    if not df_pagina.empty:
        st.subheader("📈 Evolução dos Valores")
        fig_pagina = px.bar(
            df_pagina,
            x="Data",
            y="Valor",
            color="Categoria",
            labels={
                "Data": "Data",
                "Valor": "Valor (R$)",
                "Categoria": "Categoria"
            },
            title=f"Valores por Data - {pagina.strip()}",
        )
        st.plotly_chart(fig_pagina, use_container_width=True)
    else:
        st.info("Não há dados disponíveis para a área selecionada com os filtros aplicados.")