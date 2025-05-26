This project is a web application designed for personal finance management. Its primary function is to analyze credit card statements, enabling users to gain insights into their spending habits. Users can upload their statements in Excel or CSV format. The application then processes this data, automatically categorizes expenses based on predefined rules, and allows for manual categorization. Key features include data visualization and in-depth analysis and projection of installment payments. This tool helps users track and understand their expenditures, particularly those made via credit card.

## Key Technologies Used
- Python
- Streamlit (for the web interface)
- Pandas (for data manipulation)
- Plotly (for interactive charts)
- Openpyxl (for reading Excel files)
- Numpy (for numerical operations, often a Pandas dependency)

## Core Functionalities

### Data Ingestion and Processing
The application's `load_data` function is responsible for ingesting and preparing user-uploaded financial data. Key capabilities include:
- **File Format Support:** Accepts both Excel (.xls, .xlsx) and CSV (.csv) files.
- **Currency Cleaning:** Implements a `limpar_valor` helper function to clean currency strings by removing symbols (R$), spaces, and standardizing decimal separators (comma to period) before converting to float. It can handle values that are already numeric.
- **Flexible CSV Parsing:** When handling CSV files, the system attempts to read the data using multiple encodings (UTF-8 and ISO-8859-1) and common separators (comma and semicolon) to maximize compatibility.
- **Column Standardization:** It looks for essential columns using a predefined mapping ('data', 'lançamento', 'valor') and matches them case-insensitively from the uploaded file. If these columns aren't found, it reports an error.
- **Date Conversion:** The 'data' column undergoes robust conversion to datetime objects. The system attempts to parse dates using several common formats (e.g., DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY, DD-MM-YYYY) to accommodate various statement styles.
- **Exclusion of Negative Values:** A critical processing step is the exclusion of any rows where the 'Valor' (value/amount) column is negative. This ensures analyses focus on expenditures or positive transactions.
- **Category Initialization:** After loading and basic cleaning, new columns 'Categoria Nível 1' and 'Categoria Nível 2' are added and initialized ('Não categorizado' and None, respectively) to prepare for expense categorization.
- **Data Sorting:** Upon successful processing, the entire dataset is sorted by date in ascending order.

### Expense Categorization
The application employs a sophisticated system for categorizing expenses, offering both automation and user control:
- **Two-Level System:** Expenses are organized into a two-tier hierarchy: 'Categoria Nível 1' for general categories (e.g., "Alimentação", "Transporte") and 'Categoria Nível 2' for more detailed sub-categories (e.g., "Restaurante", "Uber").
- **Rule-Based Automatic Categorization:**
    - The primary mechanism for automatic categorization relies on rules defined in an external Excel file, `regras_categorizacao.xlsx`.
    - The `load_rules_from_excel` function is designed for flexibility in reading this file. It searches for columns containing keywords and their corresponding categories using a list of common aliases. For instance, it looks for keyword columns like 'lançamento', 'Lançamento', 'Descrição', 'Keyword', etc. For category levels, it searches for 'CategoriaNivel1', 'CatNivel1', 'Cat1' (for Level 1) and 'CategoriaNivel2', 'CatNivel2', 'Cat2' (for Level 2).
    - Keywords from the rules file are converted to lowercase and stripped of leading/trailing spaces. When matching, the system prioritizes longer keywords to ensure more specific rules are applied first.
- **Suggestion Engine (`suggest_categories_v2`):**
    - This function takes a transaction description and applies the loaded rules to suggest 'Categoria Nível 1' and 'Categoria Nível 2'.
    - It includes special logic to identify "Parcelamento" (installments) by searching for patterns like "NN/NN" (e.g., "01/12", "03/06") within the transaction description. If such a pattern is found, the 'Categoria Nível 1' is initially set to "Parcelamento". This can be overridden by a more specific rule from the Excel file if one matches the description.
    - If no rule sets a 'Categoria Nível 2', but 'Categoria Nível 1' is set (and not 'Não categorizado'), a default 'Categoria Nível 2' like 'Geral' may be applied.
- **Manual Categorization Interface:**
    - Users have the final say over categorization. The application displays the transactions in an interactive table using Streamlit's `st.data_editor`.
    - Within this table, users can directly modify the 'Categoria Nível 1' and 'Categoria Nível 2' for any transaction using dropdown select boxes populated with existing and rule-defined categories.
- **Session-Based Memory for Edits:**
    - When a user manually changes the categories for a specific transaction description, these changes are stored in the session state (`st.session_state.categorias_mapeadas`).
    - This means that if the same description appears multiple times in the uploaded file (or if the user re-processes the same file within the session), the manually set categories will be consistently applied, though this mapping is cleared when a new file is uploaded.

### Main Page ('Visão Geral') Features
The "Visão Geral" (General Overview) page, primarily managed by `folders/app.py`, serves as the main dashboard for users after they upload their statement. It offers the following features:

- **Key Metrics Displayed:**
    - **Total Value:** A prominent display of the total sum of all non-negative 'Valor' (value) entries from the processed statement, formatted as currency (R$).
- **Interactive Visualizations (using Plotly):**
    - **Categorical Pie Chart:** Illustrates the proportion of expenses across different categories. Users can switch the view between 'Categoria Nível 1' (general) and 'Categoria Nível 2' (detailed) using a radio button in the sidebar.
    - **Categorical Bar Chart:** Presents the total sum of expenses for each category, also switchable between 'Categoria Nível 1' and 'Categoria Nível 2'. This chart helps identify which categories contribute most to spending.
    - **Evolution Chart (Line/Bar Combo):**
        - Visualizes daily spending patterns (as a line chart) and the cumulative total spending (as a bar chart) over time.
        - Users can select a custom date range (start and end dates) for this chart.
        - A feature allows users to input a "Limite Saldo Acumulado" (Cumulative Balance Limit). If a value greater than zero is entered, a horizontal dashed red line representing this limit is drawn on the chart, providing a visual cue against the cumulative spending.
    - **Nested Nível 2 Charts:** If the user filters the main view by one or more 'Categoria Nível 1' categories, this section dynamically generates detailed pie and bar charts for each selected 'Categoria Nível 1'. These nested charts break down the spending within that Nível 1 category by its corresponding 'Categoria Nível 2' sub-categories.
- **Filtering Capabilities:**
    - **Category Filters:** Users can refine the data displayed in all charts using multi-select boxes for both 'Categoria Nível 1' and 'Categoria Nível 2'. This allows for focused analysis on specific spending areas.
    - **Date Range Filter:** As mentioned, the evolution chart has specific date input fields to narrow down the time period for analysis.
- **"Top 5 Expenses" Display:**
    - A table lists the five transactions with the highest 'Valor' (amount), showing their date, description, value, and assigned categories (Nível 1 and Nível 2). This helps users quickly identify significant expenditures.
- **User Interface Elements:**
    - **Data Editor Grid:** Transactions are displayed in an interactive grid (`st.data_editor`) where users can not only view the data but also directly edit the 'Categoria Nível 1' and 'Categoria Nível 2' for each transaction.
    - **Sidebar Controls:** A persistent sidebar houses:
        - The file uploader for Excel or CSV files.
        - Radio buttons to select the category level (Nível 1 or Nível 2) for the main summary charts.
        - Navigation links to other pages of the application (e.g., "Análise de Parcelamentos").
    - **Update Button:** An "Atualizar Gráficos" (Update Charts) button allows users to manually refresh the visualizations after making changes to category filters or edits in the data editor.

### Installment Analysis Page ('Análise de Parcelamentos')
This page, managed by `folders/pages/parcelamentos_analysis.py`, is dedicated to providing a detailed view and projection of installment payments.

- **Data Source:** It operates on the data processed and categorized on the "Visão Geral" page. Specifically, it filters for transactions where 'Categoria Nível 1' is "Parcelamento", accessing this data from Streamlit's session state (`st.session_state.df_fatura`).
- **Installment Detail Parsing:**
    - A key function, `parse_parcelamento_description`, is used to interpret transaction descriptions that contain installment information. It searches for patterns like "XX/YY" (e.g., "Compra ABC 02/05") to extract the current installment number (2) and the total number of installments (5).
- **Core Calculations:**
    - **Remaining Installments:** For each installment transaction, it calculates 'Parcelas Restantes' (Remaining Installments) by subtracting the 'Parcela Atual' (Current Installment) from 'Total Parcelas' (Total Installments).
    - **Value per Installment:** It estimates the 'Valor por Parcela' (Value per Installment) by dividing the 'Valor' (current transaction value) by the 'Parcela Atual'. This assumes that the value recorded is the cumulative value up to the current installment, and all installments are of equal value.
    - **Remaining Value:** Based on the 'Valor por Parcela' and 'Parcelas Restantes', it calculates the 'Valor Restante' (Remaining Value) for each ongoing installment plan.
- **Future Payment Projection:**
    - The page projects the total outflow due to installment payments for upcoming months.
    - Users are provided with a select box to choose the "mês de início da projeção" (starting month for the projection). The options typically span a few years into the future.
    - The projected payments for each future month are then visualized using a line chart (`plotly.express.line`), showing the expected total amount due from all active installments in those months.
- **Data Display and Summaries:**
    - **Total Remaining Value:** A summary metric displays the "Total Restante de Parcelamentos," which is the sum of 'Valor Restante' across all identified installment plans.
    - **Detailed Table:** A comprehensive table lists all transactions categorized as "Parcelamento". This table includes:
        - Original transaction data (Date, Description, Value, Categories).
        - Parsed installment details: 'Parcela Atual', 'Total Parcelas'.
        - Calculated fields: 'Parcelas Restantes', 'Valor por Parcela', 'Valor Restante'.
        This allows users to scrutinize individual installment plans and their future commitments.

## Project Structure
The project is organized as a multi-page Streamlit web application with a clear separation of concerns:

- **Multi-page Streamlit Application Layout:**
    - `folders/app.py`: This script is the main entry point for the Streamlit application. It hosts the primary user interface, referred to as "Visão Geral" (General Overview), where users upload data and see a general analysis.
    - `folders/pages/`: This subdirectory adheres to Streamlit's convention for creating multi-page applications. Each `.py` file within this directory typically corresponds to a separate page or section of the application.
        - `parcelamentos_analysis.py`: Located in `folders/pages/`, this script defines the "Análise de Parcelamentos" (Installment Analysis) page, providing specialized tools for installment tracking and projection.

- **Key Supporting Files:**
    - `regras_categorizacao.xlsx`: This Excel file is crucial for the application's functionality. It is located in the root directory of the project (from the perspective of `folders/app.py`, it is accessed as `../regras_categorizacao.xlsx`). It stores user-defined rules (keywords and corresponding categories) that the application uses for automatically categorizing transactions.
    - `requirements.txt`: Standard Python project file listing all external library dependencies (e.g., Streamlit, Pandas, Plotly, Openpyxl, Numpy) required to run the application.
    - `README.md`: The primary markdown file providing an overview of the project, its purpose, and setup instructions. (Note: Some details in the README might not fully reflect the current multi-page structure if not updated.)
    - `.gitignore`: A standard Git file that specifies which files and directories should be ignored by the version control system (e.g., temporary files, environment-specific files).
    - `LICENSE`: Contains the software license under which the project is distributed.
    - `project_summary.md`: This document (the one currently being generated) provides a detailed summary of the project's functionalities and structure.

- **Overall Organization:**
    The project's structure effectively separates the core application logic (within `folders/app.py`), specific page functionalities (within `folders/pages/`), and external configurations or data (like `regras_categorizacao.xlsx` and `requirements.txt`). This modular design promotes maintainability and scalability.

## Configuration and Customization
The application offers a significant degree of customization for its core expense categorization logic, primarily through an external Excel file, without requiring any changes to the underlying Python code.

- **Primary Customization Method:**
    - Users can tailor the automatic expense categorization by directly editing the `regras_categorizacao.xlsx` file. This file is located in the project's root directory and serves as the central repository for categorization rules.

- **Rule Definition in `regras_categorizacao.xlsx`:**
    - **Adding/Modifying Rules:** Users can add new rows to define new rules, modify existing rows to adjust categories, or delete rows to remove rules.
    - **Rule Structure:** Each row in the Excel file represents a single categorization rule. A typical rule consists of three key pieces of information:
        1.  A **keyword or phrase** to be searched within the transaction descriptions (e.g., "UBER TRIP", "NETFLIX").
        2.  A corresponding **'Categoria Nível 1'** (e.g., "Transporte", "Assinaturas").
        3.  A corresponding **'Categoria Nível 2'** (e.g., "Aplicativo", "Streaming Video").

- **Flexibility in Excel Column Naming:**
    - The `load_rules_from_excel` function in `folders/app.py` is designed to be robust against variations in the exact column names used in the `regras_categorizacao.xlsx` file.
    - For instance, it will search for the keyword column under various common names like 'lançamento', 'Lançamento', 'Descrição', 'Descricao', 'Estabelecimento', 'PalavraChave', 'Keyword', or 'Chave'.
    - Similarly, for Level 1 categories, it looks for headers such as 'CategoriaNivel1', 'CategoriaGeral', 'CatNivel1', or 'Cat1'.
    - For Level 2 categories, it checks for 'CategoriaNivel2', 'CategoriaDetalhada', 'CatNivel2', or 'Cat2'.
    - This flexibility allows users to more easily adapt existing spreadsheets they might have for defining rules, rather than being forced to adhere to a strictly predefined template.

- **Impact of Customization:**
    - Any modifications made to `regras_categorizacao.xlsx` directly and immediately influence the automatic categorization suggestions made by the `suggest_categories_v2` function. When a statement is processed, the application reads the latest rules from this file to categorize transactions.

- **No Code Changes Needed for Customization:**
    - A key advantage of this system is that users can extensively customize the categorization logic (by editing the Excel file) without needing to delve into or alter the Python source code of the application. This makes personalization accessible to users who may not be programmers.

## Important Processing Logic Notes
Beyond the main data ingestion and categorization flows, several specific processing steps are crucial for the application's behavior and accuracy:

1.  **Exclusion of Negative Values:**
    - **Implementation:** Within the `load_data` function (in `folders/app.py`), after the 'Valor' (value/amount) column is cleaned and converted to a numeric type, a filtering step is applied: `df = df[df['Valor'] >= 0].copy()`.
    - **Implication:** This line explicitly removes any rows from the dataset where the 'Valor' is negative. As a result, the application is designed to focus its analyses (totals, charts, tables, and categorizations) exclusively on positive financial transactions, which are typically expenditures. Negative values, which might represent refunds, credits, chargebacks, or statement payments, are intentionally excluded from all subsequent calculations and displays. This ensures that metrics like "Total Gasto" (Total Spent) accurately reflect outgoings.

2.  **"Parcelamento" (Installment) Identification and Handling:**
    - **Initial Identification (`suggest_categories_v2`):** The `suggest_categories_v2` function in `folders/app.py` incorporates a specific regular expression `r'\b(\d{1,2}/\d{1,2})\b'` to automatically detect potential installment payments directly from the transaction description. If a description contains a pattern like "01/10" or "05/12", the 'Categoria Nível 1' is preliminarily set to "Parcelamento".
    - **Rule Override:** This initial regex-based identification is not absolute. If a user has defined a more specific rule in the `regras_categorizacao.xlsx` file that matches the description of an installment transaction but assigns it to a different category (e.g., a specific "Assinatura" or "Compra Online" that happens to be an installment), the rule from the Excel file will take precedence. The `suggest_categories_v2` function applies rules from `loaded_rules` after the initial "Parcelamento" check, allowing this override.
    - **Significance for "Análise de Parcelamentos" Page:** The accurate identification of transactions as "Parcelamento" (either by regex or by rule) is fundamental for the functionality of the dedicated "Análise de Parcelamentos" page. This page relies on these categorized transactions to perform its detailed calculations of remaining installments, value per installment, and future payment projections. Without this specific categorization, installment transactions would not be processed by this specialized analysis tool.
