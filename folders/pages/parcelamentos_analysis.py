# -*- coding: utf-8 -*- # Define encoding
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import numpy as np
import re
import calendar # Import calendar for month names

# --- Configuração da Página Streamlit ---
st.set_page_config(page_title="Análise de Parcelamentos", page_icon="💳", layout="wide")

# --- Funções Auxiliares (Copied from app.py for self-containment) ---
# Note: In a real multi-page app, you might put shared functions in a separate utility file
# and import them. For this example, copying for simplicity.
def limpar_valor(valor):
    """Cleans currency strings and converts to float."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor) is str:
        # Remove currency symbols, spaces, and replace comma decimal separator
        valor_limpo = re.sub(r'[R$\s]', '', valor).replace(',', '.')
        try:
            return float(valor_limpo)
        except ValueError:
            # Handle cases where comma might be used as thousands separator
            valor_limpo_alt = valor.replace('.', '').replace(',', '.')
            try:
                return float(valor_limpo_alt)
            except ValueError:
                return np.nan # Return NaN if conversion fails
    return np.nan # Return NaN for other types

# We don't need load_rules_from_excel or suggest_categories_v2 here
# as categorization is done on the main page.

# --- New Function to Parse Parcelamento Description ---
def parse_parcelamento_description(description):
    """
    Parses a parcelamento description (e.g., 'COMPRA PARCELADA 05/10')
    to extract current and total installments.

    Args:
        description (str): The transaction description.

    Returns:
        tuple: (current_installment, total_installments) or (None, None) if not found.
    """
    if not isinstance(description, str):
        return None, None

    # Look for the XX/YY pattern
    match = re.search(r'\b(\d{1,2})/(\d{1,2})\b', description)
    if match:
        try:
            current = int(match.group(1))
            total = int(match.group(2))
            # Basic validation: current should not be greater than total
            if 1 <= current <= total:
                return current, total
        except ValueError:
            pass # Ignore if conversion to int fails

    return None, None # Return None if pattern not found or invalid

# --- Page Content ---
st.title("💳 Análise Detalhada de Parcelamentos")

# Access the processed data from session state
if 'df_fatura' in st.session_state and st.session_state.df_fatura is not None:
    df_fatura = st.session_state.df_fatura.copy()

    # Filter for Parcelamento transactions
    df_parcelamentos = df_fatura[df_fatura['Categoria Nível 1'] == 'Parcelamento'].copy()

    if df_parcelamentos.empty:
        st.info("Não há lançamentos categorizados como 'Parcelamento' para analisar.")
    else:
        # --- Extract Parcelamento Details ---
        df_parcelamentos[['Parcela Atual', 'Total Parcelas']] = df_parcelamentos['Descricao'].apply(
            lambda x: pd.Series(parse_parcelamento_description(x))
        )

        # Filter out rows where parcelamento info couldn't be parsed
        df_parcelamentos = df_parcelamentos.dropna(subset=['Parcela Atual', 'Total Parcelas'])

        if df_parcelamentos.empty:
             st.warning("Nenhum lançamento de 'Parcelamento' encontrado com o formato 'XX/YY' na descrição.")
        else:
            # Ensure installment columns are integers
            df_parcelamentos['Parcela Atual'] = df_parcelamentos['Parcela Atual'].astype(int)
            df_parcelamentos['Total Parcelas'] = df_parcelamentos['Total Parcelas'].astype(int)

            # Calculate remaining installments and remaining value for each transaction
            df_parcelamentos['Parcelas Restantes'] = df_parcelamentos['Total Parcelas'] - df_parcelamentos['Parcela Atual']
            # Calculate the value per installment (assuming equal installments)
            df_parcelamentos['Valor por Parcela'] = df_parcelamentos['Valor'] / df_parcelamentos['Parcela Atual']
            df_parcelamentos['Valor Restante'] = df_parcelamentos['Parcelas Restantes'] * df_parcelamentos['Valor por Parcela']


            # --- Projection Logic ---
            st.subheader("Projeção de Parcelamentos Futuros")

            # Get the earliest date among the parcelamentos
            earliest_parcelamento_date = df_parcelamentos['Data'].min()
            # Determine the default start month for projection (the month after the last transaction or current month)
            default_start_month = (datetime.now().date().replace(day=1) + timedelta(days=32)).replace(day=1) # Start next month

            # Create a list of months for the selectbox
            month_options = []
            # Project a few years into the future to populate the selectbox
            for i in range(36): # Project 3 years
                month_date = (date.today().replace(day=1) + timedelta(days=30*i)).replace(day=1)
                month_options.append(f"{calendar.month_name[month_date.month]}/{month_date.year}")

            # Selectbox for the starting month of the projection
            selected_start_month_str = st.selectbox(
                "Selecione o mês de início da projeção:",
                options=month_options,
                index=month_options.index(f"{calendar.month_name[default_start_month.month]}/{default_start_month.year}") if f"{calendar.month_name[default_start_month.month]}/{default_start_month.year}" in month_options else 0,
                key='projection_start_month'
            )

            # Convert selected start month string to a datetime object (first day of the month)
            selected_start_month = datetime.strptime(selected_start_month_str, "%B/%Y").date().replace(day=1)


            # Create a DataFrame for the monthly projection
            monthly_projection = {}

            # Iterate through each parcelamento transaction
            for index, row in df_parcelamentos.iterrows():
                current_installment = row['Parcela Atual']
                total_installments = row['Total Parcelas']
                value_per_installment = row['Valor por Parcela']
                transaction_date = row['Data'].date() # Use date part for month calculation

                # Project the future installments for this transaction
                for i in range(row['Parcelas Restantes']):
                    # Calculate the month of the future installment
                    # Start from the month *after* the transaction month + current installment count
                    # Example: Transaction in Jan (month 1), 1/10. Next payment is Feb (month 2).
                    # If 5/10 in Jan, next payment is Feb (month 2).
                    # The month of the next payment is the month of the transaction + the current installment number.
                    # However, if the transaction date is late in the month, the *next* payment might be in the month
                    # corresponding to the current installment + 1. Let's simplify and assume the next payment
                    # occurs in the month after the transaction month + current installment count.

                    # Calculate the month index relative to the transaction month
                    # If transaction is in Jan (month 1) and it's 1/10, the next payment is in month 1 + 1 = month 2.
                    # If transaction is in Jan and it's 5/10, the next payment is in month 1 + 5 = month 6.
                    # The installment number XX corresponds to the XX-th payment, which happens in the month
                    # corresponding to the transaction month + (XX-1).
                    # So, the (i+1)-th remaining installment (where i starts from 0) will be in the month
                    # corresponding to the transaction month + current_installment + i.

                    # Calculate the month of the *current* installment
                    current_installment_month = transaction_date.replace(day=1) + pd.DateOffset(months=current_installment -1)

                    # Calculate the month of the *future* installment (i-th remaining installment)
                    future_installment_month = current_installment_month + pd.DateOffset(months=i)


                    # Only consider installments that are in or after the selected start month
                    if future_installment_month.date() >= selected_start_month:
                        month_key = future_installment_month.strftime("%Y-%m") # Use YYYY-MM for sorting
                        if month_key not in monthly_projection:
                            monthly_projection[month_key] = 0
                        monthly_projection[month_key] += value_per_installment


            # Convert the projection dictionary to a DataFrame
            if monthly_projection:
                df_monthly_projection = pd.DataFrame.from_dict(monthly_projection, orient='index', columns=['Valor Projetado'])
                df_monthly_projection.index = pd.to_datetime(df_monthly_projection.index)
                df_monthly_projection = df_monthly_projection.sort_index()

                # Add a column for Month/Year label for plotting
                df_monthly_projection['Mês/Ano'] = df_monthly_projection.index.strftime("%B/%Y")

                # --- Monthly Projection Chart ---
                st.markdown("---")
                st.subheader("Projeção Mensal de Parcelamentos")

                fig_projection = px.line(
                    df_monthly_projection,
                    x='Mês/Ano',
                    y='Valor Projetado',
                    title="Projeção Mensal de Parcelamentos (R$)",
                    labels={'Valor Projetado': 'Valor Projetado (R$)', 'Mês/Ano': 'Mês/Ano'},
                    markers=True
                )
                fig_projection.update_layout(xaxis_title="Mês/Ano", yaxis_title="Valor Projetado (R$)")
                st.plotly_chart(fig_projection, use_container_width=True)

                # --- Total Remaining Parcelamento Value ---
                total_remaining_parcelamentos = df_parcelamentos['Valor Restante'].sum()
                st.markdown(f"**Total Restante de Parcelamentos:** R$ {total_remaining_parcelamentos:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))


            else:
                st.info("Não há parcelamentos futuros a partir do mês selecionado.")


            # --- Table of Parcelamento Details ---
            st.markdown("---")
            st.subheader("Detalhes dos Lançamentos de Parcelamento")
            st.dataframe(
                df_parcelamentos[['Data', 'Descricao', 'Valor', 'Categoria Nível 1', 'Categoria Nível 2', 'Parcela Atual', 'Total Parcelas', 'Parcelas Restantes', 'Valor por Parcela', 'Valor Restante']],
                column_config={
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "Descricao": st.column_config.TextColumn("Descrição"),
                    "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                    "Categoria Nível 1": st.column_config.TextColumn("Cat. Nv1"),
                    "Categoria Nível 2": st.column_config.TextColumn("Cat. Nv2"),
                    "Parcela Atual": st.column_config.NumberColumn("Parcela Atual"),
                    "Total Parcelas": st.column_config.NumberColumn("Total Parcelas"),
                    "Parcelas Restantes": st.column_config.NumberColumn("Parcelas Restantes"),
                    "Valor por Parcela": st.column_config.NumberColumn("Valor/Parcela (R$)", format="R$ %.2f"),
                    "Valor Restante": st.column_config.NumberColumn("Valor Restante (R$)", format="R$ %.2f"),
                },
                use_container_width=True,
                hide_index=True
            )

else:
    st.info("Por favor, carregue um arquivo na página 'Visão Geral' para analisar os parcelamentos.")

# --- Rodapé ---
st.markdown("---")
st.caption(f"Análise de Fatura | Página de Parcelamentos | {datetime.now().year}")
