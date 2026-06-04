import pandas as pd
import streamlit as st
import plotly.express as px

# =============================================================================
# 1. CONFIGURAÇÕES DE LAYOUT DA PÁGINA (STREAMLIT)
# =============================================================================
st.set_page_config(
    page_title="Dashboard Seguro - Carteiras",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# Puxando o link blindado do cofre do Streamlit (Segurança Máxima)
URL_SHEETS = st.secrets["URL_PLANILHA"]

# =============================================================================
# 2. CARREGAMENTO E CACHE DE DADOS (PANDAS)
# =============================================================================
@st.cache_data(ttl=600)
def carregar_dados_sheets(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url, dtype={'Carteira': str})
        if 'Carteira' in df.columns:
            df['Carteira'] = df['Carteira'].astype(str).str.strip().str.zfill(2)
        return df
    except Exception as e:
        st.error(f"Erro crítico ao conectar com o Google Sheets: {e}")
        return pd.DataFrame()

df_carteiras = carregar_dados_sheets(URL_SHEETS)

# =============================================================================
# 3. SISTEMA DE SEGURANÇA VIA URL (TOKENS DE ACESSO)
# =============================================================================
parametros_url = st.query_params

# Resgata o token digitado na URL (ex: ?token=abc123xyz)
token_digitado = parametros_url.get("token", "Bloqueado")

# Valida o token contra o cofre de segredos da nuvem (st.secrets)
carteira_ativa = "Bloqueado"
if "tokens" in st.secrets and token_digitado in st.secrets["tokens"]:
    carteira_ativa = st.secrets["tokens"][token_digitado]

# Tratamento para identificar se é a senha mestra "geral" ou número de carteira
if str(carteira_ativa).lower() == "geral":
    carteira_ativa = "Geral"
elif carteira_ativa != "Bloqueado":
    carteira_ativa = str(carteira_ativa).strip().zfill(2)

# =============================================================================
# 4. VALIDAÇÃO DA TRAVA E PROCESSAMENTO DE DADOS (PANDAS)
# =============================================================================
if carteira_ativa == "Bloqueado":
    st.error("❌ Acesso Negado. Nenhuma credencial de gerência válida foi identificada nesta URL.")
    st.info("💡 Acesse utilizando o link exclusivo enviado pelo seu administrador.")

elif carteira_ativa != "Geral" and carteira_ativa not in df_carteiras['Carteira'].values:
    st.warning(f"⚠️ A carteira de código '{carteira_ativa}' não foi localizada na base de dados.")
    st.info("Verifique se o código enviado na URL está correto.")

else:
    # FILTRAGEM VIA PANDAS: Libera tudo se for "Geral", isola se for número
    if carteira_ativa == "Geral":
        df_carteira_crua = df_carteiras.copy()
    else:
        df_carteira_crua = df_carteiras[df_carteiras['Carteira'] == carteira_ativa].copy()
    
    # Mapeamento dos nomes exatos das colunas
    coluna_carteira = 'Carteira'
    coluna_valor = 'Valor Liq Calc python'
    coluna_cobranca = 'COBRANÇA'
    coluna_cliente = 'N Fantasia'
    coluna_id = 'ID_Único'
    coluna_grupo = 'Grupo Atendimento'
    coluna_range = 'Range_Acompanhamento'
    coluna_vencimento = 'Vencto real'
    coluna_status = 'Status Atend'
    coluna_tipo = 'Tipo'
    coluna_data_relatorio = 'Data_Relatorio_Consolidada'
    
    # Tratamento inicial dos números (Limpeza de R$, pontos de milhar e vírgulas)
    if coluna_valor in df_carteira_crua.columns:
        df_carteira_crua[coluna_valor] = df_carteira_crua[coluna_valor].astype(str)
        df_carteira_crua[coluna_valor] = df_carteira_crua[coluna_valor].str.replace('R$', '', regex=False).str.strip()
        df_carteira_crua[coluna_valor] = df_carteira_crua[coluna_valor].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_carteira_crua[coluna_valor] = pd.to_numeric(df_carteira_crua[coluna_valor], errors='coerce').fillna(0.0)

    # Tratamento preventivo da coluna de Status
    if coluna_status in df_carteira_crua.columns:
        df_carteira_crua[coluna_status] = pd.to_numeric(df_carteira_crua[coluna_status], errors='coerce').fillna(0).astype(int).astype(str)

    # Captura a data do relatório para o título
    data_relatorio_exibicao = "Data Indisponível"
    if coluna_data_relatorio in df_carteira_crua.columns and not df_carteira_crua[coluna_data_relatorio].dropna().empty:
        data_relatorio_exibicao = str(df_carteira_crua[coluna_data_relatorio].dropna().iloc[0]).strip()

    # -------------------------------------------------------------------------
    # MOTOR DE DATAS DIVIDIDO: Mês/Ano e Dia Exato
    # -------------------------------------------------------------------------
    if coluna_vencimento in df_carteira_crua.columns:
        datas_convertidas = pd.to_datetime(df_carteira_crua[coluna_vencimento], errors='coerce', dayfirst=True)
        
        df_carteira_crua['Mes_Filtro'] = datas_convertidas.dt.strftime('%m/%Y').fillna('Sem Data')
        df_carteira_crua['Data_Exata'] = datas_convertidas.dt.strftime('%d/%m/%Y').fillna('Sem Data')
        df_carteira_crua['Mes_Grafico'] = datas_convertidas.dt.strftime('%Y-%m').fillna('Sem Data')
        
        opcoes_mes = datas_convertidas.dropna().sort_values().dt.strftime('%m/%Y').unique().tolist()
        opcoes_dia = datas_convertidas.dropna().sort_values().dt.strftime('%d/%m/%Y').unique().tolist()
        
        if datas_convertidas.isna().any():
            opcoes_mes.append('Sem Data')
            opcoes_dia.append('Sem Data')
    else:
        df_carteira_crua['Mes_Filtro'] = 'Sem Data'
        df_carteira_crua['Data_Exata'] = 'Sem Data'
        df_carteira_crua['Mes_Grafico'] = 'Sem Data'
        opcoes_mes = ['Sem Data']
        opcoes_dia = ['Sem Data']

    # -------------------------------------------------------------------------
    # CONSTRUÇÃO DOS FILTROS INTERATIVOS GERAIS (SIDEBAR)
    # -------------------------------------------------------------------------
    st.sidebar.markdown("## 🔍 Filtros Gerais")
    st.sidebar.markdown("---")

    # NOVO: Filtro de Carteiras EXCLUSIVO para a visão Master
    if carteira_ativa == "Geral" and coluna_carteira in df_carteira_crua.columns:
        opcoes_carteira = sorted([str(x) for x in df_carteira_crua[coluna_carteira].dropna().unique()])
        sel_carteira = st.sidebar.multiselect("⭐ CARTEIRA (Apenas Master):", options=opcoes_carteira, placeholder="Todas")
        st.sidebar.markdown("---")
    else:
        sel_carteira = []

    if coluna_cobranca in df_carteira_crua.columns:
        opcoes_cobranca = sorted([str(x) for x in df_carteira_crua[coluna_cobranca].dropna().unique()])
        sel_cobranca = st.sidebar.multiselect("1. COBRANÇA:", options=opcoes_cobranca, placeholder="Todos")
    else:
        sel_cobranca = []

    if coluna_cliente in df_carteira_crua.columns:
        opcoes_cliente = sorted([str(x) for x in df_carteira_crua[coluna_cliente].dropna().unique()])
        sel_cliente = st.sidebar.multiselect("2. CLIENTE:", options=opcoes_cliente, placeholder="Todos")
    else:
        sel_cliente = []

    if coluna_status in df_carteira_crua.columns:
        opcoes_status = sorted([str(x) for x in df_carteira_crua[coluna_status].unique()], key=int)
        sel_status = st.sidebar.multiselect("3. STATUS ATEND:", options=opcoes_status, placeholder="Todos")
    else:
        sel_status = []

    if coluna_grupo in df_carteira_crua.columns:
        opcoes_grupo = sorted([str(x) for x in df_carteira_crua[coluna_grupo].dropna().unique()])
        sel_grupo = st.sidebar.multiselect("4. GRUPO ATENDIMENTO:", options=opcoes_grupo, placeholder="Todos")
    else:
        sel_grupo = []

    if coluna_range in df_carteira_crua.columns:
        opcoes_range = sorted([str(x) for x in df_carteira_crua[coluna_range].dropna().unique()])
        sel_range = st.sidebar.multiselect("5. RANGE ACOMPANHAMENTO:", options=opcoes_range, placeholder="Todos")
    else:
        sel_range = []

    sel_mes = st.sidebar.multiselect("6. MÊS VENCIMENTO:", options=opcoes_mes, placeholder="Todos")
    sel_dia = st.sidebar.multiselect("7. DIA VENCIMENTO:", options=opcoes_dia, placeholder="Todos")

    # -------------------------------------------------------------------------
    # APLICANDO OS FILTROS CRUZADOS NA BASE DE MEMÓRIA (DATAFRAME)
    # -------------------------------------------------------------------------
    df_filtrado = df_carteira_crua.copy()
    
    if sel_carteira: df_filtrado = df_filtrado[df_filtrado[coluna_carteira].astype(str).isin(sel_carteira)]
    if sel_cobranca: df_filtrado = df_filtrado[df_filtrado[coluna_cobranca].astype(str).isin(sel_cobranca)]
    if sel_cliente:  df_filtrado = df_filtrado[df_filtrado[coluna_cliente].astype(str).isin(sel_cliente)]
    if sel_status:   df_filtrado = df_filtrado[df_filtrado[coluna_status].astype(str).isin(sel_status)]
    if sel_grupo:    df_filtrado = df_filtrado[df_filtrado[coluna_grupo].astype(str).isin(sel_grupo)]
    if sel_range:    df_filtrado = df_filtrado[df_filtrado[coluna_range].astype(str).isin(sel_range)]
    if sel_mes:      df_filtrado = df_filtrado[df_filtrado['Mes_Filtro'].astype(str).isin(sel_mes)]
    if sel_dia:      df_filtrado = df_filtrado[df_filtrado['Data_Exata'].astype(str).isin(sel_dia)]

    # -------------------------------------------------------------------------
    # CÁLCULO DOS 5 KPIS PRINCIPAIS (DINÂMICOS)
    # -------------------------------------------------------------------------
    total_geral = df_filtrado[coluna_valor].sum() if coluna_valor in df_filtrado.columns else 0.0
    quant_titulos = df_filtrado[coluna_id].nunique() if coluna_id in df_filtrado.columns else len(df_filtrado)
    quant_clientes = df_filtrado[coluna_cliente].nunique() if coluna_cliente in df_filtrado.columns else 0

    valor_cobravel = 0.0
    valor_incobravel = 0.0
    
    if coluna_cobranca in df_filtrado.columns and coluna_valor in df_filtrado.columns:
        serie_cobranca = df_filtrado[coluna_cobranca].astype(str).str.strip()
        filtro_cobravel = serie_cobranca.str.contains('cobrável|cobravel', case=False, regex=True, na=False)
        filtro_estrito_cobravel = filtro_cobravel & ~serie_cobranca.str.contains('incobrável|incobravel', case=False, regex=True, na=False)
        valor_cobravel = df_filtrado[filtro_estrito_cobravel][coluna_valor].sum()
        
        filtro_incobravel = serie_cobranca.str.contains('incobrável|incobravel', case=False, regex=True, na=False)
        valor_incobravel = df_filtrado[filtro_incobravel][coluna_valor].sum()

    # -------------------------------------------------------------------------
    # CRIAÇÃO DO DATAFRAME FILTRADO EXCLUSIVO PARA OS GRÁFICOS 2, 3, 4 e 5 (NF/BOL)
    # -------------------------------------------------------------------------
    if coluna_tipo in df_filtrado.columns:
        df_filtrado[coluna_tipo] = df_filtrado[coluna_tipo].astype(str).str.strip().str.upper()
        df_graficos_filtrados = df_filtrado[df_filtrado[coluna_tipo].isin(['NF', 'BOL'])].copy()
    else:
        df_graficos_filtrados = df_filtrado.copy()

    # =============================================================================
    # 5. CONSTRUÇÃO DA INTERFACE GRÁFICA ORGANIZADA (STREAMLIT)
    # =============================================================================
    nome_carteira = 'VISÃO GERAL (MASTER)' if carteira_ativa == 'Geral' else f'Carteira {carteira_ativa}'
    titulo_painel = f"Controle Inadimplência — {nome_carteira} | 📅 {data_relatorio_exibicao}"
    
    st.markdown(f"# {titulo_painel}")
    st.write("Dados atualizados em tempo real diretamente do Google Sheets.")
    st.markdown("---")
    
    # Renderização dos KPIs
    st.markdown("### 📈 Indicadores Gerais")
    g1, g2, g3 = st.columns(3)
    with g1:
        with st.container(border=True):
            st.markdown("**💰 Total Geral (Valor Líq)**")
            st.markdown(f"### R$ {total_geral:,.2f}")
    with g2:
        with st.container(border=True):
            st.markdown("**📄 Quantidade de Títulos**")
            st.markdown(f"### {quant_titulos:,}".replace(",", "."))
    with g3:
        with st.container(border=True):
            st.markdown("**👥 Quantidade de Clientes**")
            st.markdown(f"### {quant_clientes:,}".replace(",", "."))
            
    g4, g5 = st.columns(2)
    with g4:
        with st.container(border=True):
            st.markdown("🟢 **Total Cobrável**")
            st.markdown(f"## R$ {valor_cobravel:,.2f}")
    with g5:
        with st.container(border=True):
            st.markdown("🔴 **Total Incobrável**")
            st.markdown(f"## R$ {valor_incobravel:,.2f}")
            
    st.markdown("---")

    # -------------------------------------------------------------------------
    # LINHA 1 DE GRÁFICOS: CLIENTES (Largura Total Superior)
    # -------------------------------------------------------------------------
    if coluna_cliente in df_filtrado.columns:
        st.markdown("**CLIENTES**")
        with st.container(height=600, border=True):
            df_g1 = df_filtrado.groupby(coluna_cliente)[coluna_valor].sum().reset_index()
            df_g1 = df_g1.sort_values(by=coluna_valor, ascending=True)
            
            altura_interna_g1 = max(550, len(df_g1) * 35)
            max_g1 = df_g1[coluna_valor].max() if not df_g1.empty else 100
            
            fig1 = px.bar(
                df_g1, x=coluna_valor, y=coluna_cliente, orientation='h', 
                template="plotly_dark", height=altura_interna_g1, text=coluna_valor,
                color_discrete_sequence=['#4CAF50'], range_x=[0, max_g1 * 1.35]
            )
            fig1.update_yaxes(type='category', title=None)
            fig1.update_xaxes(showticklabels=False, title=None, showgrid=False)
            fig1.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', cliponaxis=False, textfont=dict(color='white', size=11))
            fig1.update_layout(margin=dict(l=220, r=40, t=10, b=10))
            st.plotly_chart(fig1, use_container_width=True)

    # -------------------------------------------------------------------------
    # LINHA 2 DE GRÁFICOS: PIZZAS LADO A LADO COM LEGENDA INFERIOR
    # -------------------------------------------------------------------------
    col_pizza1, col_pizza2 = st.columns(2)
    
    with col_pizza1:
        st.markdown("**INADIMPLÊNCIA POR GRUPO**")
        with st.container(height=480, border=True): 
            if coluna_grupo in df_graficos_filtrados.columns:
                df_g2 = df_graficos_filtrados.groupby(coluna_grupo)[coluna_valor].sum().reset_index()
                cores_pizza = ['#17a2b8', '#4CAF50', '#20c997', '#0e76a8']
                
                total_g2 = df_g2[coluna_valor].sum() if not df_g2.empty else 1
                df_g2['Legenda'] = df_g2.apply(lambda r: f"{r[coluna_grupo]} (R$ {r[coluna_valor]:,.2f} | {(r[coluna_valor]/total_g2)*100:.1f}%)", axis=1)
                
                fig2 = px.pie(
                    df_g2, values=coluna_valor, names='Legenda', 
                    template="plotly_dark", height=430, color_discrete_sequence=cores_pizza
                )
                fig2.update_traces(
                    textinfo='percent', 
                    textfont=dict(size=12, color='white')
                )
                fig2.update_layout(
                    legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), 
                    margin=dict(l=10, r=10, t=20, b=100) 
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Coluna Grupo Atendimento não encontrada.")

    with col_pizza2:
        st.markdown("**INADIMPLÊNCIA POR ACOMPANHAMENTO**")
        with st.container(height=480, border=True):
            if coluna_range in df_graficos_filtrados.columns:
                df_g3 = df_graficos_filtrados.groupby(coluna_range)[coluna_valor].sum().reset_index()
                cores_pizza_3 = ['#0e76a8', '#17a2b8', '#4CAF50', '#20c997']
                
                total_g3 = df_g3[coluna_valor].sum() if not df_g3.empty else 1
                df_g3['Legenda'] = df_g3.apply(lambda r: f"{r[coluna_range]} (R$ {r[coluna_valor]:,.2f} | {(r[coluna_valor]/total_g3)*100:.1f}%)", axis=1)
                
                fig3 = px.pie(
                    df_g3, values=coluna_valor, names='Legenda', 
                    template="plotly_dark", height=430, color_discrete_sequence=cores_pizza_3
                )
                fig3.update_traces(
                    textinfo='percent', 
                    textfont=dict(size=12, color='white')
                )
                fig3.update_layout(
                    legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), 
                    margin=dict(l=10, r=10, t=20, b=100)
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("Coluna Range_Acompanhamento não encontrada.")

    # -------------------------------------------------------------------------
    # LINHA 3 DE GRÁFICOS: MÊS (Gráfico) E STATUS ATEND
    # -------------------------------------------------------------------------
    col_baixo1, col_baixo2 = st.columns(2)
    
    with col_baixo1:
        st.markdown("**Valor Vencido por Mês**")
        with st.container(height=450, border=True):
            if 'Mes_Grafico' in df_graficos_filtrados.columns:
                try:
                    df_g4 = df_graficos_filtrados.groupby('Mes_Grafico')[coluna_valor].sum().reset_index()
                    df_g4 = df_g4.sort_values(by='Mes_Grafico', ascending=True)
                    
                    df_g4['Mes_Exibicao'] = df_g4['Mes_Grafico'].apply(lambda x: f"{x[-2:]}/{x[:4]}" if x != 'Sem Data' else x)
                    
                    altura_interna_g4 = max(400, len(df_g4) * 35)
                    max_g4 = df_g4[coluna_valor].max() if not df_g4.empty else 100
                    
                    fig4 = px.bar(
                        df_g4, x=coluna_valor, y='Mes_Exibicao', orientation='h', 
                        template="plotly_dark", height=altura_interna_g4, text=coluna_valor,
                        color_discrete_sequence=['#4CAF50'], range_x=[0, max_g4 * 1.35]
                    )
                    fig4.update_yaxes(type='category', title=None, categoryorder='array', categoryarray=df_g4['Mes_Exibicao'])
                    fig4.update_xaxes(showticklabels=False, title=None, showgrid=False)
                    fig4.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', cliponaxis=False, textfont=dict(color='white', size=11))
                    fig4.update_layout(margin=dict(l=100, r=40, t=10, b=10))
                    st.plotly_chart(fig4, use_container_width=True)
                except:
                    st.warning("⚠️ Erro ao formatar datas para o gráfico mensal.")

    with col_baixo2:
        st.markdown("**Valor por Status Atend **")
        with st.container(height=450, border=True):
            if coluna_status in df_graficos_filtrados.columns:
                df_graficos_filtrados[coluna_status] = pd.to_numeric(df_graficos_filtrados[coluna_status], errors='coerce').fillna(0).astype(int).astype(str)
                
                df_g5 = df_graficos_filtrados.groupby(coluna_status)[coluna_valor].sum().reset_index()
                df_g5 = df_g5.sort_values(by=coluna_valor, ascending=True)
                
                altura_interna_g5 = max(400, len(df_g5) * 35)
                max_g5 = df_g5[coluna_valor].max() if not df_g5.empty else 100
                
                fig5 = px.bar(
                    df_g5, x=coluna_valor, y=coluna_status, orientation='h', 
                    template="plotly_dark", height=altura_interna_g5, text=coluna_valor,
                    color_discrete_sequence=['#4CAF50'], range_x=[0, max_g5 * 1.35]
                )
                fig5.update_yaxes(type='category', title=None)
                fig5.update_xaxes(showticklabels=False, title=None, showgrid=False)
                fig5.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', cliponaxis=False, textfont=dict(color='white', size=11))
                fig5.update_layout(coloraxis_showscale=False, margin=dict(l=100, r=40, t=10, b=10)) 
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("Coluna Status Atend não encontrada.")

    st.markdown("---")
    st.markdown("### 📋 Tabela de Títulos Resumido")
    
    colunas_finais = [c for c in df_filtrado.columns if c not in ['Mes_Filtro', 'Data_Exata', 'Mes_Grafico']]
    st.dataframe(df_filtrado[colunas_finais], use_container_width=True, hide_index=True)
