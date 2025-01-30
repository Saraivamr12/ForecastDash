import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp
import time

# Configurações iniciais
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")
st.title("📊 Dashboard Financeiro")

USER_CREDENTIALS = {
    "admin": "1234",
    "Maria Saraiva": "Wap@2024",
    "MktWap": "Wap@2025",
    "Jean": "Wap@2025",
    "Tiago": "mkt@wap"
}

# Inicializa a sessão de login, se necessário
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""

if "welcome_shown" not in st.session_state:
    st.session_state["welcome_shown"] = False  # Controle para exibir a mensagem apenas no primeiro login

# --- FUNÇÃO DE LOGIN ---
def login():
    st.title("Login")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

# Se o usuário **não** estiver logado, exibe apenas a página de login
if not st.session_state["logged_in"]:
    login()
    st.stop()  # Interrompe a execução do código abaixo se o usuário não estiver autenticado

# --- SE O USUÁRIO ESTIVER LOGADO, EXIBE O DASHBOARD ---

if st.session_state["logged_in"] and not st.session_state["welcome_shown"]:
    msg_container = st.sidebar.empty()
    msg_container.success(f"✅ Bem-vindo, {st.session_state['username']}!")
    st.session_state["welcome_shown"] = True
    time.sleep(1)
    msg_container.empty()

# Função para carregar e processar as abas relevantes@st.cache_data
@st.cache_data
def processar_aba(arquivo_excel, aba):
    try:
        # Carregar os dados da aba
        df = pd.read_excel(arquivo_excel, sheet_name=aba, header=1)

        # Verificar se o DataFrame foi carregado corretamente
        if df.empty:
            raise ValueError(f"A aba '{aba}' está vazia.")

        # Validar número mínimo de colunas esperado
        if len(df.columns) < 8:
            raise ValueError(f"A aba '{aba}' não possui colunas suficientes para processamento.")

        # Renomear colunas com validação
        colunas_esperadas = ["Projeto", "Categoria", "Tipo", "Centro de Custo", "Marca", "Pilares", "Fixo/Variável"]
        colunas_renomeadas = {df.columns[i + 1]: colunas_esperadas[i] for i in range(len(colunas_esperadas))}

        # Renomear colunas
        df.rename(columns=colunas_renomeadas, inplace=True)

        # Validar se todas as colunas necessárias estão presentes
        colunas_faltando = [col for col in colunas_esperadas if col not in df.columns]
        if colunas_faltando:
            raise ValueError(f"As colunas esperadas estão ausentes na aba '{aba}': {colunas_faltando}")

        # Remover linhas onde todas as colunas principais estão vazias
        df.dropna(subset=colunas_esperadas, how="all", inplace=True)

        # Converter "Centro de Custo" para numérico
        df["Centro de Custo"] = pd.to_numeric(df["Centro de Custo"], errors="coerce").fillna(0).astype(int)

        # Identificar colunas de meses (a partir da 8ª coluna)
        colunas_meses = [col for col in df.columns[8:] if "TOTAL" not in str(col).upper()]
        if not colunas_meses:
            raise ValueError(f"Nenhuma coluna de mês válida encontrada na aba '{aba}'.")

        # Garantir que valores monetários nas colunas de meses estão no formato correto
        for col in colunas_meses:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ".").str.replace(" ", ""),
                errors="coerce"
            ).fillna(0)

        # Transformar para formato longo (melt)
        df_melt = df.melt(
            id_vars=colunas_esperadas,
            value_vars=colunas_meses,
            var_name="Data",
            value_name="Valor"
        )

        # Filtrar valores inválidos ou nulos
        df_melt.dropna(subset=["Valor"], inplace=True)

        # Adicionar coluna com o nome da aba
        df_melt["Fonte"] = aba.strip()

        # Retornar o DataFrame processado
        return df_melt

    except Exception as e:
        st.error(f"Erro ao processar a aba '{aba}': {e}")
        return pd.DataFrame()
@st.cache_data
def carregar_dados(arquivo_excel, abas_relevantes):
    dfs = []
    for aba in abas_relevantes:
        df_melt = processar_aba(arquivo_excel, aba)
        if not df_melt.empty:
            dfs.append(df_melt)
        else:
            st.warning(f"A aba '{aba}' não foi processada corretamente e foi ignorada.")

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        st.error("Nenhuma aba relevante foi processada com sucesso.")
        return pd.DataFrame()

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
arquivo_excel = "Orçamento - 2025 - Base (3).xlsx"
abas_relevantes = [" 2025 - MKT DE CONTEUDO ", " 2025 - MKT DE PRODUTO", " 2025 - Growth", " 2025 - Conteúdo", " 2025 - Mídia e Performance", "2025 - CX"]

df_geral = carregar_dados(arquivo_excel, abas_relevantes) 
df_calendario = carregar_calendario(arquivo_excel)

# Sidebar com navegação
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Escolha a visualização:", ["Visão Geral", "Calendário de Projetos", "Análise de Budget"] + abas_relevantes)

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

st.sidebar.button("🔴 Logout", on_click=lambda: st.session_state.update({"logged_in": False, "username": ""}))


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
    # Calcular os valores dinâmicos com base nos filtros aplicados
    total_geral = df_filtrado["Valor"].sum()
    total_fixo = df_filtrado[df_filtrado["Fixo/Variável"] == "Fixo"]["Valor"].sum()
    total_variavel = df_filtrado[df_filtrado["Fixo/Variável"] == "Variável"]["Valor"].sum()

    # Exibir os BIG NUMBERS com layout em colunas
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="💰 Total Previsto para Todas as Áreas", 
            value=f"R$ {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    with col2:
        st.metric(
            label="📈 Total Fixo Previsto para Todas as Áreas", 
            value=f"R$ {total_fixo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    with col3:
        st.metric(
            label="📉 Total Variável Previsto em Todas as Áreas", 
            value=f"R$ {total_variavel:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    st.subheader("📊 Projetos 2025 - Ordenados por Gasto")
    st.caption("")    
    st.dataframe(df_filtrado, use_container_width=True)
    
    # Carregar os dados da planilha
    arquivo_excel = "Orçamento - 2025 - Base (3).xlsx"
    abas_relevantes = [" 2025 - MKT DE CONTEUDO ", " 2025 - MKT DE PRODUTO", " 2025 - Growth", " 2025 - Conteúdo", " 2025 - Mídia e Performance", "2025 - CX" ]

    # Calcular a soma dos valores por mês e aba
    df_agrupado = calcular_soma_por_mes(arquivo_excel, abas_relevantes)

    # Ordenar os meses para garantir a exibição cronológica
    df_agrupado = df_agrupado.sort_values("Mês")

    # Gerar o gráfico de evolução de gastos
# Aplicar os filtros no dataframe consolidado para o gráfico
    df_agrupado_filtrado = df_agrupado.copy()
 

    # Garantir que o dataframe não está vazio após os filtros
    if not df_filtrado.empty:
        st.subheader("📈 Evolução dos Valores Planejados por Área")
        
        # Agregar os valores por Fonte (Área) e Data (Mês)
        df_agrupado_area = df_filtrado.groupby(["Data", "Fonte"])["Valor"].sum().reset_index()
        
        # Gerar o gráfico de barras dinâmico com os valores por área
        fig_bar_dinamico = px.bar(
            df_agrupado_area,
            x="Data",  # Eixo X (Datas, por exemplo)
            y="Valor",  # Eixo Y (Valores filtrados)
            color="Fonte",  # Barras separadas por Área
            barmode="group",  # Barras agrupadas por mês
            labels={
                "Data": "Data",
                "Valor": "Total Gasto (R$)",
                "Fonte": "Área"
            },
            title="Comparação de Gastos Totais por Área"
        )
        
        # Exibir o gráfico
        st.plotly_chart(fig_bar_dinamico, use_container_width=True)
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
    
    st.plotly_chart(fig, use_container_width=True)

        # Função para carregar budget


elif pagina == "Análise de Budget":

    @st.cache_data
    def carregar_dados_2024(file_path):
        """ Carrega e processa os dados da aba 2024. """
        try:
            df_2024 = pd.read_excel(file_path, sheet_name="2024", header=1)

            df_2024.rename(columns={
                df_2024.columns[1]: "Projeto",
                df_2024.columns[2]: "Tipo",
                df_2024.columns[3]: "Centro de Custo",
                df_2024.columns[4]: "Marca",
                df_2024.columns[5]: "Pilares",
                df_2024.columns[6]: "Fixo/Variável"
            }, inplace=True)

            colunas_meses = [col for col in df_2024.columns[7:] if "TOTAL" not in str(col).upper()]

            for col in colunas_meses:
                df_2024[col] = pd.to_numeric(df_2024[col], errors="coerce").fillna(0)

            df_2024_melt = df_2024.melt(
                id_vars=["Projeto", "Tipo", "Centro de Custo", "Marca", "Pilares", "Fixo/Variável"],
                value_vars=colunas_meses,
                var_name="Mês",
                value_name="Valor"
            )

            df_2024_melt["Mês"] = pd.to_datetime(df_2024_melt["Mês"], errors="coerce")
            df_2024_melt = df_2024_melt[df_2024_melt["Valor"] > 0]

            return df_2024_melt

        except Exception as e:
            st.error(f"Erro ao carregar dados da aba 2024: {e}")
            return pd.DataFrame()

    # 📌 Carregar dados da aba 2024
    df_2024 = carregar_dados_2024(arquivo_excel)

    # 📊 Gerar gráfico de maiores gastos
    if not df_2024.empty:
        st.subheader("📊 Maiores Gastos do Ano de 2024")

        df_maiores_gastos = df_2024.groupby("Projeto")["Valor"].sum().reset_index()
        df_maiores_gastos = df_maiores_gastos.sort_values(by="Valor", ascending=False).head(10)

        fig_maiores_gastos = px.bar(
            df_maiores_gastos,
            x="Valor",
            y="Projeto",
            orientation="h",
            title="Top 10 Maiores Gastos de 2024",
            labels={"Projeto": "Projetos", "Valor": "Gasto Total (R$)"},
            text_auto=True
        )

        st.plotly_chart(fig_maiores_gastos, use_container_width=True)
    else:
        st.warning("Nenhum dado disponível para exibir os maiores gastos de 2024.")

    # 📌 Carregar Budgets
    @st.cache_data
    def carregar_budget_fixos(file_path):
        """ Carrega e processa os dados da aba BUDGET FIXOS. """
        budget_fixos = pd.read_excel(file_path, sheet_name="BUDGET FIXOS")
        budget_fixos = budget_fixos.rename(columns={"Unnamed: 1": "Tipo", budget_fixos.columns[2]: "Budget Disponível"})
        budget_fixos = budget_fixos.dropna(subset=["Tipo", "Budget Disponível"])
        return budget_fixos[["Tipo", "Budget Disponível"]]

    @st.cache_data
    def carregar_budget_variaveis(file_path):
        """ Carrega e processa os dados da aba BUDGET VARIÁVEIS. """
        budget_variaveis = pd.read_excel(file_path, sheet_name="BUDGET VARIÁVEIS")
        budget_variaveis = budget_variaveis.rename(columns={"Unnamed: 0": "Tipo", budget_variaveis.columns[1]: "Budget Disponível"})
        budget_variaveis = budget_variaveis.dropna(subset=["Tipo", "Budget Disponível"])
        return budget_variaveis[["Tipo", "Budget Disponível"]]

    # 📌 Carregar dados de Budget Fixo e Variável
    gastos_fixos = carregar_budget_fixos(arquivo_excel)
    gastos_variaveis = carregar_budget_variaveis(arquivo_excel)

    # 📌 Comparação entre Budget e Planejado para 2025
    st.subheader("📊 Comparação entre Budget Disponível e Valores Planejados")

    df_planejado_resumo = df_geral.groupby(["Projeto", "Centro de Custo", "Fixo/Variável"])["Valor"].sum().reset_index()

    df_planejado_resumo = df_geral.groupby(["Projeto", "Centro de Custo", "Fixo/Variável"])["Valor"].sum().reset_index()

    # Separar os planejamentos fixos e variáveis
    df_planejado_fixos = df_planejado_resumo[df_planejado_resumo["Fixo/Variável"].str.lower() == "fixo"].copy()
    df_planejado_variaveis = df_planejado_resumo[df_planejado_resumo["Fixo/Variável"].str.lower() == "variável"].copy()

    # Garantir que "Centro de Custo" e "Tipo" estão no mesmo formato (string) para o merge
    df_planejado_fixos["Centro de Custo"] = df_planejado_fixos["Centro de Custo"].astype(str)
    df_planejado_variaveis["Centro de Custo"] = df_planejado_variaveis["Centro de Custo"].astype(str)
    gastos_fixos["Tipo"] = gastos_fixos["Tipo"].astype(str)
    gastos_variaveis["Tipo"] = gastos_variaveis["Tipo"].astype(str)

    # Comparação de valores fixos
    comparacao_fixos = pd.merge(
        df_planejado_fixos.rename(columns={"Centro de Custo": "Tipo"}),
        gastos_fixos,
        on="Tipo",
        how="left"
    ).fillna(0)

    # Comparação de valores variáveis
    comparacao_variaveis = pd.merge(
        df_planejado_variaveis.rename(columns={"Centro de Custo": "Tipo"}),
        gastos_variaveis,
        on="Tipo",
        how="left"
    ).fillna(0)

    # Criar status de orçamento
    def definir_status(valor_planejado, budget_disponivel):
        if valor_planejado > budget_disponivel:
            return "🔴 Acima do Budget"
        elif valor_planejado < budget_disponivel:
            return "🟢 Abaixo do Budget"
        else:
            return "🟡 Dentro do Budget"

    comparacao_fixos["Status"] = comparacao_fixos.apply(lambda row: definir_status(row["Valor"], row["Budget Disponível"]), axis=1)
    comparacao_variaveis["Status"] = comparacao_variaveis.apply(lambda row: definir_status(row["Valor"], row["Budget Disponível"]), axis=1)

    # Unir os dois DataFrames
    comparacao_final = pd.concat([comparacao_fixos, comparacao_variaveis], ignore_index=True)

    # 📋 Exibir tabela de comparação sem ace_tools
    st.subheader("📋 Resumo Comparativo por Tipo")
    st.dataframe(comparacao_final, use_container_width=True)
    # Comparação de valores variáveis
    comparacao_variaveis = pd.merge(
        df_planejado_variaveis.rename(columns={"Centro de Custo": "Tipo"}),
        gastos_variaveis,
        on="Tipo",
        how="left"
    ).fillna(0)

    comparacao_variaveis = pd.merge(
        df_planejado_variaveis.rename(columns={"Centro de Custo": "Tipo"}),
        gastos_variaveis,
        on="Tipo",
        how="left"
    ).fillna(0)

    # Criar status de orçamento
    def definir_status(valor_planejado, budget_disponivel):
        if valor_planejado > budget_disponivel:
            return "🔴 Acima do Budget"
        elif valor_planejado < budget_disponivel:
            return "🟢 Abaixo do Budget"
        else:
            return "🟡 Dentro do Budget"

    comparacao_fixos["Status"] = comparacao_fixos.apply(lambda row: definir_status(row["Valor"], row["Budget Disponível"]), axis=1)
    comparacao_variaveis["Status"] = comparacao_variaveis.apply(lambda row: definir_status(row["Valor"], row["Budget Disponível"]), axis=1)

    # Unir os dois DataFrames
    comparacao_final = pd.concat([comparacao_fixos, comparacao_variaveis], ignore_index=True)

    # 📋 Exibir tabela de comparação sem usar ace_tools
    st.subheader("📋 Resumo Comparativo por Tipo")
    st.dataframe(comparacao_final, use_container_width=True)

    # 📊 Gráficos de Comparação
    st.subheader("📊 Comparação Budget vs. Planejado")
    fig_comparacao = px.bar(
        comparacao_final,
        x="Tipo",
        y=["Valor", "Budget Disponível"],
        barmode="group",
        title="Comparação entre Budget e Planejado"
    )
    st.plotly_chart(fig_comparacao, use_container_width=True)

    st.subheader("📊 Diferença Entre Orçado e Planejado")
    fig_diferenca = px.bar(
        comparacao_final,
        x="Tipo",
        y="Valor",
        color="Status",
        title="Diferença Entre Orçado e Planejado por Tipo",
        text_auto=True
    )
    st.plotly_chart(fig_diferenca, use_container_width=True)

elif pagina == "Calendário de Projetos":
    st.subheader("📅 Calendário de Projetos 2025")
    tabela_calendario = criar_tabela_calendario(df_calendario)
    colunas_exibir = ["Projeto"] + filtro_meses
    tabela_filtrada = tabela_calendario[colunas_exibir]
    st.dataframe(tabela_filtrada, use_container_width=True)

elif pagina in abas_relevantes:
    st.subheader(f"📊 Análise Detalhada - {pagina.strip()}")
    
    # Filtrar os dados da aba selecionada
    df_area_filtrado = df_filtrado[df_filtrado["Fonte"] == pagina.strip()]

    # Verificar se há dados processados
    if df_area_filtrado.empty:
        st.warning(f"Nenhum dado processado para a aba '{pagina.strip()}'. Verifique a estrutura dos dados na planilha.")
    else:
        # Exibir os Big Numbers
        total_area, fixo_area, variavel_area = calcular_totais_area(df_area_filtrado)
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

        # Exibir os dados da aba
        st.subheader("📋 Dados Detalhados da Aba")
        st.dataframe(df_area_filtrado, use_container_width=True)

        # Gerar gráfico de barras
        st.subheader("📈 Evolução dos Valores por Data")
        fig = px.bar(
            df_area_filtrado,
            x="Data",
            y="Valor",
            color="Categoria",
            labels={
                "Data": "Data",
                "Valor": "Valor (R$)",
                "Categoria": "Categoria"
            },
            title=f"Evolução dos Valores - {pagina.strip()}"
        )
        st.plotly_chart(fig, use_container_width=True)