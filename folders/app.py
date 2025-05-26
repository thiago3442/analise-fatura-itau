# -*- coding: utf-8 -*- # Define encoding
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import numpy as np
import re
import io
import os
from .utils import limpar_valor

# --- Configuração da Página Streamlit ---
st.set_page_config(page_title="Análise de Fatura Itaú", page_icon="📊", layout="wide")

# --- Funções Auxiliares ---
@st.cache_data
def load_rules_from_excel(file_path='regras_categorizacao.xlsx'):
    """Loads categorization rules from an Excel file."""
    # Adjust path if rules file is not in the same directory as app.py
    # Assuming regras_categorizacao.xlsx is in the ANALISE-FATURA-ITAU directory
    base_dir = os.path.dirname(__file__) # Directory of the current script (app.py)
    rules_full_path = os.path.join(base_dir, '..', file_path) # Go up one dir to ANALISE-FATURA-ITAU

    if not os.path.exists(rules_full_path):
        st.warning(f"Arquivo de regras '{file_path}' não encontrado em '{rules_full_path}'. Usando categorização básica.");
        return {}
    try:
        # Use appropriate engine based on file extension
        engine = 'openpyxl' if rules_full_path.endswith('.xlsx') else 'xlrd'
        df_rules = pd.read_excel(rules_full_path, engine=engine)

        # Identify potential column names - keeping flexibility but prioritizing the requested names
        possible_keyword_cols = ['lançamento', 'Lançamento', 'Descrição', 'Descricao', 'Estabelecimento', 'PalavraChave', 'Keyword', 'Chave']
        possible_cat1_cols = ['CategoriaNivel1', 'CategoriaGeral', 'CatNivel1', 'Cat1']
        possible_cat2_cols = ['CategoriaNivel2', 'CategoriaDetalhada', 'CatNivel2', 'Cat2']

        col_keyword, col_cat1, col_cat2 = None, None, None

        # Find the actual column names in the DataFrame (case-insensitive search)
        df_rules_cols_lower = {col.lower(): col for col in df_rules.columns}

        for col in possible_keyword_cols:
            if col.lower() in df_rules_cols_lower:
                col_keyword = df_rules_cols_lower[col.lower()]
                break
        for col in possible_cat1_cols:
            if col.lower() in df_rules_cols_lower:
                col_cat1 = df_rules_cols_lower[col.lower()]
                break
        for col in possible_cat2_cols:
            if col.lower() in df_rules_cols_lower:
                col_cat2 = df_rules_cols_lower[col.lower()]
                break

        # Check if essential columns were found
        if col_keyword is None or col_cat1 is None or col_cat2 is None:
            st.error(f"O arquivo de regras '{file_path}' deve conter colunas para Palavra-Chave, Categoria Nível 1 e Categoria Nível 2. Verifique se alguma das seguintes colunas existe: Palavra-Chave: {', '.join(possible_keyword_cols)}. Categoria Nível 1: {', '.join(possible_cat1_cols)}. Categoria Nível 2: {', '.join(possible_cat2_cols)}.")
            return {}

        # Select and clean relevant columns
        df_rules = df_rules[[col_keyword, col_cat1, col_cat2]].copy()
        df_rules[col_keyword] = df_rules[col_keyword].astype(str).str.lower().str.strip()
        df_rules[col_cat1] = df_rules[col_cat1].astype(str).str.strip()
        df_rules[col_cat2] = df_rules[col_cat2].fillna('N/A').astype(str).str.strip()

        # Replace empty strings with None for consistent handling
        df_rules.replace({'N/A': None, '': None}, inplace=True)

        # Filter out rows with empty keywords
        df_rules = df_rules[df_rules[col_keyword].str.strip() != '']

        # Sort by keyword length descending for better matching (longer keywords first)
        df_rules['keyword_len'] = df_rules[col_keyword].str.len()
        df_rules = df_rules.sort_values(by='keyword_len', ascending=False)

        # Convert rules DataFrame to a dictionary for faster lookup
        rules_dict = {}
        for _, row in df_rules.iterrows():
            rules_dict[row[col_keyword]] = {'Nivel1': row[col_cat1], 'Nivel2': row[col_cat2]}

        return rules_dict
    except FileNotFoundError:
         st.warning(f"Arquivo de regras '{file_path}' não encontrado. Usando categorização básica.");
         return {}
    except Exception as e:
        st.error(f"Erro ao ler arquivo de regras '{file_path}': {e}");
        return {}

def suggest_categories_v2(description, rules_dict):
    """Suggests categories based on description and rules."""
    cat_nivel1 = 'Não categorizado'
    cat_nivel2 = None # Use None for no specific Nivel 2

    if not isinstance(description, str):
        return cat_nivel1, cat_nivel2

    description_lower = description.lower()

    # --- Modified Parcelamento Logic ---
    # Check for parcelamento (installment) pattern first
    parcelamento_match = re.search(r'\b(\d{1,2}/\d{1,2})\b', description)
    if parcelamento_match:
        # Only set Nivel 1 to 'Parcelamento' based on regex
        cat_nivel1 = 'Parcelamento'
        # Do NOT set cat_nivel2 here based on regex.
        # The Nivel 2 for Parcelamento will come from the rules_dict if a matching rule exists.

    # Apply rules if available
    if rules_dict:
        for keyword, categories in rules_dict.items():
            keyword_found = False
            # Use regex for whole word match if possible, fallback to substring
            try:
                if re.search(r'\b' + re.escape(keyword) + r'\b', description_lower):
                    keyword_found = True
            except re.error:
                 # Fallback to simple substring check if regex fails (e.g., complex characters in keyword)
                 if keyword in description_lower:
                     keyword_found = True

            # If regex didn't find it, try simple substring check as a fallback
            if not keyword_found and keyword in description_lower:
                 keyword_found = True

            if keyword_found:
                cat_nivel1_regra = categories.get('Nivel1', 'Não categorizado')
                cat_nivel2_regra = categories.get('Nivel2')

                # Apply rule categories
                cat_nivel1 = cat_nivel1_regra # Rule can override Parcelamento Nivel 1 if needed

                # Apply Nivel 2 rule if it exists.
                # This will set Nivel 2 for Parcelamento if a rule matches, or for other categories.
                if cat_nivel2_regra is not None:
                     cat_nivel2 = cat_nivel2_regra

                # If a rule matched, we can break the loop (assuming rules are sorted by specificity/length)
                break

    # Default Nivel 2 if Nivel 1 is set but Nivel 2 is still None and not 'Não categorizado' or 'Parcelamento'
    # This now applies if no rule set Nivel 2, including for 'Parcelamento' if no specific rule exists.
    if cat_nivel2 is None and cat_nivel1 != 'Não categorizado':
        cat_nivel2 = 'Geral' # Or a suitable default like 'Outros'

    return cat_nivel1, cat_nivel2

# Modified load_data function to handle both Excel and CSV and exclude negative values
def load_data(uploaded_file):
    """Loads data from the uploaded Excel or CSV file with specific column names and excludes negative values."""
    if uploaded_file is not None:
        try:
            file_name = uploaded_file.name
            file_extension = os.path.splitext(file_name)[1].lower()

            if file_extension in ['.xls', '.xlsx']:
                engine = 'openpyxl' if file_extension == '.xlsx' else 'xlrd'
                df = pd.read_excel(uploaded_file, engine=engine, sheet_name=0)
            elif file_extension == '.csv':
                # Assuming comma separator, adjust if needed
                # Try different encodings and separators
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8', errors='replace')
                except Exception as e_utf8:
                    try:
                        # Reset file pointer for next read attempt
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file, encoding='ISO-8859-1', errors='replace')
                    except Exception as e_iso:
                         # Reset file pointer
                         uploaded_file.seek(0)
                         try:
                             df = pd.read_csv(uploaded_file, encoding='utf-8', errors='replace', sep=';')
                         except Exception as e_utf8_semicolon:
                             # Reset file pointer
                             uploaded_file.seek(0)
                             try:
                                 df = pd.read_csv(uploaded_file, encoding='ISO-8859-1', errors='replace', sep=';')
                             except Exception as e_iso_semicolon:
                                 st.error(f"Não foi possível ler o arquivo CSV. Tente salvar como UTF-8 com separador ','. Erros: UTF-8({e_utf8}), ISO({e_iso}), UTF-8(semicolon)({e_utf8_semicolon}), ISO(semicolon)({e_iso_semicolon})")
                                 return None


                # Handle potential issues with CSV headers/footers by checking for expected columns
                # This is a basic check; more robust parsing might be needed for complex files
                if df.empty or len(df.columns) < 3:
                     st.error("Não foi possível ler o arquivo CSV. Verifique o formato, codificação e separador.")
                     return None

            else:
                st.error("Formato de arquivo não suportado. Carregue um arquivo .xls, .xlsx ou .csv.")
                return None

            # Expected columns (case-insensitive matching)
            colunas_necessarias = {'data': 'Data', 'lançamento': 'Descricao', 'valor': 'Valor'}
            colunas_encontradas = {}
            colunas_faltando = []

            # Find the actual column names in the DataFrame (case-insensitive search)
            df_cols_lower = {col.lower(): col for col in df.columns}

            for col_padrao, col_final in colunas_necessarias.items():
                if col_padrao in df_cols_lower:
                    colunas_encontradas[df_cols_lower[col_padrao]] = col_final
                else:
                    colunas_faltando.append(col_padrao)

            # Check if all necessary columns were found
            if colunas_faltando:
                st.error(f"Colunas essenciais não encontradas no arquivo: {', '.join(colunas_faltando)}. Certifique-se de que o arquivo contenha as colunas 'data', 'lançamento' e 'valor'.")
                return None

            # Rename columns to standard names
            df = df.rename(columns=colunas_encontradas)

            # Select only the final required columns
            df = df[list(colunas_necessarias.values())]

            # Process 'Data' column
            if 'Data' in df.columns:
                try:
                    # Attempt to convert to datetime, handling potential errors
                    df['Data_Limpada'] = df['Data'].astype(str).str.strip()
                    # Try multiple date formats
                    date_formats = ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y'] # Added %d-%m-%Y
                    for fmt in date_formats:
                         df['Data_Convertida'] = pd.to_datetime(df['Data_Limpada'], format=fmt, errors='coerce')
                         if not df['Data_Convertida'].isnull().all():
                             break # Stop if at least some dates are converted

                    # Check if conversion failed for all rows
                    nan_count = df['Data_Convertida'].isnull().sum()
                    if nan_count == len(df) and len(df) > 0: # Check if ALL rows failed
                        # Corrected the unterminated string literal here
                        st.error("Falha ao converter TODAS as datas. Verifique se a coluna 'data' está em um formato reconhecido (ex: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY).")

                        return None

                    df['Data'] = df['Data_Convertida']
                    df.drop(columns=['Data_Limpada', 'Data_Convertida'], inplace=True, errors='ignore')

                except Exception as e:
                    st.error(f"Erro CRÍTICO durante a conversão da coluna 'data': {e}. Verifique o formato.");
                    return None
            else:
                 st.error("Coluna 'Data' não encontrada após renomear. Verifique se a coluna 'data' existe no arquivo.")
                 return None


            # Process 'Valor' column
            df['Valor'] = df['Valor'].apply(limpar_valor)

            # --- Exclude rows with negative 'Valor' ---
            df = df[df['Valor'] >= 0].copy() # Keep only non-negative values

            # Process 'Descricao' column
            df['Descricao'] = df['Descricao'].astype(str)

            # Filter out rows with empty or NaN descriptions (after excluding negative values)
            df = df[df['Descricao'].str.strip() != ''][df['Descricao'].str.lower() != 'nan']

            # Initialize category columns
            df['Categoria Nível 1'] = 'Não categorizado'
            df['Categoria Nível 2'] = None

            # Add 'MesAno' column
            if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']) and not df['Data'].isnull().all():
                df['MesAno'] = df['Data'].dt.to_period('M').astype(str)
            else:
                df['MesAno'] = 'N/A'

            # Sort by date if data is valid
            if 'Data' in df.columns and pd.api.types.is_datetime64_any_dtype(df['Data']) and not df['Data'].isnull().all():
                 return df.sort_values(by='Data').reset_index(drop=True)
            else:
                 return df.reset_index(drop=True) # Return without sorting if data is invalid


        except FileNotFoundError:
            st.error("Arquivo não encontrado.")
            return None
        except Exception as e:
            st.error(f"Erro no processamento do arquivo: {e}");
            return None
    return None


# Removed calculate_days_remaining function

# --- CARREGA AS REGRAS DO ARQUIVO EXCEL ---
RULES_FILE_PATH = 'regras_categorizacao.xlsx'
loaded_rules = load_rules_from_excel(RULES_FILE_PATH)

# --- Inicialização do Estado da Sessão ---
if 'df_fatura' not in st.session_state:
    st.session_state.df_fatura = None
if 'df_for_plot' not in st.session_state:
    st.session_state.df_for_plot = pd.DataFrame()
if 'categorias_mapeadas' not in st.session_state:
    st.session_state.categorias_mapeadas = {}
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None
if 'show_charts' not in st.session_state:
    st.session_state.show_charts = False
if 'selected_cat_nv1' not in st.session_state:
    st.session_state.selected_cat_nv1 = []
if 'selected_cat_nv2' not in st.session_state:
    st.session_state.selected_cat_nv2 = []


# --- Interface Streamlit ---
st.title("📊 Análise de Fatura - Visão Geral") # Changed title for the main page

# --- Sidebar ---
with st.sidebar:
    st.header("Controles")

    # --- Navigation ---
    # Corrected page link for the main page to be relative to the 'folders' directory
    st.page_link("app.py", label="Visão Geral", icon="📊")
    st.page_link("pages/parcelamentos_analysis.py", label="Análise de Parcelamentos", icon="💳")
    st.divider()

    # Updated file uploader to accept csv
    uploaded_file = st.file_uploader("1. Carregue seu arquivo Excel ou CSV (colunas: data, lançamento, valor):", type=["xls", "xlsx", "csv"])
    # Removed closing day input

    # Get categories from loaded rules and base lists
    categorias_nv1_arquivo = sorted(list(set(rule['Nivel1'] for rule in loaded_rules.values() if rule.get('Nivel1'))))
    categorias_nv2_arquivo = sorted(list(set(rule['Nivel2'] for rule in loaded_rules.values() if rule.get('Nivel2'))))

    lista_categorias_base_nv1 = ['Não categorizado', 'Alimentação', 'Transporte', 'Moradia', 'Lazer', 'Assinaturas', 'Compras Online', 'Vestuário/Compras', 'Saúde', 'Educação', 'Mercado', 'Pet', 'Serviços', 'Viagem', 'Presentes', 'Parcelamento', 'Outros']
    lista_categorias_base_nv2 = ['Geral', 'Não Aplicável', 'Compra Parcelada']

    lista_categorias_final_nv1 = sorted(list(set(lista_categorias_base_nv1 + categorias_nv1_arquivo)))
    # Ensure None is included in Nivel 2 options for the selectbox
    lista_categorias_final_nv2 = sorted(list(set(lista_categorias_base_nv2 + [cat for cat in categorias_nv2_arquivo if cat is not None])))

    st.divider()
    nivel_grafico = st.radio("Nível Categoria Gráficos:", ('Nível 1 (Geral)', 'Nível 2 (Detalhada)'), key='nivel_grafico_radio')


# --- File Upload Processing ---
if uploaded_file is not None:
    # Check if a new file has been uploaded
    if st.session_state.uploaded_file_name != uploaded_file.name:
        st.info(f"Carregando: {uploaded_file.name}")
        # Reset session state when a new file is uploaded
        st.session_state.df_fatura = None
        st.session_state.categorias_mapeadas = {} # Clear previous mappings
        st.session_state.uploaded_file_name = uploaded_file.name
        st.session_state.show_charts = False # Hide charts until updated
        st.session_state.df_for_plot = pd.DataFrame() # Clear plot data
        st.session_state.selected_cat_nv1 = [] # Reset filters
        st.session_state.selected_cat_nv2 = [] # Reset filters
        # st.rerun() # Rerun to clear the state and show loading message

    # Load and process the data if it's not already in session state
    if st.session_state.df_fatura is None:
        df_loaded = load_data(uploaded_file)

        if df_loaded is not None:
            # Apply initial categorization based on rules
            df_temp = df_loaded.copy()
            df_temp['Descricao'] = df_temp['Descricao'].astype(str) # Ensure description is string

            for index, row in df_temp.iterrows():
                 # Apply rules first
                 sug_cat1, sug_cat2 = suggest_categories_v2(row['Descricao'], loaded_rules)
                 df_temp.loc[index, 'Categoria Nível 1'] = sug_cat1
                 df_temp.loc[index, 'Categoria Nível 2'] = sug_cat2

                 # Check if there's a manual mapping for this description from a previous session
                 # This part might be tricky with file upload as mappings are tied to descriptions,
                 # but descriptions might repeat across files. For simplicity, we'll apply rules
                 # and then allow manual editing which updates mappings for the current dataset.
                 # If you need persistent mappings across different files, a more complex
                 # mapping management system would be needed.

            st.session_state.df_fatura = df_temp
            st.session_state.df_for_plot = df_temp.copy() # Initialize plot data
            st.session_state.show_charts = True # Show charts after initial load
            st.session_state.selected_cat_nv1 = [] # Reset filters
            st.session_state.selected_cat_nv2 = [] # Reset filters
            st.rerun() # Rerun to display the loaded data and charts

    # --- Display Processed Data and Allow Category Editing ---
    if st.session_state.df_fatura is not None and not st.session_state.df_fatura.empty:
        df = st.session_state.df_fatura.copy() # Use a copy to avoid modifying session state directly during editing

        # Indicadores Chave
        st.subheader("Resumo")
        # Calculate total (sum of all values, since negative values are excluded)
        total_valor = pd.to_numeric(df['Valor'], errors='coerce').fillna(0).sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="💰 Total", value=f"R$ {total_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        # Removed closing day metric
        with col2:
             st.write("") # Placeholder for alignment

        # Table to display processed data and allow category editing
        st.subheader("Lançamentos e Categorização (Nível 1 / Nível 2)")
        st.markdown("Revise as categorias sugeridas e edite se necessário. Use 'Atualizar Gráficos' para refletir as mudanças.")

        # Ensure categories lists for selectboxes are up-to-date based on current data and rules
        current_cats_nv1 = sorted(df['Categoria Nível 1'].unique().tolist())
        current_cats_nv2 = sorted([cat for cat in df['Categoria Nível 2'].unique().tolist() if pd.notna(cat)])

        # Combine with base and rule categories for the full list of options
        all_possible_cats_nv1 = sorted(list(set(lista_categorias_final_nv1 + current_cats_nv1)))
        all_possible_cats_nv2 = sorted(list(set(lista_categorias_final_nv2 + current_cats_nv2)))


        column_config_display = {
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", width="small"),
            "Descricao": st.column_config.TextColumn("Descrição", width="medium"),
            "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", width="small"),
            "Categoria Nível 1": st.column_config.SelectboxColumn(
                "Cat. Nível 1",
                options=all_possible_cats_nv1,
                required=True,
                width="medium"
            ),
            "Categoria Nível 2": st.column_config.SelectboxColumn(
                "Cat. Nível 2",
                options=[None] + all_possible_cats_nv2, # Include None as an option
                required=False,
                width="medium"
            ),
            "MesAno": None # Hide this internal column
        }

        # Prepare DataFrame for display editor
        df_display_editor = df.copy()
        # Ensure 'Data' is in a format compatible with st.data_editor DateColumn for display
        df_display_editor['Data'] = pd.to_datetime(df_display_editor['Data'], errors='coerce').dt.date # Convert to date objects
        # Convert None in Nivel 2 to empty string for the editor display
        df_display_editor['Categoria Nível 2'] = df_display_editor['Categoria Nível 2'].fillna("")

        edited_df_display = st.data_editor(
            df_display_editor,
            column_config=column_config_display,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed", # Use fixed rows as editing is for existing data
            key="data_editor_display_" + uploaded_file.name # Use file name in key to reset on new upload
        )

        # Check if the display editor was edited
        # Compare with the current state of df_fatura (after initial processing)
        # Need to prepare df_fatura for comparison (convert Data to date, fillna for Nivel 2)
        df_fatura_for_comparison = st.session_state.df_fatura.copy()
        df_fatura_for_comparison['Data'] = pd.to_datetime(df_fatura_for_comparison['Data'], errors='coerce').dt.date
        df_fatura_for_comparison['Categoria Nível 2'] = df_fatura_for_comparison['Categoria Nível 2'].fillna("")


        if not edited_df_display.equals(df_fatura_for_comparison):
            # Update session state df_fatura with edits from the display editor
            edited_df_display['Data'] = pd.to_datetime(edited_df_display['Data'], errors='coerce') # Convert back to datetime
            edited_df_display['Categoria Nível 2'] = edited_df_display['Categoria Nível 2'].replace({"": None}) # Convert empty back to None
            edited_df_display['Valor'] = pd.to_numeric(edited_df_display['Valor'], errors='coerce') # Ensure Valor is numeric

            # Re-add MesAno column as it might be lost in editing
            if 'Data' in edited_df_display.columns and pd.api.types.is_datetime64_any_dtype(edited_df_display['Data']) and not edited_df_display['Data'].isnull().all():
                 edited_df_display['MesAno'] = edited_df_display['Data'].dt.to_period('M').astype(str)
            else:
                 edited_df_display['MesAno'] = 'N/A'

            st.session_state.df_fatura = edited_df_display.sort_values(by='Data').reset_index(drop=True)

            # Update manual mappings based on edits (for the current file)
            st.session_state.categorias_mapeadas = {} # Clear existing mappings for this file
            for index, row in st.session_state.df_fatura.iterrows():
                 st.session_state.categorias_mapeadas[str(row['Descricao'])] = {'Nivel1': row['Categoria Nível 1'], 'Nivel2': row['Categoria Nível 2']}


            st.info("Categorias editadas. Clique em 'Atualizar Gráficos'.")
            # st.rerun() # Rerunning here might be too aggressive


        st.divider()

        # --- Filters and Update Button ---
        col_filter1, col_filter2, col_button = st.columns([2, 2, 1])
        with col_filter1:
            # Update filter options based on current data in df_fatura
            options_nv1 = sorted(st.session_state.df_fatura['Categoria Nível 1'].unique().tolist())
            selected_nv1 = st.multiselect("Filtrar Nível 1:", options=options_nv1, default=st.session_state.selected_cat_nv1, key='multi_cat_nv1')
            st.session_state.selected_cat_nv1 = selected_nv1 # Update state

        with col_filter2:
            # Update filter options based on current data in df_fatura
            options_nv2 = sorted([cat for cat in st.session_state.df_fatura['Categoria Nível 2'].unique().tolist() if pd.notna(cat)])
            selected_nv2 = st.multiselect("Filtrar Nível 2:", options=options_nv2, default=st.session_state.selected_cat_nv2, key='multi_cat_nv2')
            st.session_state.selected_cat_nv2 = selected_nv2 # Update state

        with col_button:
            st.write("") # Add some vertical space
            st.write("")
            update_button_pressed = st.button("🔄 Atualizar Gráficos", key='update_charts_button')

        # --- Visualizações Gráficas ---
        # Trigger chart update when button is pressed or if data is initially loaded/edited
        if st.session_state.show_charts and not st.session_state.df_for_plot.empty:

             df_plot_filtered = st.session_state.df_for_plot.copy()

             # Apply filters
             if selected_nv1:
                 df_plot_filtered = df_plot_filtered[df_plot_filtered['Categoria Nível 1'].isin(selected_nv1)]
             if selected_nv2:
                 # Filter for None in multiselect requires careful handling.
                 if selected_nv2:
                     # Check if None is explicitly selected in the multiselect
                     if None in selected_nv2:
                         # Filter for selected non-None values OR rows where Categoria Nível 2 is None
                         df_plot_filtered = df_plot_filtered[
                             (df_plot_filtered['Categoria Nível 2'].isin([cat for cat in selected_nv2 if cat is not None])) |
                             (df_plot_filtered['Categoria Nível 2'].isnull())
                         ]
                     else:
                         # Filter only for selected non-None values
                         df_plot_filtered = df_plot_filtered[df_plot_filtered['Categoria Nível 2'].isin(selected_nv2)]


             # Data cleaning for plotting
             df_plot_filtered['Valor'] = pd.to_numeric(df_plot_filtered['Valor'], errors='coerce')
             df_plot_filtered = df_plot_filtered.dropna(subset=['Valor']) # Keep rows with valid Valor
             # Exclude 'Não categorizado' from category plots unless explicitly included in filters (current logic excludes)
             # If you want to include 'Não categorizado' in plots, remove this line:
             df_plot_filtered_categorized = df_plot_filtered[df_plot_filtered['Categoria Nível 1'] != 'Não categorizado'].copy() # Use a copy

             # Determine the primary plotting column based on radio button
             coluna_grafico_primario = 'Categoria Nível 1' if nivel_grafico == 'Nível 1 (Geral)' else 'Categoria Nível 2'

             # Handle None values in the primary plotting column for Nivel 2 display
             if coluna_grafico_primario == 'Categoria Nível 2':
                 df_plot_filtered_categorized[coluna_grafico_primario] = df_plot_filtered_categorized[coluna_grafico_primario].fillna('N/A ou Geral') # Display label for None

             if not df_plot_filtered_categorized.empty:
                 st.subheader(f"Visualizações por {nivel_grafico}")
                 col_g1, col_g2 = st.columns(2)
                 with col_g1:
                     st.markdown(f"##### Distribuição por {nivel_grafico}")
                     # Pie chart uses all non-negative values after filtering
                     if not df_plot_filtered_categorized.empty:
                         fig_pie = px.pie(df_plot_filtered_categorized, names=coluna_grafico_primario, values='Valor', title=f"Distribuição por {nivel_grafico}", hole=0.3)
                         fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05 if i < 3 else 0 for i in range(len(df_plot_filtered_categorized[coluna_grafico_primario].unique()))], sort=False);
                         fig_pie.update_layout(showlegend=False, title_x=0.5, margin=dict(t=50, b=0, l=0, r=0));
                         st.plotly_chart(fig_pie, use_container_width=True)
                     else:
                         st.info(f"Não há dados para exibir na distribuição por {nivel_grafico} após os filtros.")


                 with col_g2:
                     st.markdown(f"##### Total por Categoria ({nivel_grafico})")
                     gastos_agrupados = df_plot_filtered_categorized.groupby(coluna_grafico_primario)['Valor'].sum().reset_index().sort_values(by='Valor', ascending=False);
                     if not gastos_agrupados.empty:
                         fig_bar = px.bar(gastos_agrupados, x=coluna_grafico_primario, y='Valor', title=f"Total (R$)", labels={'Valor': 'Total (R$)', coluna_grafico_primario: nivel_grafico}, text_auto='.2f', color=coluna_grafico_primario, color_discrete_sequence=px.colors.qualitative.Pastel);
                         fig_bar.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Total (R$)");
                         st.plotly_chart(fig_bar, use_container_width=True)
                     else:
                         st.info(f"Não há dados para exibir o total por categoria ({nivel_grafico}) após os filtros.")

                 # --- Nested Nivel 2 Charts when filtering by Nivel 1 ---
                 if nivel_grafico == 'Nível 1 (Geral)' and selected_nv1:
                     st.markdown("---")
                     st.subheader("Visualização Detalhada por Nível 2 (dentro dos filtros de Nível 1)")

                     # Filter data for nested charts - only include rows within selected Nivel 1 categories
                     df_nested_plot = df_plot_filtered[df_plot_filtered['Categoria Nível 1'].isin(selected_nv1)].copy()
                     df_nested_plot = df_nested_plot.dropna(subset=['Categoria Nível 2', 'Valor']) # Drop rows without Nivel 2 or Valor
                     df_nested_plot = df_nested_plot[df_nested_plot['Categoria Nível 2'].str.strip() != ''] # Exclude empty Nivel 2 strings

                     if not df_nested_plot.empty:
                         # Group by Nivel 1 and Nivel 2 to get data for nested charts
                         nested_grouped = df_nested_plot.groupby(['Categoria Nível 1', 'Categoria Nível 2'])['Valor'].sum().reset_index()

                         # Iterate through each selected Nivel 1 category to create nested charts
                         for nivel1_cat in selected_nv1:
                             nested_data_for_cat = nested_grouped[nested_grouped['Categoria Nível 1'] == nivel1_cat].copy()

                             if not nested_data_for_cat.empty:
                                 st.markdown(f"##### Detalhes por Nível 2 para: {nivel1_cat}")
                                 col_nested_g1, col_nested_g2 = st.columns(2)

                                 with col_nested_g1:
                                     st.markdown(f"###### Distribuição Nível 2 em {nivel1_cat}")
                                     fig_nested_pie = px.pie(nested_data_for_cat, names='Categoria Nível 2', values='Valor', title=f"Distribuição Nível 2 (%)", hole=0.3)
                                     fig_nested_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05 if i < 3 else 0 for i in range(len(nested_data_for_cat['Categoria Nível 2'].unique()))], sort=False);
                                     fig_nested_pie.update_layout(showlegend=False, title_x=0.5, margin=dict(t=50, b=0, l=0, r=0));
                                     st.plotly_chart(fig_nested_pie, use_container_width=True)

                                 with col_nested_g2:
                                     st.markdown(f"###### Total Nível 2 em {nivel1_cat}")
                                     fig_nested_bar = px.bar(nested_data_for_cat.sort_values(by='Valor', ascending=False), x='Categoria Nível 2', y='Valor', title=f"Total Nível 2 (R$)", labels={'Valor': 'Total (R$)', 'Categoria Nível 2': 'Nível 2'}, text_auto='.2f', color='Categoria Nível 2', color_discrete_sequence=px.colors.qualitative.Pastel);
                                     fig_nested_bar.update_layout(xaxis_tickangle=-45, title_x=0.5, yaxis_title="Total (R$)");
                                     st.plotly_chart(fig_nested_bar, use_container_width=True)
                             else:
                                 st.info(f"Não há dados de Nível 2 categorizados para '{nivel1_cat}' após os filtros.")
                     else:
                         st.info("Não há dados de Nível 2 categorizados para os filtros de Nível 1 selecionados.")


                 # --- Gráfico de Evolução AJUSTADO (Linha/Barra Invertido) ---
                 st.markdown("---")
                 st.markdown("##### Evolução Diária e Acumulada")

                 # Ensure 'Data' is datetime for plotting evolution
                 df_plot_filtered['Data'] = pd.to_datetime(df_plot_filtered['Data'], errors='coerce')
                 df_plot_line_base = df_plot_filtered.dropna(subset=['Data']).sort_values(by='Data')

                 col_date1, col_date2, col_limit = st.columns([1, 1, 1])
                 with col_date1:
                     # Set default start date to the minimum date in the filtered data or 30 days ago
                     default_start_date = df_plot_line_base['Data'].min().date() if not df_plot_line_base.empty else date.today() - timedelta(days=30)
                     start_date = st.date_input("Data Início:", value=default_start_date, key='start_date_evol_flex') # No min/max to allow flexible input
                 with col_date2:
                     # Set default end date to the maximum date in the filtered data or today
                     default_end_date = df_plot_line_base['Data'].max().date() if not df_plot_line_base.empty else date.today()
                     end_date = st.date_input("Data Fim:", value=default_end_date, key='end_date_evol_flex') # No min/max to allow flexible input
                 with col_limit:
                     gasto_limite = st.number_input("Limite Saldo Acumulado (R$):", min_value=0.0, value=0.0, step=100.0, format="%.2f", help="Valor > 0 plota linha limite.")

                 # Filter data based on selected date range
                 if start_date and end_date and start_date <= end_date:
                     start_dt = pd.to_datetime(start_date)
                     end_dt = pd.to_datetime(end_date)
                     df_plot_line = df_plot_line_base[(df_plot_line_base['Data'] >= start_dt) & (df_plot_line_base['Data'] <= end_dt)].copy() # Use .copy() to avoid SettingWithCopyWarning
                 else:
                     st.warning("Período de data inválido selecionado.")
                     df_plot_line = pd.DataFrame() # Empty DataFrame if date range is invalid

                 # The evolution chart now uses all non-negative values
                 if not df_plot_line.empty:
                     # Group by date and calculate daily total and cumulative sum
                     gastos_por_dia = df_plot_line.groupby(df_plot_line['Data'].dt.date)['Valor'].sum().reset_index()
                     gastos_por_dia['Data'] = pd.to_datetime(gastos_por_dia['Data']) # Convert date objects back to datetime for plotting
                     gastos_por_dia = gastos_por_dia.sort_values(by='Data')
                     # Cumulative sum of all non-negative values
                     gastos_por_dia['Saldo Acumulado'] = gastos_por_dia['Valor'].cumsum()

                     fig_evol = make_subplots(specs=[[{"secondary_y": True}]])

                     # --- INVERSÃO AQUI ---
                     # Add LINE for daily value (Primary Y-axis)
                     fig_evol.add_trace(
                         go.Scatter(x=gastos_por_dia['Data'], y=gastos_por_dia['Valor'], name="Valor Diário", mode='lines+markers', line=dict(color='royalblue', width=2)),
                         secondary_y=False,
                     )
                     # Add BARS for cumulative balance (Secondary Y-axis)
                     fig_evol.add_trace(
                         go.Bar(x=gastos_por_dia['Data'], y=gastos_por_dia['Saldo Acumulado'], name="Saldo Acumulado", marker_color='lightsalmon', opacity=0.7),
                         secondary_y=True,
                     )
                     # --- FIM DA INVERSÃO ---

                     # Add limit line if gasto_limite is greater than 0
                     if gasto_limite > 0 and not gastos_por_dia.empty:
                         fig_evol.add_shape(
                             type="line",
                             x0=gastos_por_dia['Data'].min(), y0=gasto_limite,
                             x1=gastos_por_dia['Data'].max(), y1=gasto_limite,
                             line=dict(color="Red", width=2, dash="dash"),
                             xref='x', yref='y2' # Associate with the secondary y-axis
                         )
                         # Add annotation for the limit line
                         fig_evol.add_annotation(
                             x=gastos_por_dia['Data'].max(), y=gasto_limite, yref='y2',
                             text=f"Limite R$ {gasto_limite:.2f}",
                             showarrow=False, yshift=10, xanchor="right",
                             font=dict(color="red", size=10)
                         )


                     fig_evol.update_layout(
                         title_text="Valor Diário e Saldo Acumulado",
                         xaxis_title="Data",
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                         hovermode='x unified' # Improve hover experience
                     )
                     # Adjust axis colors to match the traces (optional, but good practice)
                     fig_evol.update_yaxes(title_text="Valor Diário (R$)", secondary_y=False, title_font_color='royalblue', tickfont_color='royalblue')
                     fig_evol.update_yaxes(title_text="Saldo Acumulado (R$)", secondary_y=True, title_font_color='lightsalmon', tickfont_color='lightsalmon')

                     st.plotly_chart(fig_evol, use_container_width=True)
                 else:
                     st.info("Não há dados para o período de evolução selecionado ou após filtros.")

             else:
                 st.info(f"Aplique filtros ou categorize lançamentos com '{nivel_grafico}' válidos para ver os gráficos.")
        else:
             st.info("Clique em 'Atualizar Gráficos' para exibir as visualizações.")

        # --- Outras Análises ---
        st.subheader("Outras Análises")
        st.markdown("**Maiores Valores (Top 5)**") # Changed title
        # Use the current state of df_fatura for this analysis
        if st.session_state.df_fatura is not None and not st.session_state.df_fatura.empty:
            df_analysis = st.session_state.df_fatura.copy()
            df_analysis['Valor'] = pd.to_numeric(df_analysis['Valor'], errors='coerce')
            # Find largest values (which are now non-negative)
            maiores_valores = df_analysis.nlargest(5, 'Valor')

            if not maiores_valores.empty:
                st.dataframe(
                    maiores_valores[['Data', 'Descricao', 'Valor', 'Categoria Nível 1', 'Categoria Nível 2']],
                    column_config={
                        "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "Descricao": st.column_config.TextColumn("Descrição"),
                        "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"), # Display as positive
                        "Categoria Nível 1": st.column_config.TextColumn("Cat. Nv1"),
                        "Categoria Nível 2": st.column_config.TextColumn("Cat. Nv2"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                 st.info("Não há dados para exibir os maiores valores.")
        else:
            st.info("Carregue dados para ver os maiores valores.")

    elif uploaded_file is not None and st.session_state.df_fatura is None:
         st.warning("Não foi possível processar o arquivo. Verifique se ele contém as colunas 'data', 'lançamento' e 'valor' e se o formato da data é DD/MM/YYYY.")

else:
    st.info("⬅️ Carregue um arquivo Excel ou CSV na barra lateral. O arquivo deve conter as colunas 'data', 'lançamento' e 'valor'.")


# --- Rodapé ---
st.markdown("---")
st.caption(f"Análise de Fatura | v2.17 (Corrected Page Links Relative to Entrypoint) | {datetime.now().year}")
