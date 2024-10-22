import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import certifi

MONGODB_URI = st.secrets["MONGODB_URI"]

# Usando certifi para garantir o CA SSL correto e adicionando parâmetros para TLS
client = MongoClient(
    MONGODB_URI, 
    tls=True, 
    tlsCAFile=certifi.where(), 
    tlsAllowInvalidCertificates=False,
    serverSelectionTimeoutMS=30000  # Timeout de 30 segundos
)

# Verificar conexão com MongoDB
try:
    client.admin.command('ping')  # Verificar se a conexão é bem-sucedida
    db = client['PersonalFinances']
    expenses_collection = db['expenses']
    print("Conexão com o MongoDB estabelecida com sucesso!")
except Exception as e:
    print(f"Erro de conexão com o MongoDB: {e}")
    sys.exit(1)  # type: ignore # Encerra o programa com código de erro

# Função para agrupar despesas por mês
def group_expenses_by_month():
    pipeline = [
        {
            "$group": {
                "_id": {
                    "month": {"$month": "$date"},
                    "year": {"$year": "$date"},
                },
                "totalAmount": {"$sum": "$amount"},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    result = expenses_collection.aggregate(pipeline)
    return {f'{item["_id"]["month"]}/{item["_id"]["year"]}': item["totalAmount"] for item in result}

# Função para obter despesas por categoria
def group_expenses_by_category(month, year):
    pipeline = [
        {
            "$match": {
                "$expr": {
                    "$and": [
                        {"$eq": [{"$month": "$date"}, month]},
                        {"$eq": [{"$year": "$date"}, year]}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$category",
                "totalAmount": {"$sum": "$amount"}
            }
        }
    ]
    result = expenses_collection.aggregate(pipeline)
    return {item["_id"]: item["totalAmount"] for item in result}

# Função para obter despesas diárias
def group_expenses_by_day(month, year):
    pipeline = [
        {
            "$match": {
                "$expr": {
                    "$and": [
                        {"$eq": [{"$month": "$date"}, month]},
                        {"$eq": [{"$year": "$date"}, year]}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {"$dayOfMonth": "$date"},
                "totalAmount": {"$sum": "$amount"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    result = expenses_collection.aggregate(pipeline)
    return {item["_id"]: item["totalAmount"] for item in result}

# Função para converter datetime.date para datetime.datetime
def convert_to_datetime(d):
    if isinstance(d, date):
        return datetime.combine(d, datetime.min.time())
    return d

# Função para adicionar uma nova despesa
def add_expense(name, amount, date, category):
    try:
        new_expense = {
            "name": name,
            "amount": amount,
            "date": convert_to_datetime(date),
            "category": category,
            "is_paid": False,
            "payment_date": None
        }
        expenses_collection.insert_one(new_expense)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar despesa: {e}")
        return False

# Função para editar uma despesa existente
def edit_expense(expense_id, name, amount, date, category, is_paid, payment_date):
    try:
        update_fields = {
            "name": name,
            "amount": amount,
            "date": convert_to_datetime(date),
            "category": category,
            "is_paid": is_paid
        }
        if is_paid:
            update_fields["payment_date"] = convert_to_datetime(payment_date)
        else:
            update_fields["payment_date"] = None

        expenses_collection.update_one({"_id": expense_id}, {"$set": update_fields})
        return True
    except Exception as e:
        st.error(f"Erro ao editar a despesa: {e}")
        return False

# Função para listar todas as despesas
def get_all_expenses():
    return list(expenses_collection.find().sort("date", -1))

# Página principal - Despesas por Mês
def show_home_page():
    st.title("Despesas por Mês")

    # Gráfico de despesas mensais
    st.header("Gráfico de Despesas por Mês")
    monthly_expenses = group_expenses_by_month()

    if monthly_expenses:
        months = list(monthly_expenses.keys())
        amounts = list(monthly_expenses.values())

        # Definindo cores para o gráfico
        colors = px.colors.qualitative.Plotly  # Usando uma paleta de cores variada

        # Criando o gráfico de barras com diferentes cores
        fig = px.bar(
            x=months, 
            y=amounts, 
            labels={'x': 'Mês', 'y': 'Total (R$)'}, 
            title="Despesas por Mês", 
            color=months, 
            color_discrete_sequence=colors
        )

        st.plotly_chart(fig)
    else:
        st.write("Nenhuma despesa registrada ainda.")

    # Formulário para adicionar nova despesa
    st.header("Adicionar Nova Despesa")
    with st.form(key="add_expense_form"):
        name = st.text_input("Descrição", key='name')
        amount = st.number_input("Valor (R$)", min_value=0.0, key='amount')
        date_input = st.date_input("Data", value=datetime.today().date())  # Renomeado para evitar conflito com o módulo datetime
        category = st.selectbox(
            "Categoria", 
            ["💧 Água", "⚡ Energia", "🏠 Aluguel", "🌐 Internet"], 
            key='category_display'
        )
        category_value = category.replace('💧 ', '').replace('⚡ ', '').replace('🏠 ', '').replace('🌐 ', '')
        submit_button = st.form_submit_button("Adicionar")

        if submit_button:
            if name and amount > 0 and category:
                if add_expense(name, amount, date_input, category_value):
                    st.success(f"Despesa adicionada com sucesso: {name} - R$ {amount}")
                else:
                    st.error("Erro ao adicionar a despesa.")
            else:
                st.error("Por favor, preencha todos os campos corretamente.")

# Página de resumo de despesas
def show_summary_page():
    st.title("Resumo de Despesas do Período")

    # Filtro por mês e ano
    st.subheader("Filtrar por Mês e Ano")
    month = st.selectbox("Mês", list(range(1, 13)), index=datetime.today().month - 1)
    year = st.number_input("Ano", min_value=2000, max_value=2100, value=datetime.today().year)

    # Exibir todas as despesas em uma tabela
    st.header("Todas as Despesas")
    expenses = get_all_expenses()

    if expenses:
        df = pd.DataFrame(expenses)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')  # Formato brasileiro DD/MM/AAAA
        df['payment_date'] = pd.to_datetime(df['payment_date'], errors='coerce')  # Corrigir valores nulos
        df['payment_date'] = df['payment_date'].dt.strftime('%d/%m/%Y')  # Formato DD/MM/AAAA

        df.rename(columns={
            "name": "Descrição", 
            "amount": "Valor (R$)", 
            "category": "Categoria", 
            "date": "Data", 
            "is_paid": "Paga", 
            "payment_date": "Data de Pagamento"
        }, inplace=True)

        # Filtrando as despesas com base no mês e ano selecionados
        df['Mês'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.month
        df['Ano'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.year
        filtered_df = df[(df['Mês'] == month) & (df['Ano'] == year)]
        filtered_df['Valor (R$)'] = filtered_df['Valor (R$)'].apply(lambda x: float(str(x).replace(',', '.')))
        total_expenses = filtered_df['Valor (R$)'].sum()

        # Exibindo todas as colunas, incluindo os novos campos 'Paga' e 'Data de Pagamento'
        st.dataframe(filtered_df[['Descrição', 'Valor (R$)', 'Categoria', 'Data', 'Paga', 'Data de Pagamento']])
        st.write(f"**Total de Despesas: R$ {total_expenses:,.2f}".replace('.', ',').replace(',', '.', 1))

        # Gráfico de despesas por categoria - Aplicar o filtro corretamente
        st.subheader("Gráfico de Despesas por Categoria")
        category_expenses = group_expenses_by_category(month, year)  # Passar o filtro corretamente
        if category_expenses:
            categories = list(category_expenses.keys())
            totals = list(category_expenses.values())
            category_fig = px.pie(
                values=totals, 
                names=categories, 
                title="Despesas por Categoria"
            )
            st.plotly_chart(category_fig)

        # Gráfico de despesas diárias
        st.subheader("Total de Despesas por Dia")
        daily_expenses = group_expenses_by_day(month, year)
        if daily_expenses:
            days = list(daily_expenses.keys())
            amounts = list(daily_expenses.values())
            daily_fig = px.line(
                x=days, 
                y=amounts, 
                labels={'x': 'Dia', 'y': 'Total (R$)'}, 
                title="Total de Despesas Diárias"
            )
            st.plotly_chart(daily_fig)
        else:
            st.write(f"Nenhuma despesa registrada para {month}/{year}.")
    else:
        st.write("Nenhuma despesa registrada ainda.")

# Página de edição de despesas
def show_edit_page():
    st.title("Editar Despesas")

    # Filtro por mês e ano
    st.subheader("Filtrar por Mês e Ano para Edição")
    month = st.selectbox("Mês", list(range(1, 13)), index=datetime.today().month - 1, key='edit_month')
    year = st.number_input("Ano", min_value=2000, max_value=2100, value=datetime.today().year, key='edit_year')

    # Exibir todas as despesas em uma tabela e permitir edição
    st.header("Editar Despesas")
    expenses = get_all_expenses()

    if expenses:
        df = pd.DataFrame(expenses)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')  # Formato brasileiro
        df['payment_date'] = pd.to_datetime(df['payment_date'], errors='coerce')  # Corrigir valores nulos
        df['payment_date'] = df['payment_date'].dt.strftime('%d/%m/%Y')  # Formato DD/MM/AAAA

        df.rename(columns={
            "name": "Descrição", 
            "amount": "Valor (R$)", 
            "category": "Categoria", 
            "date": "Data", 
            "is_paid": "Paga", 
            "payment_date": "Data de Pagamento"
        }, inplace=True)

        # Filtrando as despesas com base no mês e ano selecionados
        df['Mês'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.month
        df['Ano'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.year
        filtered_df = df[(df['Mês'] == month) & (df['Ano'] == year)]

        if not filtered_df.empty:
            expense_options = filtered_df['Descrição'].unique().tolist()
            expense_to_edit = st.selectbox("Selecione a Despesa para Editar", expense_options)
            if expense_to_edit:
                expense_data = expenses_collection.find_one({"name": expense_to_edit})
                if expense_data:
                    with st.form(key="edit_expense_form"):
                        new_name = st.text_input("Descrição", value=expense_data.get("name", ""))
                        new_amount = st.number_input("Valor (R$)", min_value=0.0, value=expense_data.get("amount", 0.0))
                        new_date = st.date_input(
                            "Data", 
                            value=pd.to_datetime(expense_data.get("date")).date() if expense_data.get("date") else datetime.today().date()
                        )
                        category_options = ["Água", "Energia", "Aluguel", "Internet"]
                        current_category = expense_data.get('category', 'Outros')
                        if current_category not in category_options:
                            category_options.append(current_category)
                        new_category = st.selectbox(
                            "Categoria", 
                            category_options, 
                            index=category_options.index(current_category) if current_category in category_options else 0
                        )
                        is_paid = st.checkbox("Pago", value=expense_data.get("is_paid", False))
                        payment_date = None
                        if is_paid:
                            payment_date = st.date_input(
                                "Data de Pagamento", 
                                value=pd.to_datetime(expense_data.get("payment_date")).date() if expense_data.get("payment_date") else datetime.today().date()
                            )

                        edit_submit_button = st.form_submit_button("Salvar Alterações")
                        if edit_submit_button:
                            if edit_expense(
                                expense_data["_id"], 
                                new_name, 
                                new_amount, 
                                new_date, 
                                new_category, 
                                is_paid, 
                                payment_date
                            ):
                                st.success(f"Despesa '{new_name}' editada com sucesso!")
                            else:
                                st.error("Erro ao editar a despesa.")
        else:
            st.write(f"Nenhuma despesa registrada para {month}/{year}.")
    else:
        st.write("Nenhuma despesa registrada ainda.")

# Sidebar para navegação
st.sidebar.title("Menu")
page = st.sidebar.selectbox(
    "Selecione a página", 
    ["Despesas por Mês", "Resumo de Despesas", "Editar Despesas"]
)

# Mostrar a página de acordo com a seleção
if page == "Despesas por Mês":
    show_home_page()
elif page == "Resumo de Despesas":
    show_summary_page()
elif page == "Editar Despesas":
    show_edit_page()
