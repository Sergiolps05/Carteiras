import pandas as pd
import streamlit as st
import plotly.express as px
import io 

# =============================================================================
# 1. CONFIGURAÇÕES DA PÁGINA E UI/UX (Layouts Streamlit)
# =============================================================================
st.set_page_config(
    page_title="Dashboard Inadimplência - Carteiras",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded" 
)

estilo_premium = """
    <style>
    /* Esconde ações do topo direito (Deploy, GitHub), preservando o botão da sidebar */
    [data-testid="stToolbarActions"] {visibility: hidden !important;}
    .stDeployButton {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* GARANTE que o botão de abrir os filtros (canto esquerdo) fique sempre visível */
    [data-testid="collapsedControl"] {visibility: visible !important; display: block !important;}
    
    /* UI Premium: Cards flutuantes para KPIs */
    [data-testid="stMetric"] {
        background-color: #262730 !important; 
        border-radius: 10px !important;
        padding: 15px 20px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3) !important;
        border-left: 5px solid #4CAF50 !important; 
    }
    [data-testid="stMetricValue"] {
        margin-top: 10px !important;
    }
    </style>
"""
st.markdown(estilo_premium, unsafe_allow_html=True)

# MODO DE SEGURANÇA: Evita a tela branca se os secrets falharem
try:
    URL_SHEETS = st.secrets["URL_PLANILHA"]
except KeyError:
    st.error("🚨 ERRO CRÍTICO: A variável 'URL_PLANILHA' não foi encontrada nos Secrets!")
    st.stop()
except Exception as e:
    st.error(f"🚨 ERRO NOS SECRETS: {e}")
    st.stop()

# =============================================================================
# 2. ENGENHARIA DE DADOS (Pandas & Cache)
# =============================================================================
@st.cache_data(ttl=600)
def carregar_dados_sheets(url: str) -> pd.DataFrame:
    try:
        # CORREÇÃO CRÍTICA APLICADA AQUI (low_memory=False)
        df = pd.read_csv(url, dtype={'Carteira': str, 'Parcela': str}, low_memory=False)
        df.columns = df.columns.str.strip() 
        if 'Carteira' in df.columns:
            df['Carteira'] = df['Carteira'].astype(str).str.strip().str.zfill(2)
        return df
    except Exception as e:
        st.error(f"Falha na integração com a base de dados: {e}")
        return pd.DataFrame()

df_carteiras = carregar_dados_sheets(URL_SHEETS)

# =============================================================================
# 3. GOVERNANÇA E SEGURANÇA (Session State)
# =============================================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["carteira_ativa"] = "Bloqueado"

if not st.session_state["autenticado"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True): 
            st.markdown("<h2 style='text-align: center;'> Visualização Inadimplência</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888;'>Insira a sua credencial para acessar a carteira</p>", unsafe_allow_html=True)
            st.divider()
            
            senha_digitada = st.text_input("Senha de Acesso:", type="password")
            
            if st.button("Entrar no Sistema", type="primary", width="stretch"):
                if "tokens" in st.secrets and senha_digitada in st.secrets["tokens"]:
                    st.session_state["autenticado"] = True
                    st.session_state["carteira_ativa"] = st.secrets["tokens"][senha_digitada]
                    st.rerun()
                else:
                    st.error("❌ Credencial incorreta ou acesso negado.")
    st.stop()  

carteira_ativa = st.session_state["carteira_ativa"]
carteira_ativa = "Geral" if str(carteira_ativa).lower() == "geral" else str(carteira_ativa).strip().zfill(2)

st.sidebar.button("🚪 Encerrar Sessão", width="stretch", on_click=lambda: st.session_state.clear() or st.rerun())
st.sidebar.divider()

# =============================================================================
# 4. TRATAMENTO E MODELAGEM DE DADOS (Limpeza Vetorizada)
# =============================================================================
df_carteira_crua = df_carteiras.copy() if carteira_ativa == "Geral" else df_carteiras[df_carteiras['Carteira'] == carteira_ativa].copy()

coluna_valor = 'Valor'
coluna_status = 'Status Atend'
coluna_data_relatorio = 'Data_Relatorio_Consolidada'
coluna_vencimento = 'Vencto real'

if coluna_valor in df_carteira_crua.columns:
    df_carteira_crua[coluna_valor] = pd.to_numeric(
        df_carteira_crua[coluna_valor].astype(str).str.replace('R$', '', regex=False)
        .str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce'
    ).fillna(0.0)

if coluna_status in df_carteira_crua.columns:
    df_carteira_crua[coluna_status] = pd.to_numeric(df_carteira_crua[coluna_status], errors='coerce').fillna(0).astype(int).astype(str)

if coluna_data_relatorio in df_carteira_crua.columns:
    df_carteira_crua['Data_Analise_dt'] = pd.to_datetime(df_carteira_crua[coluna_data_relatorio], errors='coerce', dayfirst=True)
    opcoes_data_relatorio = df_carteira_crua['Data_Analise_dt'].dropna().sort_values(ascending=False).dt.strftime('%d/%m/%Y').unique().tolist()
else:
    df_carteira_crua['Data_Analise_dt'] = pd.NaT
    opcoes_data_relatorio = []

if coluna_vencimento in df_carteira_crua.columns:
    datas_venc = pd.to_datetime(df_carteira_crua[coluna_vencimento], errors='coerce', dayfirst=True)
    df_carteira_crua['Mes_Filtro'] = datas_venc.dt.strftime('%m/%Y').fillna('Sem Data')
    df_carteira_crua['Data_Exata'] = datas_venc.dt.strftime('%d/%m/%Y').fillna('Sem Data')
    df_carteira_crua['Mes_Grafico'] = datas_venc.dt.strftime('%Y-%m').fillna('Sem Data')
else:
    df_carteira_crua['Mes_Filtro'] = df_carteira_crua['Data_Exata'] = df_carteira_crua['Mes_Grafico'] = 'Sem Data'

# -------------------------------------------------------------------------
# FILTROS LATERAIS INTERATIVOS
# -------------------------------------------------------------------------
st.sidebar.markdown("###  Dia do relatório")
sel_data_relatorio_str = st.sidebar.selectbox("Data do Relatório:", options=opcoes_data_relatorio) if opcoes_data_relatorio else "Sem Data"
sel_data_relatorio_dt = pd.to_datetime(sel_data_relatorio_str, format='%d/%m/%Y') if sel_data_relatorio_str != "Sem Data" else None

st.sidebar.divider()
st.sidebar.markdown("###  Filtros")

def criar_filtro(coluna, label):
    if coluna in df_carteira_crua.columns:
        opcoes = sorted([str(x) for x in df_carteira_crua[coluna].dropna().unique()])
        return st.sidebar.multiselect(label, options=opcoes, placeholder="Todos")
    return []

sel_carteira = criar_filtro('Carteira', " CARTEIRA:") if carteira_ativa == "Geral" else []
sel_cobranca = criar_filtro('COBRANÇA', "1. COBRANÇA:")
sel_cliente = criar_filtro('N Fantasia', "2. CLIENTE:")
sel_cnpj = criar_filtro('CNPJ/CPF', "3. CNPJ/CPF:")
sel_status = criar_filtro('Status Atend', "4. STATUS ATEND:")
sel_grupo = criar_filtro('Grupo Atendimento', "5. GRUPO ATEND:")
sel_range = criar_filtro('Range_Acompanhamento', "6. RANGE ACOMPANHAMENTO:")

opcoes_mes = sorted([str(x) for x in df_carteira_crua['Mes_Filtro'].unique()])
sel_mes = st.sidebar.multiselect("7. MÊS VENCIMENTO:", options=opcoes_mes, placeholder="Todos")

opcoes_dia = sorted([str(x) for x in df_carteira_crua['Data_Exata'].unique()])
sel_dia = st.sidebar.multiselect("8. DIA VENCIMENTO:", options=opcoes_dia, placeholder="Todos")

sel_prefixo = criar_filtro('Prefixo', "9. PREFIXO:")

# -------------------------------------------------------------------------
# APLICAÇÃO DE FILTROS E CONSTRUÇÃO DE DELTAS
# -------------------------------------------------------------------------
df_filtrado = df_carteira_crua.copy()
if sel_carteira: df_filtrado = df_filtrado[df_filtrado['Carteira'].astype(str).isin(sel_carteira)]
if sel_cobranca: df_filtrado = df_filtrado[df_filtrado['COBRANÇA'].astype(str).isin(sel_cobranca)]
if sel_cliente:  df_filtrado = df_filtrado[df_filtrado['N Fantasia'].astype(str).isin(sel_cliente)]
if sel_cnpj:     df_filtrado = df_filtrado[df_filtrado['CNPJ/CPF'].astype(str).isin(sel_cnpj)]
if sel_status:   df_filtrado = df_filtrado[df_filtrado['Status Atend'].astype(str).isin(sel_status)]
if sel_grupo:    df_filtrado = df_filtrado[df_filtrado['Grupo Atendimento'].astype(str).isin(sel_grupo)]
if sel_range:    df_filtrado = df_filtrado[df_filtrado['Range_Acompanhamento'].astype(str).isin(sel_range)]
if sel_mes:      df_filtrado = df_filtrado[df_filtrado['Mes_Filtro'].astype(str).isin(sel_mes)]
if sel_dia:      df_filtrado = df_filtrado[df_filtrado['Data_Exata'].astype(str).isin(sel_dia)]
if sel_prefixo:  df_filtrado = df_filtrado[df_filtrado['Prefixo'].astype(str).isin(sel_prefixo)]
    
df_atual = df_filtrado[df_filtrado['Data_Analise_dt'] == sel_data_relatorio_dt].copy() if sel_data_relatorio_dt else df_filtrado.copy()
df_anterior = pd.DataFrame(columns=df_filtrado.columns)

if sel_data_relatorio_dt is not None:
    datas_anteriores = [d for d in df_carteira_crua['Data_Analise_dt'].dropna().unique() if d < sel_data_relatorio_dt]
    if datas_anteriores:
        df_anterior = df_filtrado[df_filtrado['Data_Analise_dt'] == max(datas_anteriores)].copy()

def calcular_kpis(df_alvo):
    if df_alvo.empty: return 0.0, 0, 0, 0.0, 0.0
    
    v_total = df_alvo[coluna_valor].sum() if coluna_valor in df_alvo.columns else 0.0
    
    if 'Tipo' in df_alvo.columns and 'ID_Único' in df_alvo.columns:
        tipos_formatados = df_alvo['Tipo'].astype(str).str.strip().str.upper()
        df_apenas_titulos = df_alvo[tipos_formatados.isin(['NF', 'BOL'])]
        q_tit = df_apenas_titulos['ID_Único'].nunique()
    elif 'ID_Único' in df_alvo.columns:
        q_tit = df_alvo['ID_Único'].nunique()
    else:
        q_tit = len(df_alvo)
    
    q_cli = df_alvo['N Fantasia'].nunique() if 'N Fantasia' in df_alvo.columns else 0
    
    v_cob, v_incob = 0.0, 0.0
    if 'COBRANÇA' in df_alvo.columns:
        serie = df_alvo['COBRANÇA'].astype(str).str.strip().str.lower()
        f_cob = serie.str.contains('cobrável|cobravel', regex=True, na=False) & ~serie.str.contains('incobrável|incobravel', regex=True, na=False)
        f_incob = serie.str.contains('incobrável|incobravel', regex=True, na=False)
        v_cob, v_incob = df_alvo[f_cob][coluna_valor].sum(), df_alvo[f_incob][coluna_valor].sum()
        
    return v_total, q_tit, q_cli, v_cob, v_incob

t_geral, q_titulos, q_clientes, v_cobravel, v_incobravel = calcular_kpis(df_atual)
t_geral_ant, q_titulos_ant, q_clientes_ant, v_cobravel_ant, v_incobravel_ant = calcular_kpis(df_anterior)

calc_delta = lambda at, ant: f"{((at - ant) / ant) * 100:+.1f}%" if ant else None

# =============================================================================
# 5. VISUALIZAÇÃO DE DADOS (Plotly Express)
# =============================================================================
st.markdown(f"<h1 style='color: #4CAF50;'>Controle de Inadimplência</h1>", unsafe_allow_html=True)
st.markdown(f"<h4 style='color: #bbb;'>{carteira_ativa if carteira_ativa == 'Geral' else f'Carteira {carteira_ativa}'}</h4>", unsafe_allow_html=True)

g1, g2, g3 = st.columns(3)
g1.metric("💰 Total Geral (Valor Líq)", f"R$ {t_geral:,.2f}", calc_delta(t_geral, t_geral_ant), delta_color="inverse")
g2.metric("📄 Quantidade de Títulos", f"{q_titulos:,}".replace(",", "."), calc_delta(q_titulos, q_titulos_ant), delta_color="inverse")
g3.metric("👥 Quantidade de Clientes", f"{q_clientes:,}".replace(",", "."), calc_delta(q_clientes, q_clientes_ant), delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)
g4, g5 = st.columns(2)
g4.metric("🟢 Total Cobrável", f"R$ {v_cobravel:,.2f}", calc_delta(v_cobravel, v_cobravel_ant), delta_color="inverse")
g5.metric("🔴 Total Incobrável", f"R$ {v_incobravel:,.2f}", calc_delta(v_incobravel, v_incobravel_ant), delta_color="inverse")
st.divider()

# -------------------------------------------------------------------------
# 1. GRÁFICO DE CLIENTES (COM BARRA DE ROLAGEM)
# -------------------------------------------------------------------------
if 'N Fantasia' in df_atual.columns and not df_atual.empty:
    st.markdown("###  Concentração de Inadimplência por Clientes")
    with st.container(height=600, border=True):
        df_g1 = df_atual.groupby('N Fantasia')[coluna_valor].sum().reset_index().sort_values(coluna_valor)
        
        altura_interna_g1 = max(550, len(df_g1) * 35)
        
        fig1 = px.bar(df_g1, x=coluna_valor, y='N Fantasia', orientation='h', template="plotly_dark", 
                      height=altura_interna_g1, color_discrete_sequence=['#4CAF50'], text=coluna_valor)
        
        fig1.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', textfont=dict(color='white', size=11))
        fig1.update_layout(xaxis_showticklabels=False, xaxis_title=None, yaxis_title=None, margin=dict(l=220, r=40, t=10, b=10))
        st.plotly_chart(fig1, width="stretch")

st.divider()

# -------------------------------------------------------------------------
# 2. GRÁFICOS DE ROSCA (GRUPO E ACOMPANHAMENTO)
# -------------------------------------------------------------------------
col_p1, col_p2 = st.columns(2)
with col_p1:
    st.markdown("####  Distribuição por Grupo Atendimento")
    with st.container(height=480, border=True):
        if 'Grupo Atendimento' in df_atual.columns and not df_atual.empty:
            df_g2 = df_atual.groupby('Grupo Atendimento')[coluna_valor].sum().reset_index()
            
            total_g2 = df_g2[coluna_valor].sum() if not df_g2.empty else 1
            df_g2['Legenda'] = df_g2.apply(lambda r: f"{r['Grupo Atendimento']} (R$ {r[coluna_valor]:,.2f} | {(r[coluna_valor]/total_g2)*100:.1f}%)", axis=1)
            
            fig2 = px.pie(df_g2, values=coluna_valor, names='Legenda', hole=0.4, template="plotly_dark",
                          color_discrete_sequence=['#17a2b8', '#4CAF50', '#20c997', '#0e76a8'])
            fig2.update_traces(textinfo='percent', textfont=dict(size=12, color='white'))
            fig2.update_layout(legend=dict(orientation="h", y=-0.1, xanchor="center", x=0.5))
            st.plotly_chart(fig2, width="stretch")

with col_p2:
    st.markdown("####  Distribuição por Acompanhamento")
    with st.container(height=480, border=True):
        if 'Range_Acompanhamento' in df_atual.columns and not df_atual.empty:
            df_g3 = df_atual.groupby('Range_Acompanhamento')[coluna_valor].sum().reset_index()
            
            total_g3 = df_g3[coluna_valor].sum() if not df_g3.empty else 1
            df_g3['Legenda'] = df_g3.apply(lambda r: f"{r['Range_Acompanhamento']} (R$ {r[coluna_valor]:,.2f} | {(r[coluna_valor]/total_g3)*100:.1f}%)", axis=1)
            
            fig3 = px.pie(df_g3, values=coluna_valor, names='Legenda', hole=0.4, template="plotly_dark",
                          color_discrete_sequence=['#0e76a8', '#17a2b8', '#4CAF50', '#20c997'])
            fig3.update_traces(textinfo='percent', textfont=dict(size=12, color='white'))
            fig3.update_layout(legend=dict(orientation="h", y=-0.1, xanchor="center", x=0.5))
            st.plotly_chart(fig3, width="stretch")

# -------------------------------------------------------------------------
# 3. GRÁFICOS DE MÊS E STATUS 
# -------------------------------------------------------------------------
col_baixo1, col_baixo2 = st.columns(2)

with col_baixo1:
    st.markdown("####  Valor Vencido por Mês (TOTAL)")
    with st.container(height=450, border=True):
        if 'Mes_Grafico' in df_atual.columns:
            try:
                df_g4 = df_atual.groupby('Mes_Grafico')[coluna_valor].sum().reset_index()
                df_g4 = df_g4.sort_values(by='Mes_Grafico', ascending=True)
                df_g4['Mes_Exibicao'] = df_g4['Mes_Grafico'].apply(lambda x: f"{x[-2:]}/{x[:4]}" if x != 'Sem Data' else x)
                
                altura_interna_g4 = max(400, len(df_g4) * 35)
                
                fig4 = px.bar(
                    df_g4, x=coluna_valor, y='Mes_Exibicao', orientation='h', 
                    template="plotly_dark", height=altura_interna_g4, text=coluna_valor,
                    color_discrete_sequence=['#4CAF50']
                )
                fig4.update_yaxes(type='category', title=None, categoryorder='array', categoryarray=df_g4['Mes_Exibicao'])
                fig4.update_xaxes(showticklabels=False, title=None, showgrid=False)
                fig4.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', cliponaxis=False, textfont=dict(color='white', size=11))
                fig4.update_layout(margin=dict(l=100, r=40, t=10, b=10))
                st.plotly_chart(fig4, width="stretch")
            except: pass

with col_baixo2:
    st.markdown("#### 🚦 Valor por Status de Atendimento")
    with st.container(height=450, border=True):
        if coluna_status in df_atual.columns:
            df_graficos_status = df_atual.copy()
            df_graficos_status[coluna_status] = pd.to_numeric(df_graficos_status[coluna_status], errors='coerce').fillna(0).astype(int).astype(str)
            df_g5 = df_graficos_status.groupby(coluna_status)[coluna_valor].sum().reset_index()
            df_g5 = df_g5.sort_values(by=coluna_valor, ascending=True)
            
            altura_interna_g5 = max(400, len(df_g5) * 35)
            
            fig5 = px.bar(
                df_g5, x=coluna_valor, y=coluna_status, orientation='h', 
                template="plotly_dark", height=altura_interna_g5, text=coluna_valor,
                color_discrete_sequence=['#4CAF50']
            )
            fig5.update_yaxes(type='category', title=None)
            fig5.update_xaxes(showticklabels=False, title=None, showgrid=False)
            fig5.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', cliponaxis=False, textfont=dict(color='white', size=11))
            fig5.update_layout(coloraxis_showscale=False, margin=dict(l=100, r=40, t=10, b=10)) 
            st.plotly_chart(fig5, width="stretch")

st.divider()

# -------------------------------------------------------------------------
# 4. GRÁFICO DE HISTÓRICO: MÉDIA MENSAL DA INADIMPLÊNCIA GERAL
# -------------------------------------------------------------------------
# st.markdown("#### 📈 Histórico: Média Mensal da Inadimplência Geral")
# with st.container(height=450, border=True):
#     if 'Data_Analise_dt' in df_filtrado.columns and not df_filtrado['Data_Analise_dt'].isna().all():
#         try:
#             df_historico = df_filtrado.copy()
#             df_historico['Dia_Relatorio'] = df_historico['Data_Analise_dt'].dt.date
#             df_totais_diarios = df_historico.groupby('Dia_Relatorio')[coluna_valor].sum().reset_index()
            
#             df_totais_diarios['Dia_Relatorio'] = pd.to_datetime(df_totais_diarios['Dia_Relatorio'])
#             df_totais_diarios['Mes_Relatorio'] = df_totais_diarios['Dia_Relatorio'].dt.strftime('%Y-%m')
            
#             df_media_mensal = df_totais_diarios.groupby('Mes_Relatorio')[coluna_valor].mean().reset_index()
#             df_media_mensal = df_media_mensal.sort_values(by='Mes_Relatorio', ascending=True)
            
#             df_media_mensal['Mes_Exibicao'] = df_media_mensal['Mes_Relatorio'].apply(lambda x: f"{x[-2:]}/{x[:4]}")
            
#             fig_media_geral = px.bar(
#                 df_media_mensal, x='Mes_Exibicao', y=coluna_valor, orientation='v', 
#                 template="plotly_dark", height=400, text=coluna_valor,
#                 color_discrete_sequence=['#17a2b8']
#             )
            
#             fig_media_geral.update_xaxes(type='category', title=None, categoryorder='array', categoryarray=df_media_mensal['Mes_Exibicao'])
#             fig_media_geral.update_yaxes(showticklabels=False, title=None, showgrid=False)
#             fig_media_geral.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside', cliponaxis=False, textfont=dict(color='white', size=11))
#             fig_media_geral.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            
#             st.plotly_chart(fig_media_geral, width="stretch")
#         except Exception as e: 
#             pass

# st.markdown("<br><br>", unsafe_allow_html=True) 

# =============================================================================
# EXPORTAÇÃO E BI (Integração Openpyxl / Power BI)
# =============================================================================
with st.expander(" Ver Base de Dados Detalhada e Exportar para Excel"):
    st.markdown("Base higienizada pronta para exportação e modelagem.")
    col_exibir = ['No. Titulo', 'Tipo', 'CNPJ/CPF', 'Valor', 'N Fantasia', 'DT Emissao', 'Vencto real', 'Carteira', 'COBRANÇA', 'Status Atend', 'Grupo Atendimento', 'Range_Acompanhamento']
    col_validas = [c for c in col_exibir if c in df_atual.columns]
    
    st.dataframe(df_atual[col_validas], width="stretch", hide_index=True)

    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_atual[col_validas].to_excel(writer, index=False, sheet_name='Base_Tratada')
        
        st.download_button(
            label=" Baixar Planilha (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"Relatorio_Base_{carteira_ativa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            width="stretch"
        )
    except Exception:
        st.error("⚠️ Inclua 'openpyxl' no requirements.txt para habilitar o download.")
