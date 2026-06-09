import pandas as pd
import streamlit as st
import plotly.express as px
import io 

# =============================================================================
# 1. CONFIGURAÇÕES DE LAYOUT E ESTILO PREMIUM (UI/UX)
# =============================================================================
# Esconde elementos do Streamlit e adiciona CSS para Cards Premium
estilo_premium = """
    <style>
    /* Esconde o botão do GitHub e rodapé */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    
    /* Estilização Premium para os KPIs (Cards) */
    [data-testid="metric-container"] {
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        border-left: 4px solid #4CAF50; /* Detalhe verde na lateral */
    }
    
    /* Muda a cor do detalhe lateral do card de Inadimplência para Vermelho */
    div:nth-child(2) > div > [data-testid="metric-container"] {
        border-left: 4px solid #ff4b4b; 
    }
    </style>
"""

st.set_page_config(
    page_title="Dashboard Seguro - Carteiras",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" 
)
st.markdown(estilo_premium, unsafe_allow_html=True)

# Puxando o link blindado do cofre do Streamlit
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
# 3. SISTEMA DE LOGIN SEGURO (SESSION STATE)
# =============================================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["carteira_ativa"] = "Bloqueado"

if not st.session_state["autenticado"]:
    st.markdown("<br><br>", unsafe_allow_html=True) # Dá um espaço no topo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True): # Coloca o login dentro de um card
            st.markdown("<h2 style='text-align: center;'>🔒 Portal da Inadimplência</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888;'>Insira a sua credencial para acessar a carteira</p>", unsafe_allow_html=True)
            st.divider()
            
            senha_digitada = st.text_input("Senha de Acesso:", type="password")
            
            if st.button("Entrar no Sistema", type="primary", use_container_width=True):
                if "tokens" in st.secrets and senha_digitada in st.secrets["tokens"]:
                    st.session_state["autenticado"] = True
                    st.session_state["carteira_ativa"] = st.secrets["tokens"][senha_digitada]
                    st.rerun()
                else:
                    st.error("❌ Credencial incorreta ou acesso negado.")
    st.stop() 

carteira_ativa = st.session_state["carteira_ativa"]
if str(carteira_ativa).lower() == "geral":
    carteira_ativa = "Geral"
else:
    carteira_ativa = str(carteira_ativa).strip().zfill(2)

st.sidebar.button("🚪 Encerrar Sessão (Logout)", use_container_width=True, on_click=lambda: st.session_state.clear() or st.rerun())
st.sidebar.divider()

# =============================================================================
# 4. VALIDAÇÃO E PROCESSAMENTO DE DADOS (PANDAS)
# =============================================================================
if carteira_ativa == "Geral":
    df_carteira_crua = df_carteiras.copy()
else:
    df_carteira_crua = df_carteiras[df_carteiras['Carteira'] == carteira_ativa].copy()

coluna_carteira = 'Carteira'
coluna_valor = 'Valor'
coluna_cobranca = 'COBRANÇA'
coluna_cliente = 'N Fantasia'
coluna_cnpj = 'CNPJ/CPF'
coluna_id = 'ID_Único'
coluna_grupo = 'Grupo Atendimento'
coluna_range = 'Range_Acompanhamento'
coluna_vencimento = 'Vencto real'
coluna_status = 'Status Atend'
coluna_tipo = 'Tipo'
coluna_data_relatorio = 'Data_Relatorio_Consolidada'

if coluna_valor in df_carteira_crua.columns:
    df_carteira_crua[coluna_valor] = df_carteira_crua[coluna_valor].astype(str).str.replace('R$', '', regex=False).str.strip()
    df_carteira_crua[coluna_valor] = df_carteira_crua[coluna_valor].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df_carteira_crua[coluna_valor] = pd.to_numeric(df_carteira_crua[coluna_valor], errors='coerce').fillna(0.0)

if coluna_status in df_carteira_crua.columns:
    df_carteira_crua[coluna_status] = pd.to_numeric(df_carteira_crua[coluna_status], errors='coerce').fillna(0).astype(int).astype(str)

if coluna_data_relatorio in df_carteira_crua.columns:
    df_carteira_crua['Data_Analise_dt'] = pd.to_datetime(df_carteira_crua[coluna_data_relatorio], errors='coerce', dayfirst=True)
    opcoes_data_relatorio = df_carteira_crua['Data_Analise_dt'].dropna().sort_values(ascending=False).dt.strftime('%d/%m/%Y').unique().tolist()
else:
    df_carteira_crua['Data_Analise_dt'] = pd.NaT
    opcoes_data_relatorio = []

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
    df_carteira_crua['Mes_Filtro'], df_carteira_crua['Data_Exata'], df_carteira_crua['Mes_Grafico'] = 'Sem Data', 'Sem Data', 'Sem Data'
    opcoes_mes, opcoes_dia = ['Sem Data'], ['Sem Data']

# -------------------------------------------------------------------------
# CONSTRUÇÃO DOS FILTROS INTERATIVOS GERAIS
# -------------------------------------------------------------------------
st.sidebar.markdown("### 📅 Retrato da Base")
if opcoes_data_relatorio:
    sel_data_relatorio_str = st.sidebar.selectbox("Data do Relatório:", options=opcoes_data_relatorio)
    sel_data_relatorio_dt = pd.to_datetime(sel_data_relatorio_str, format='%d/%m/%Y')
else:
    sel_data_relatorio_str = "Sem Data"
    sel_data_relatorio_dt = None

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Segmentação")

if carteira_ativa == "Geral" and coluna_carteira in df_carteira_crua.columns:
    opcoes_carteira = sorted([str(x) for x in df_carteira_crua[coluna_carteira].dropna().unique()])
    sel_carteira = st.sidebar.multiselect("⭐ CARTEIRA (Master):", options=opcoes_carteira, placeholder="Todas")
    st.sidebar.divider()
else: sel_carteira = []

if coluna_cobranca in df_carteira_crua.columns:
    opcoes_cobranca = sorted([str(x) for x in df_carteira_crua[coluna_cobranca].dropna().unique()])
    sel_cobranca = st.sidebar.multiselect("1. COBRANÇA:", options=opcoes_cobranca, placeholder="Todos")
else: sel_cobranca = []

if coluna_cliente in df_carteira_crua.columns:
    opcoes_cliente = sorted([str(x) for x in df_carteira_crua[coluna_cliente].dropna().unique()])
    sel_cliente = st.sidebar.multiselect("2. CLIENTE:", options=opcoes_cliente, placeholder="Todos")
else: sel_cliente = []

if coluna_cnpj in df_carteira_crua.columns:
    opcoes_cnpj = sorted([str(x) for x in df_carteira_crua[coluna_cnpj].dropna().unique()])
    sel_cnpj = st.sidebar.multiselect("🔢 CNPJ/CPF:", options=opcoes_cnpj, placeholder="Todos")
else: sel_cnpj = []

if coluna_status in df_carteira_crua.columns:
    opcoes_status = sorted([str(x) for x in df_carteira_crua[coluna_status].unique()], key=int)
    sel_status = st.sidebar.multiselect("3. STATUS ATEND:", options=opcoes_status, placeholder="Todos")
else: sel_status = []

if coluna_grupo in df_carteira_crua.columns:
    opcoes_grupo = sorted([str(x) for x in df_carteira_crua[coluna_grupo].dropna().unique()])
    sel_grupo = st.sidebar.multiselect("4. GRUPO ATEND:", options=opcoes_grupo, placeholder="Todos")
else: sel_grupo = []

if coluna_range in df_carteira_crua.columns:
    opcoes_range = sorted([str(x) for x in df_carteira_crua[coluna_range].dropna().unique()])
    sel_range = st.sidebar.multiselect("5. RANGE ACOMPANHAMENTO:", options=opcoes_range, placeholder="Todos")
else: sel_range = []

sel_mes = st.sidebar.multiselect("6. MÊS VENCIMENTO:", options=opcoes_mes, placeholder="Todos")
sel_dia = st.sidebar.multiselect("7. DIA VENCIMENTO:", options=opcoes_dia, placeholder="Todos")

# -------------------------------------------------------------------------
# APLICANDO FILTROS GERAIS
# -------------------------------------------------------------------------
df_filtrado = df_carteira_crua.copy()
if sel_carteira: df_filtrado = df_filtrado[df_filtrado[coluna_carteira].astype(str).isin(sel_carteira)]
if sel_cobranca: df_filtrado = df_filtrado[df_filtrado[coluna_cobranca].astype(str).isin(sel_cobranca)]
if sel_cliente:  df_filtrado = df_filtrado[df_filtrado[coluna_cliente].astype(str).isin(sel_cliente)]
if sel_cnpj:     df_filtrado = df_filtrado[df_filtrado[coluna_cnpj].astype(str).isin(sel_cnpj)]
if sel_status:   df_filtrado = df_filtrado[df_filtrado[coluna_status].astype(str).isin(sel_status)]
if sel_grupo:    df_filtrado = df_filtrado[df_filtrado[coluna_grupo].astype(str).isin(sel_grupo)]
if sel_range:    df_filtrado = df_filtrado[df_filtrado[coluna_range].astype(str).isin(sel_range)]
if sel_mes:      df_filtrado = df_filtrado[df_filtrado['Mes_Filtro'].astype(str).isin(sel_mes)]
if sel_dia:      df_filtrado = df_filtrado[df_filtrado['Data_Exata'].astype(str).isin(sel_dia)]

# -------------------------------------------------------------------------
# MOTOR DE SNAPSHOTS E DELTAS DE KPI
# -------------------------------------------------------------------------
df_atual = pd.DataFrame(columns=df_filtrado.columns)
df_anterior = pd.DataFrame(columns=df_filtrado.columns)

if sel_data_relatorio_dt is not None:
    datas_unicas = df_carteira_crua['Data_Analise_dt'].dropna().sort_values().unique()
    df_atual = df_filtrado[df_filtrado['Data_Analise_dt'] == sel_data_relatorio_dt].copy()
    
    datas_anteriores = [d for d in datas_unicas if d < sel_data_relatorio_dt]
    if datas_anteriores:
        data_anterior_dt = datas_anteriores[-1]
        df_anterior = df_filtrado[df_filtrado['Data_Analise_dt'] == data_anterior_dt].copy()
else:
    df_atual = df_filtrado.copy()

def calcular_kpis(df_alvo):
    if df_alvo.empty: return 0.0, 0, 0, 0.0, 0.0
    v_total = df_alvo[coluna_valor].sum() if coluna_valor in df_alvo.columns else 0.0
    q_tit = df_alvo[coluna_id].nunique() if coluna_id in df_alvo.columns else len(df_alvo)
    q_cli = df_alvo[coluna_cliente].nunique() if coluna_cliente in df_alvo.columns else 0
    v_cob, v_incob = 0.0, 0.0
    if coluna_cobranca in df_alvo.columns and coluna_valor in df_alvo.columns:
        serie = df_alvo[coluna_cobranca].astype(str).str.strip().str.lower()
        f_cob = serie.str.contains('cobrável|cobravel', regex=True, na=False) & ~serie.str.contains('incobrável|incobravel', regex=True, na=False)
        f_incob = serie.str.contains('incobrável|incobravel', regex=True, na=False)
        v_cob = df_alvo[f_cob][coluna_valor].sum()
        v_incob = df_alvo[f_incob][coluna_valor].sum()
    return v_total, q_tit, q_cli, v_cob, v_incob

t_geral, q_titulos, q_clientes, v_cobravel, v_incobravel = calcular_kpis(df_atual)
t_geral_ant, q_titulos_ant, q_clientes_ant, v_cobravel_ant, v_incobravel_ant = calcular_kpis(df_anterior)

def formatar_delta(atual, anterior):
    if anterior == 0 or pd.isna(anterior): return None
    return f"{((atual - anterior) / anterior) * 100:+.1f}%"

df_filtrado_final = df_atual.copy()

if coluna_tipo in df_filtrado_final.columns:
    df_filtrado_final[coluna_tipo] = df_filtrado_final[coluna_tipo].astype(str).str.strip().str.upper()
    df_graficos_filtrados = df_filtrado_final[df_filtrado_final[coluna_tipo].isin(['NF', 'BOL'])].copy()
else:
    df_graficos_filtrados = df_filtrado_final.copy()

# =============================================================================
# 5. CONSTRUÇÃO DA INTERFACE GRÁFICA ORGANIZADA (PREMIUM)
# =============================================================================
nome_carteira = 'VISÃO GERAL (MASTER)' if carteira_ativa == 'Geral' else f'Carteira {carteira_ativa}'

# Cabeçalho Elegante
col_titulo, col_data = st.columns([3, 1])
with col_titulo:
    st.markdown(f"<h1 style='color: #4CAF50;'>Controle de Inadimplência</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='color: #bbb;'>{nome_carteira}</h4>", unsafe_allow_html=True)
with col_data:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info(f"📅 **Relatório Base:** {sel_data_relatorio_str}")

st.divider()

# KPIs Superiores com design injetado via CSS
g1, g2, g3 = st.columns(3)
with g1:
    st.metric(label="💰 Total Geral (Valor Líq)", value=f"R$ {t_geral:,.2f}", delta=formatar_delta(t_geral, t_geral_ant), delta_color="inverse")
with g2:
    st.metric(label="📄 Quantidade de Títulos", value=f"{q_titulos:,}".replace(",", "."), delta=formatar_delta(q_titulos, q_titulos_ant), delta_color="inverse")
with g3:
    st.metric(label="👥 Quantidade de Clientes", value=f"{q_clientes:,}".replace(",", "."), delta=formatar_delta(q_clientes, q_clientes_ant), delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
        
g4, g5 = st.columns(2)
with g4:
    st.metric(label="🟢 Total Cobrável", value=f"R$ {v_cobravel:,.2f}", delta=formatar_delta(v_cobravel, v_cobravel_ant), delta_color="inverse")
with g5:
    st.metric(label="🔴 Total Incobrável", value=f"R$ {v_incobravel:,.2f}", delta=formatar_delta(v_incobravel, v_incobravel_ant), delta_color="inverse")
        
st.divider()

if coluna_cliente in df_filtrado_final.columns:
    st.markdown("### 🏢 Concentração de Inadimplência por Clientes")
    with st.container(height=600, border=True):
        df_g1 = df_filtrado_final.groupby(coluna_cliente)[coluna_valor].sum().reset_index()
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

st.divider()

col_pizza1, col_pizza2 = st.columns(2)

with col_pizza1:
    st.markdown("#### 📌 Distribuição por Grupo Atendimento")
    with st.container(height=480, border=True): 
        if coluna_grupo in df_graficos_filtrados.columns:
            df_g2 = df_graficos_filtrados.groupby(coluna_grupo)[coluna_valor].sum().reset_index()
            cores_pizza = ['#17a2b8', '#4CAF50', '#20c997', '#0e76a8']
            
            total_g2 = df_g2[coluna_valor].sum() if not df_g2.empty else 1
            df_g2['Legenda'] = df_g2.apply(lambda r: f"{r[coluna_grupo]} (R$ {r[coluna_valor]:,.2f} | {(r[coluna_valor]/total_g2)*100:.1f}%)", axis=1)
            
            fig2 = px.pie(
                df_g2, values=coluna_valor, names='Legenda', hole=0.4, # Transformei em gráfico de rosca (fica mais moderno)
                template="plotly_dark", height=430, color_discrete_sequence=cores_pizza
            )
            fig2.update_traces(textinfo='percent', textfont=dict(size=12, color='white'))
            fig2.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), margin=dict(l=10, r=10, t=20, b=100))
            st.plotly_chart(fig2, use_container_width=True)

with col_pizza2:
    st.markdown("#### 📌 Distribuição por Acompanhamento")
    with st.container(height=480, border=True):
        if coluna_range in df_graficos_filtrados.columns:
            df_g3 = df_graficos_filtrados.groupby(coluna_range)[coluna_valor].sum().reset_index()
            cores_pizza_3 = ['#0e76a8', '#17a2b8', '#4CAF50', '#20c997']
            
            total_g3 = df_g3[coluna_valor].sum() if not df_g3.empty else 1
            df_g3['Legenda'] = df_g3.apply(lambda r: f"{r[coluna_range]} (R$ {r[coluna_valor]:,.2f} | {(r[coluna_valor]/total_g3)*100:.1f}%)", axis=1)
            
            fig3 = px.pie(
                df_g3, values=coluna_valor, names='Legenda', hole=0.4,
                template="plotly_dark", height=430, color_discrete_sequence=cores_pizza_3
            )
            fig3.update_traces(textinfo='percent', textfont=dict(size=12, color='white'))
            fig3.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5), margin=dict(l=10, r=10, t=20, b=100))
            st.plotly_chart(fig3, use_container_width=True)

st.divider()

col_baixo1, col_baixo2 = st.columns(2)

with col_baixo1:
    st.markdown("#### 🗓️ Valor Vencido por Mês (TOTAL)")
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
            except: pass

with col_baixo2:
    st.markdown("#### 🚦 Valor por Status de Atendimento")
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

st.divider()

# -------------------------------------------------------------------------
# LINHA 4 DE GRÁFICOS: MÉDIA MENSAL DA INADIMPLÊNCIA GERAL
# -------------------------------------------------------------------------
st.markdown("#### 📈 Histórico: Média Mensal da Inadimplência Geral")
with st.container(height=450, border=True):
    if 'Data_Analise_dt' in df_filtrado.columns and not df_filtrado['Data_Analise_dt'].isna().all():
        try:
            df_historico = df_filtrado.copy()
            df_historico['Dia_Relatorio'] = df_historico['Data_Analise_dt'].dt.date
            df_totais_diarios = df_historico.groupby('Dia_Relatorio')[coluna_valor].sum().reset_index()
            
            df_totais_diarios['Dia_Relatorio'] = pd.to_datetime(df_totais_diarios['Dia_Relatorio'])
            df_totais_diarios['Mes_Relatorio'] = df_totais_diarios['Dia_Relatorio'].dt.strftime('%Y-%m')
            
            df_media_mensal = df_totais_diarios.groupby('Mes_Relatorio')[coluna_valor].mean().reset_index()
            df_media_mensal = df_media_mensal.sort_values(by='Mes_Relatorio', ascending=True)
            
            df_media_mensal['Mes_Exibicao'] = df_media_mensal['Mes_Relatorio'].apply(lambda x: f"{x[-2:]}/{x[:4]}")
            
            fig_media_geral = px.bar(
                df_media_mensal, x='Mes_Exibicao', y=coluna_valor, orientation='v', 
                template="plotly_dark", height=400, text=coluna_valor,
                color_discrete_sequence=['#17a2b8']
            )
            
            fig_media_geral.update_xaxes(type='category', title=None, categoryorder='array', categoryarray=df_media_mensal['Mes_Exibicao'])
            fig_media_geral.update_yaxes(showticklabels=False, title=None, showgrid=False)
            fig_media_geral.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside', cliponaxis=False, textfont=dict(color='white', size=11))
            fig_media_geral.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            
            st.plotly_chart(fig_media_geral, use_container_width=True)
        except Exception as e: 
            pass

st.markdown("<br><br>", unsafe_allow_html=True) # Dá um respiro antes da tabela

# =============================================================================
# PAINEL RETRÁTIL (EXPANDER) PARA A TABELA DE DADOS E EXPORTAÇÃO
# =============================================================================
with st.expander("🗃️ Ver Base de Dados Detalhada e Exportar para Excel"):
    st.markdown("Aqui você pode verificar os dados analíticos e fazer o download da base.")
    
    colunas_desejadas = [
        'No. Titulo', 'Tipo', 'CNPJ/CPF', 'Valor', 'N Fantasia',
        'DT Emissao', 'Vencto real', 'Carteira', 'COBRANÇA',
        'Status Atend', 'Grupo Atendimento', 'Range_Acompanhamento',
    ]

    colunas_para_exibir = [col for col in colunas_desejadas if col in df_filtrado_final.columns]

    st.dataframe(df_filtrado_final[colunas_para_exibir], use_container_width=True, hide_index=True)

    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_filtrado_final[colunas_para_exibir].to_excel(writer, index=False, sheet_name='Inadimplencia')
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Baixar Planilha (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"Relatorio_Inadimplencia_Carteira_{carteira_ativa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    except Exception as e:
        st.warning("Para habilitar o download em Excel, adicione 'openpyxl' no arquivo requirements.txt")
