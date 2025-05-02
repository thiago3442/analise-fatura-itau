# 📊 Análise de Fatura de Cartão de Crédito (Streamlit)

Uma aplicação web simples desenvolvida com Python e Streamlit para analisar e visualizar lançamentos de faturas de cartão de crédito exportadas do internet banking (adaptado para um formato específico do Itaú).

## 📝 Descrição

Esta ferramenta permite que você faça o upload do arquivo CSV da sua fatura de cartão de crédito (originalmente um `.xls` do Itaú, mas exportado/salvo como `.csv`) e obtenha insights sobre seus gastos. Ela calcula o total da fatura, os dias restantes até o fechamento, permite categorizar manualmente as despesas (com sugestões automáticas) e exibe gráficos interativos.

**Importante:** O código foi ajustado especificamente para lidar com a estrutura do arquivo `Fatura-Excel (2).xls - Lançamentos.csv` fornecido, que possui cabeçalhos e informações sumárias nas primeiras 24 linhas.

## ✨ Funcionalidades

* **Upload de Arquivo:** Carregue seu arquivo de fatura em formato CSV.
* **Cálculo Automático:** Exibe o **valor total** da fatura carregada.
* **Contagem Regressiva:** Mostra quantos **dias faltam** para o fechamento da fatura (requer input do dia de fechamento).
* **Categorização Interativa:**
    * Atribua categorias a cada lançamento usando uma caixa de seleção.
    * Receba sugestões automáticas de categorias baseadas em palavras-chave na descrição do lançamento.
    * O sistema "lembra" as categorias atribuídas para descrições específicas durante a sessão atual.
* **Visualizações Gráficas (Plotly):**
    * Gráfico de Pizza: Distribuição percentual dos gastos por categoria.
    * Gráfico de Barras: Valor total gasto por categoria.
    * Gráfico de Linha: Evolução dos gastos diários ao longo do período da fatura.
* **Análise Adicional:** Identifica as 5 maiores despesas individuais.

## 🚀 Tecnologias Utilizadas

* **Python 3**
* **Streamlit:** Para a interface web interativa.
* **Pandas:** Para leitura e manipulação dos dados do arquivo CSV.
* **Plotly:** Para a criação dos gráficos interativos.

## 📁 Estrutura do Projeto

```
seu-repositorio/
│
├── app.py             # O código principal da aplicação Streamlit
├── requirements.txt   # Lista de dependências Python
└── README.md          # Este arquivo
```

## ⚙️ Como Começar

Siga estas instruções para configurar e executar o projeto localmente.

### Pré-requisitos

* **Python 3.7+:** Certifique-se de ter o Python instalado. Você pode baixá-lo em [python.org](https://www.python.org/).
* **pip:** O gerenciador de pacotes do Python (geralmente vem com o Python).

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
    cd seu-repositorio
    ```
    *(Substitua `seu-usuario/seu-repositorio` pelo URL do seu repositório)*

2.  **Crie um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    ```
    * No Windows: `venv\Scripts\activate`
    * No macOS/Linux: `source venv/bin/activate`

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

### Executando a Aplicação

1.  **Navegue até a pasta do projeto** (se ainda não estiver lá).
2.  **Execute o Streamlit:**
    ```bash
    streamlit run app.py
    ```
3.  A aplicação será aberta automaticamente no seu navegador web padrão. Se não abrir, acesse o endereço local exibido no terminal (geralmente `http://localhost:8501`).

## 🖱️ Como Usar

1.  **Carregue o arquivo:** Na barra lateral esquerda, clique em "Browse files" e selecione o arquivo `.csv` da sua fatura.
2.  **Informe o dia de fechamento:** Digite o dia do mês em que sua fatura normalmente fecha (ex: 20).
3.  **Analise os dados:**
    * Veja o resumo com o total da fatura e os dias restantes.
    * Na tabela "Lançamentos e Categorização", clique na coluna "Categoria" de cada linha para atribuir a categoria correta. Aproveite as sugestões pré-preenchidas.
    * Explore os gráficos interativos que são atualizados conforme você categoriza.
    * Verifique as maiores despesas listadas.

## 📄 Formato do Arquivo de Entrada

A aplicação está configurada para ler um arquivo **CSV** com as seguintes características (baseado no `Fatura-Excel (2).xls - Lançamentos.csv`):

* **Codificação:** UTF-8
* **Separador:** Vírgula (`,`)
* **Cabeçalho de Dados:** A linha contendo os nomes das colunas de transação (`data,lançamento,,valor`) deve estar na **Linha 25**. As 24 linhas anteriores são ignoradas (`skiprows=24`).
* **Colunas Essenciais:**
    * `data`: Contendo a data da transação no formato `DD/MM/YYYY`.
    * `lançamento`: Contendo a descrição/estabelecimento da transação.
    * `valor`: Contendo o valor da transação como número, usando ponto (`.`) como separador decimal (ex: `105.96`, `203.68`).

Se o seu arquivo exportado do banco tiver uma estrutura diferente, será necessário ajustar a função `load_data` no arquivo `app.py`, especialmente os parâmetros `skiprows`, `sep` e o mapeamento dos nomes das colunas.

## 🔧 Customização

Você pode melhorar as sugestões automáticas de categoria editando o dicionário `CATEGORIZATION_RULES` dentro do arquivo `app.py`. Adicione novas palavras-chave (em minúsculas) e a categoria correspondente:

```python
# Exemplo dentro de app.py
CATEGORIZATION_RULES = {
    'ifood': 'Alimentação',
    'uber': 'Transporte',
    'seu_novo_estabelecimento': 'Nova Categoria',
    # ... adicione mais regras aqui
}
```


## 🖼️ Screenshots


![Exemplo de Screenshot 1](caminho/para/screenshot1.png)
![Exemplo de Screenshot 2](caminho/para/screenshot2.png)


## 📜 Licença
Este projeto é distribuído sob a licença MIT. Veja o arquivo LICENSE (se você adicionar um) para mais detalhes.


## 🤝 Contribuições
Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## 👤 Autor

- GitHub: thiago3442
- thiago3442@gmail.com
