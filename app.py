# -*- coding: utf-8 -*- # Define encoding
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Importa graph_objects
from plotly.subplots import make_subplots # Importa make_subplots
from datetime import datetime, date, timedelta
import numpy as np
import re
import io
import os

# --- Configuração da Página Streamlit ---
st.set_page_config(page_title="Análise de Fatura Itaú v2.1", page_icon="📊", layout="wide")

# --- Funções Auxiliares ---
# (limpar_valor, load_rules_from_excel, suggest_categories_v2, load_data, calculate_days_remaining)
# Mantidas como na versão anterior (v2.2)
def limpar_valor(valor):
    if isinstance(valor, (int, float)): return float(valor)
    if isinstance(valor, str):
        valor_limpo = re.sub(r'[R$\s]', '', valor).replace(',', '.')
        try: return float(valor_limpo)
        except ValueError:
             valor_limpo_alt = valor.replace('.', '').replace(',', '.')
             try: return float(valor_limpo_alt)
             except ValueError: return np.nan
    return np.nan

@st.cache_data
def load_rules_from_excel(file_path='regras_categorizacao.xlsx'):
    if not os.path.exists(file_path): st.warning(f"'{file_path}' não encontrado."); return {}
    try:
        df_rules = pd.read_excel(file_path, engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd'); col_keyword, col_cat1, col_cat2 = None, None, None; possible_keyword_cols = ['PalavraChave', 'Keyword', 'Chave']; possible_cat1_cols = ['CategoriaNivel1', 'CategoriaGeral', 'CatNivel1', 'Cat1']; possible_cat2_cols = ['CategoriaNivel2', 'CategoriaDetalhada', 'CatNivel2', 'Cat2']
        for col in possible_keyword_cols:
            if col in df_rules.columns: col_keyword = col; break
        for col in possible_cat1_cols:
            if col in df_rules.columns: col_cat1 = col; break
        for col in possible_cat2_cols:
            if col in df_rules.columns: col_cat2 = col; break
        if col_keyword is None or col_cat1 is None or col_cat2 is None: st.error(f"'{file_path}' deve conter '{possible_keyword_cols[0]}', '{possible_cat1_cols[0]}' e '{possible_cat2_cols[0]}'."); return {}
        df_rules = df_rules[[col_keyword, col_cat1, col_cat2]].copy(); df_rules[col_keyword] = df_rules[col_keyword].astype(str).str.lower().str.strip(); df_rules[col_cat1] = df_rules[col_cat1].astype(str).str.strip(); df_rules[col_cat2] = df_rules[col_cat2].fillna('N/A').astype(str).str.strip(); df_rules.replace({'N/A': None, '': None}, inplace=True); df_rules = df_rules[df_rules[col_keyword] != '']; df_rules['keyword_len'] = df_rules[col_keyword].str.len(); df_rules = df_rules.sort_values(by='keyword_len', ascending=False)
        rules_dict = {};
        for _, row in df_rules.iterrows(): rules_dict[row[col_keyword]] = {'Nivel1': row[col_cat1], 'Nivel2': row[col_cat2]}
        return rules_dict
    except Exception as e: st.error(f"Erro ao ler regras '{file_path}': {e}"); return {}

def suggest_categories_v2(description, rules_dict):
    cat_nivel1 = 'Não categorizado'; cat_nivel2 = None
    if not isinstance(description, str): return cat_nivel1, cat_nivel2
    description_lower = description.lower()
    parcelamento_match = re.search(r'\b(\d{1,2}/\d{1,2})\b', description)
    if parcelamento_match: parcela_info = parcelamento_match.group(1); cat_nivel1 = 'Parcelamento'; cat_nivel2 = f'Compra Parcelada ({parcela_info})'
    if rules_dict:
        for keyword, categories in rules_dict.items():
            keyword_found = False
            try:
                if re.search(r'\b' + re.escape(keyword) + r'\b', description_lower): keyword_found = True
            except re.error:
                 if keyword in description_lower: keyword_found = True
            if not keyword_found and keyword in description_lower: keyword_found = True
            if keyword_found:
                cat_nivel1_regra = categories.get('Nivel1', 'Não categorizado'); cat_nivel2_regra = categories.get('Nivel2')
                cat_nivel1 = cat_nivel1_regra
                if cat_nivel2_regra and (cat_nivel1 != 'Parcelamento' or cat_nivel1_regra == 'Parcelamento'): cat_nivel2 = cat_nivel2_regra
                break
    if cat_nivel2 is None and cat_nivel1 != 'Não categorizado' and cat_nivel1 != 'Parcelamento': cat_nivel2 = 'Geral'
    return cat_nivel1, cat_nivel2

def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            file_name = uploaded_file.name; engine = None
            if file_name.endswith('.xls'): engine = 'xlrd'
            elif file_name.endswith('.xlsx'): engine = 'openpyxl'
            df = pd.read_excel(uploaded_file, skiprows=24, engine=engine, sheet_name=0)

            colunas_necessarias = {'data': 'Data', 'lançamento': 'Descricao', 'valor': 'Valor'}
            colunas_possiveis = {'data': ['data', 'Data'], 'lançamento': ['lançamento', 'Lançamento', 'Descrição', 'Descricao', 'Estabelecimento'], 'valor': ['valor', 'Valor']}
            colunas_renomear = {}; colunas_faltando = []
            for col_padrao, nomes_possiveis in colunas_possiveis.items():
                col_encontrada = next((nome for nome in nomes_possiveis if nome in df.columns), None)
                if col_encontrada: colunas_renomear[col_encontrada] = colunas_necessarias[col_padrao]
                else: colunas_faltando.append(col_padrao)
            if colunas_faltando: st.error(f"Colunas essenciais não encontradas: {', '.join(colunas_faltando)}."); return None
            df = df.rename(columns=colunas_renomear)
            colunas_finais = list(colunas_necessarias.values())
            df = df[[col for col in colunas_finais if col in df.columns]]

            if 'Data' in df.columns:
                try:
                    df['Data_Limpada'] = df['Data'].astype(str).str.strip()
                    df['Data_Convertida'] = pd.to_datetime(df['Data_Limpada'], format='%d/%m/%Y', errors='coerce')
                    nan_count = df['Data_Convertida'].isnull().sum()
                    if nan_count == len(df) and len(df) > 0: st.error("Falha ao converter TODAS as datas (formato DD/MM/YYYY esperado).")
                    df['Data'] = df['Data_Convertida']
                    df.drop(columns=['Data_Limpada', 'Data_Convertida'], inplace=True, errors='ignore')
                except Exception as e: st.error(f"Erro CRÍTICO durante conversão da Data: {e}."); return None
            else: st.error("Coluna 'Data' não encontrada!"); return None

            df['Valor'] = df['Valor'].apply(limpar_valor)
            df['Descricao'] = df['Descricao'].astype(str)
            df = df[df['Descricao'].str.strip() != ''][df['Descricao'].str.lower() != 'nan']

            df['Categoria Nível 1'] = 'Não categorizado'
            df['Categoria Nível 2'] = None
            if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']) and not df['Data'].isnull().all():
                 df['MesAno'] = df['Data'].dt.to_period('M').astype(str)
            else: df['MesAno'] = 'N/A'

            if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']) and not df['Data'].isnull().all():
                 return df.sort_values(by='Data').reset_index(drop=True)
            else: return df.reset_index(drop=True)
        except Exception as e: st.error(f"Erro no processamento: {e}"); return None
    return None

def calculate_days_remaining(closing_day):
    # (Mantida como corrigida)
    today = datetime.today(); current_year = today.year; current_month = today.month
    if not 1 <= closing_day <= 31: return "Dia inválido"
    try: potential_closing_date = datetime(current_year, current_month, closing_day)
    except ValueError:
         next_month_dt = today + timedelta(days=35);
         try: potential_closing_date = next_month_dt.replace(day=closing_day)
         except ValueError: st.warning(f"Dia {closing_day} inválido."); return "Data Inválida"
    if today >= potential_closing_date.replace(hour=0, minute=0, second=0, microsecond=0):
         next_closing_dt = today + timedelta(days=35);
         try: next_closing_date = next_closing_dt.replace(day=closing_day)
         except ValueError: st.warning(f"Dia {closing_day} inválido."); return "Data Inválida"
    else: next_closing_date = potential_closing_date
    delta = next_closing_date.date() - today.date(); return delta.days


# --- CARREGA AS REGRAS DO ARQUIVO EXCEL ---
RULES_FILE_PATH = 'regras_categorizacao.xlsx'
loaded_rules = load_rules_from_excel(RULES_FILE_PATH)

# --- Inicialização do Estado da Sessão ---
if 'df_fatura' not in st.session_state: st.session_state.df_fatura = None
if 'df_for_plot' not in st.session_state: st.session_state.df_for_plot = pd.DataFrame()
if 'categorias_mapeadas' not in st.session_state: st.session_state.categorias_mapeadas = {}
if 'uploaded_file_name' not in st.session_state: st.session_state.uploaded_file_name = None
if 'show_charts' not in st.session_state: st.session_state.show_charts = False
if 'selected_cat_nv1' not in st.session_state: st.session_state.selected_cat_nv1 = []
if 'selected_cat_nv2' not in st.session_state: st.session_state.selected_cat_nv2 = []


# --- Interface Streamlit ---
st.title("📊 Análise de Fatura - Categorias Nível 1 e 2")

# --- Sidebar ---
with st.sidebar:
    # (Conteúdo da Sidebar mantido como antes)
    st.header("Controles"); uploaded_file = st.file_uploader("1. Carregue seu arquivo Excel:", type=["xls", "xlsx"]); default_closing_day = 20; closing_day = st.number_input("2. Dia de fechamento:", min_value=1, max_value=31, value=default_closing_day, step=1)
    categorias_nv1_arquivo = sorted(list(set(rule['Nivel1'] for rule in loaded_rules.values() if rule.get('Nivel1')))); categorias_nv2_arquivo = sorted(list(set(rule['Nivel2'] for rule in loaded_rules.values() if rule.get('Nivel2'))))
    lista_categorias_base_nv1 = ['Não categorizado', 'Alimentação', 'Transporte', 'Moradia', 'Lazer', 'Assinaturas', 'Compras Online', 'Vestuário/Compras', 'Saúde', 'Educação', 'Mercado', 'Pet', 'Serviços', 'Viagem', 'Presentes', 'Parcelamento', 'Outros']; lista_categorias_base_nv2 = ['Geral', 'Não Aplicável', 'Compra Parcelada']
    lista_categorias_final_nv1 = sorted(list(set(lista_categorias_base_nv1 + categorias_nv1_arquivo))); lista_categorias_final_nv2 = sorted(list(set(lista_categorias_base_nv2 + [cat for cat in categorias_nv2_arquivo if cat is not None])))
    st.divider(); nivel_grafico = st.radio("Nível Categoria Gráficos:", ('Nível 1 (Geral)', 'Nível 2 (Detalhada)'), key='nivel_grafico_radio'); coluna_grafico = 'Categoria Nível 1' if nivel_grafico == 'Nível 1 (Geral)' else 'Categoria Nível 2'

# --- Processamento e Exibição Principal ---
if uploaded_file is not None:
    # (Lógica de carregamento como antes)
    if st.session_state.uploaded_file_name != uploaded_file.name:
        st.info(f"Carregando: {uploaded_file.name}"); st.session_state.df_fatura = None; st.session_state.categorias_mapeadas = {}; st.session_state.uploaded_file_name = uploaded_file.name; st.session_state.show_charts = False; st.session_state.df_for_plot = pd.DataFrame(); st.session_state.selected_cat_nv1 = []; st.session_state.selected_cat_nv2 = []
    if st.session_state.df_fatura is None:
         df_loaded = load_data(uploaded_file)
         if df_loaded is not None:
             df_temp = df_loaded.copy(); df_temp['Descricao'] = df_temp['Descricao'].astype(str)
             for index, row in df_temp.iterrows():
                 manual_map = st.session_state.categorias_mapeadas.get(row['Descricao']);
                 if manual_map: df_temp.loc[index, 'Categoria Nível 1'] = manual_map.get('Nivel1', 'Não categorizado'); df_temp.loc[index, 'Categoria Nível 2'] = manual_map.get('Nivel2')
                 else: sug_cat1, sug_cat2 = suggest_categories_v2(row['Descricao'], loaded_rules); df_temp.loc[index, 'Categoria Nível 1'] = sug_cat1; df_temp.loc[index, 'Categoria Nível 2'] = sug_cat2
             st.session_state.df_fatura = df_temp; st.session_state.df_for_plot = df_temp.copy(); st.session_state.show_charts = True; st.session_state.selected_cat_nv1 = []; st.session_state.selected_cat_nv2 = []; st.rerun()

    if st.session_state.df_fatura is not None:
        df = st.session_state.df_fatura
        if df.empty: st.warning("DataFrame vazio.")
        else:
            # Indicadores Chave
            st.subheader("Resumo"); total_fatura = pd.to_numeric(df['Valor'], errors='coerce').fillna(0).sum(); dias_restantes = calculate_days_remaining(closing_day); col1, col2 = st.columns(2);
            with col1: st.metric(label="💰 Total", value=f"R$ {total_fatura:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            with col2: st.metric(label="⏳ Fechamento", value=f"{dias_restantes} dias" if isinstance(dias_restantes, int) else dias_restantes)
            # Tabela Editável
            st.subheader("Lançamentos e Categorização (Nível 1 / Nível 2)"); st.markdown("Edite as categorias. Use 'Atualizar Gráficos' para refletir.")
            column_config_v2 = {"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", width="small"),"Descricao": st.column_config.TextColumn("Descrição", width="medium"),"Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", width="small"),"Categoria Nível 1": st.column_config.SelectboxColumn("Cat. Nível 1", options=lista_categorias_final_nv1, required=True, width="medium"),"Categoria Nível 2": st.column_config.SelectboxColumn("Cat. Nível 2", options=[None] + lista_categorias_final_nv2, required=False, width="medium"),"MesAno": None }
            try: df_editor = df.copy(); df_editor['Data'] = pd.to_datetime(df_editor['Data'], errors='coerce'); df_editor['Valor'] = pd.to_numeric(df_editor['Valor'], errors='coerce'); df_editor['Descricao'] = df_editor['Descricao'].astype(str); df_editor['Categoria Nível 1'] = df_editor['Categoria Nível 1'].astype(str); df_editor['Categoria Nível 2'] = df_editor['Categoria Nível 2'].fillna("").astype(str)
            except Exception as e: st.warning(f"Erro prep editor: {e}"); df_editor = df.copy()
            df_editor['Data'] = df_editor['Data'].replace({pd.NaT: None})
            edited_df = st.data_editor(df_editor, column_config=column_config_v2, use_container_width=True, hide_index=True, num_rows="fixed", key="data_editor_v2_" + uploaded_file.name)
            # Atualização Estado
            if not edited_df.equals(df_editor):
                 edited_df['Categoria Nível 2'] = edited_df['Categoria Nível 2'].replace({"": None}); edited_df['Data'] = pd.to_datetime(edited_df['Data'], errors='coerce'); st.session_state.df_fatura = edited_df
                 for index, row in edited_df.iterrows(): st.session_state.categorias_mapeadas[str(row['Descricao'])] = {'Nivel1': row['Categoria Nível 1'], 'Nivel2': row['Categoria Nível 2']}
                 st.info("Categorias editadas. Clique em 'Atualizar Gráficos'.")
            st.divider()
            # Filtros e Botão
            col_filter1, col_filter2, col_button = st.columns([2, 2, 1])
            with col_filter1: options_nv1 = sorted(st.session_state.df_fatura['Categoria Nível 1'].unique()); selected_nv1 = st.multiselect("Filtrar Nível 1:", options=options_nv1, default=st.session_state.selected_cat_nv1, key='multi_cat_nv1'); st.session_state.selected_cat_nv1 = selected_nv1
            with col_filter2: options_nv2 = sorted([cat for cat in st.session_state.df_fatura['Categoria Nível 2'].unique() if pd.notna(cat)]); selected_nv2 = st.multiselect("Filtrar Nível 2:", options=options_nv2, default=st.session_state.selected_cat_nv2, key='multi_cat_nv2'); st.session_state.selected_cat_nv2 = selected_nv2
            with col_button: st.write(""); st.write(""); update_button_pressed = st.button("🔄 Atualizar Gráficos", key='update_charts_button')
            if update_button_pressed: st.session_state.df_for_plot = st.session_state.df_fatura.copy(); st.session_state.show_charts = True

            # --- Visualizações Gráficas ---
            if st.session_state.show_charts and not st.session_state.df_for_plot.empty:
                st.subheader(f"Visualizações por {nivel_grafico}")
                df_plot_filtered = st.session_state.df_for_plot.copy()
                if selected_nv1: df_plot_filtered = df_plot_filtered[df_plot_filtered['Categoria Nível 1'].isin(selected_nv1)]
                if selected_nv2: df_plot_filtered['Categoria Nível 2'] = df_plot_filtered['Categoria Nível 2'].fillna('N/A_temp'); df_plot_filtered = df_plot_filtered[df_plot_filtered['Categoria Nível 2'].isin(selected_nv2)]; df_plot_filtered['Categoria Nível 2'] = df_plot_filtered['Categoria Nível 2'].replace({'N/A_temp': None})
                df_plot_filtered['Valor'] = pd.to_numeric(df_plot_filtered['Valor'], errors='coerce'); df_plot_filtered = df_plot_filtered.dropna(subset=['Valor', coluna_grafico]); df_plot_filtered = df_plot_filtered[df_plot_filtered[coluna_grafico] != 'Não categorizado'];
                if coluna_grafico == 'Categoria Nível 2': df_plot_filtered[coluna_grafico] = df_plot_filtered[coluna_grafico].fillna('N/A ou Geral')

                if not df_plot_filtered.empty:
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.markdown(f"##### Distribuição ({nivel_grafico})"); fig_pie = px.pie(df_plot_filtered, names=coluna_grafico, values='Valor', title=f"Gastos (%)", hole=0.3); fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05 if i < 3 else 0 for i in range(len(df_plot_filtered[coluna_grafico].unique()))], sort=False); fig_pie.update_layout(showlegend=False, title_x=0.5, margin=dict(t=50, b=0, l=0, r=0)); st.plotly_chart(fig_pie, use_container_width=True)
                    with col_g2:
                        st.markdown(f"##### Total Gasto ({nivel_grafico})"); gastos_agrupados = df_plot_filtered.groupby(coluna_grafico)['Valor'].sum().reset_index().sort_values(by='Valor', ascending=False); fig_bar = px.bar(gastos_agrupados, x=coluna_grafico, y='Valor', title=f"Total (R$)", labels={'Valor': 'Total (R$)', coluna_grafico: nivel_grafico}, text_auto='.2f', color=coluna_grafico, color_discrete_sequence=px.colors.qualitative.Pastel); fig_bar.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Total (R$)"); st.plotly_chart(fig_bar, use_container_width=True)

                    # --- Gráfico de Evolução AJUSTADO (Linha/Barra Invertido) ---
                    st.markdown("---"); st.markdown("##### Evolução Diária e Acumulada")
                    df_plot_filtered['Data'] = pd.to_datetime(df_plot_filtered['Data'], errors='coerce')
                    df_plot_line_base = df_plot_filtered.dropna(subset=['Data']).sort_values(by='Data')

                    col_date1, col_date2, col_limit = st.columns([1, 1, 1])
                    with col_date1: default_start_date = df_plot_line_base['Data'].min().date() if not df_plot_line_base.empty else date.today() - timedelta(days=30); start_date = st.date_input("Data Início:", value=default_start_date, key='start_date_evol_flex') # Sem min/max
                    with col_date2: default_end_date = df_plot_line_base['Data'].max().date() if not df_plot_line_base.empty else date.today(); end_date = st.date_input("Data Fim:", value=default_end_date, key='end_date_evol_flex') # Sem min/max
                    with col_limit: gasto_limite = st.number_input("Limite Saldo Acumulado (R$):", min_value=0.0, value=0.0, step=100.0, format="%.2f", help="Valor > 0 plota linha limite.")

                    if start_date and end_date and start_date <= end_date:
                         start_dt = pd.to_datetime(start_date); end_dt = pd.to_datetime(end_date); df_plot_line = df_plot_line_base[(df_plot_line_base['Data'] >= start_dt) & (df_plot_line_base['Data'] <= end_dt)]
                    else: st.warning("Período inválido."); df_plot_line = pd.DataFrame()

                    if not df_plot_line.empty:
                        gastos_por_dia = df_plot_line.groupby(df_plot_line['Data'].dt.date)['Valor'].sum().reset_index(); gastos_por_dia['Data'] = pd.to_datetime(gastos_por_dia['Data']); gastos_por_dia = gastos_por_dia.sort_values(by='Data'); gastos_por_dia['Saldo Acumulado'] = gastos_por_dia['Valor'].cumsum()

                        fig_evol = make_subplots(specs=[[{"secondary_y": True}]])

                        # --- INVERSÃO AQUI ---
                        # Adiciona LINHA para gasto diário (Eixo Y Primário)
                        fig_evol.add_trace(
                            go.Scatter(x=gastos_por_dia['Data'], y=gastos_por_dia['Valor'], name="Gasto Diário", mode='lines+markers', line=dict(color='royalblue', width=2)),
                            secondary_y=False,
                        )
                        # Adiciona BARRAS para saldo acumulado (Eixo Y Secundário)
                        fig_evol.add_trace(
                            go.Bar(x=gastos_por_dia['Data'], y=gastos_por_dia['Saldo Acumulado'], name="Saldo Acumulado", marker_color='lightsalmon', opacity=0.7),
                            secondary_y=True,
                        )
                        # --- FIM DA INVERSÃO ---

                        if gasto_limite > 0 and not gastos_por_dia.empty:
                            fig_evol.add_shape(type="line", x0=gastos_por_dia['Data'].min(), y0=gasto_limite, x1=gastos_por_dia['Data'].max(), y1=gasto_limite, line=dict(color="Red", width=2, dash="dash"), xref='x', yref='y2')
                            fig_evol.add_annotation(x=gastos_por_dia['Data'].max(), y=gasto_limite, yref='y2', text=f"Limite R$ {gasto_limite:.2f}", showarrow=False, yshift=10, xanchor="right", font=dict(color="red", size=10))

                        fig_evol.update_layout(title_text="Gastos Diários e Saldo Acumulado", xaxis_title="Data", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        # Ajusta cores dos eixos para corresponder aos novos traços (opcional)
                        fig_evol.update_yaxes(title_text="Gasto Diário (R$)", secondary_y=False, title_font_color='royalblue', tickfont_color='royalblue')
                        fig_evol.update_yaxes(title_text="Saldo Acumulado (R$)", secondary_y=True, title_font_color='lightsalmon', tickfont_color='lightsalmon')

                        st.plotly_chart(fig_evol, use_container_width=True)
                    else: st.warning("Não há dados para o período selecionado.")
                else: st.info(f"Aplique filtros ou categorize lançamentos com '{nivel_grafico}' válidos.")
            else: st.info("Clique em 'Atualizar Gráficos' para exibir.")
            # Outras Análises
            st.subheader("Outras Análises"); st.markdown("**Maiores Despesas (Top 5)**"); edited_df['Valor'] = pd.to_numeric(edited_df['Valor'], errors='coerce'); maiores_despesas = edited_df.dropna(subset=['Valor']).nlargest(5, 'Valor');
            st.dataframe(maiores_despesas[['Data', 'Descricao', 'Valor', 'Categoria Nível 1', 'Categoria Nível 2']], column_config={"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "Descricao": st.column_config.TextColumn("Descrição"), "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"), "Categoria Nível 1": st.column_config.TextColumn("Cat. Nv1"), "Categoria Nível 2": st.column_config.TextColumn("Cat. Nv2"),}, use_container_width=True, hide_index=True)
    elif uploaded_file is not None and st.session_state.df_fatura is None: st.warning("Não foi possível processar o arquivo.")
else: st.info("⬅️ Carregue um arquivo Excel na barra lateral.")
# --- Rodapé ---
st.markdown("---"); st.caption(f"Análise de Fatura | v2.3 (Evolução Invertida) | {datetime.now().year}")