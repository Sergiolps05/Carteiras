#  BI Análise e Gestão de Carteiras de Inadimplência

Um dashboard financeiro interativo desenvolvido em Python para monitoramento de carteiras, gestão de inadimplência e análise de performance de cobrança. 

Este projeto foi desenhado para resolver um gargalo real de infraestrutura: **distribuir um BI dinâmico para usuários sem licenças de ferramentas tradicionais (como Power BI) e sem Python instalado na máquina.** O painel foi empacotado como um executável (`.exe`) e utiliza uma arquitetura híbrida de dados.

##  Objetivo do Negócio
Fornecer à diretoria e aos analistas de cobrança uma visão diária e histórica da saúde das carteiras. O dashboard automatiza o cálculo de variação (Δ%) dia a dia, identifica os maiores devedores (Top 6) e exibe o fechamento médio mensal, tudo segmentado por setores estratégicos (Jurídico, Assessorias, Perdas, etc.).

##  Arquitetura Híbrida de Dados
O grande diferencial deste projeto é a integração fluida entre ambientes restritos e a nuvem:
1. **Dados Sensíveis (On-Premise):** A base principal transacional (`.xlsx`) é consumida diretamente de um diretório de rede compartilhado corporativo (`\\SERVIDOR\...`), garantindo segurança e conformidade.
2. **Parâmetros Dinâmicos (Cloud):** Utilização nativa da integração com **Google Sheets** via Streamlit (`st.connection('gsheets')`) para importar premissas, metas ou regras de negócio gerenciadas pela equipe na nuvem, sem precisar alterar a base local.

##  Stack Tecnológico
* **Linguagem & Boas Práticas:** Python 3.13 (código estruturado seguindo o padrão PEP 8 para legibilidade e manutenção).
* **Engenharia de Dados (ETL):** [Pandas](https://pandas.pydata.org/) (DataFrames, Type Casting rigoroso e limpeza de nulos para garantir a matemática dos Deltas) e Openpyxl.
* **Front-end & Visualização:** [Streamlit](https://streamlit.io/) (Interface responsiva, `st.cache_data` para performance) e [Plotly Express](https://plotly.com/python/) (Gráficos interativos em vez de estáticos).
* **Deploy / Empacotamento:** PyInstaller + `stcli.main()` (Criação de standalone `.exe` em ambiente Windows).

##  Principais Funcionalidades
* **Análise de Variação (Delta Histórico):** Algoritmo que identifica automaticamente o último dia útil processado no histórico e compara com o dia atual para exibir percentuais de queda ou aumento da inadimplência.
* **Agrupamento Automático (Setorização):** Conversão em tempo de execução de códigos numéricos ERP em categorias de negócio legíveis ("Processos Jurídicos", "Recuperação Judicial").
* **Múltiplas Visões (Geral vs Carteira):** Gráficos paralelos permitindo comparar o desempenho de uma carteira específica contra o macro da empresa.
* **Integração Cloud:** Blend de dados locais do Excel com o Google Sheets em tempo real.

##  Como Executar o Projeto

### Modo Desenvolvedor (Local)
1. Clone este repositório e crie um ambiente virtual (`.venv`).
2. Instale as dependências:
   ```bash
   pip install streamlit pandas plotly openpyxl st-gsheets-connection
