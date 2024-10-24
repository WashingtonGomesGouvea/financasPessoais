import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import certifi
import base64
import numpy as np

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
    print("Conexão com o MongoDB estabelecida com sucesso!!")
except Exception as e:
    print(f"Erro de conexão com o MongoDB: {e}")
    

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

# Função para adicionar uma nova despesa com o campo Observações e anexos
def add_expense(name, amount, date, category, notes, attachment=None):
    try:
        # Tratamento direto para remover emojis e caracteres especiais do campo categoria
        category = category.replace('💧 ', '').replace('⚡ ', '').replace('🏠 ', '').replace('🌐 ', '') \
                           .replace('🍔 ', '').replace('🚌 ', '').replace('🏥 ', '').replace('📚 ', '') \
                           .replace('🎉 ', '').replace('👗 ', '').replace('💼 ', '').replace('🏖️ ', '')

        new_expense = {
            "name": name,
            "amount": amount,
            "date": convert_to_datetime(date),
            "category": category,  # Categoria sem emojis
            "notes": notes,  # Observações podem conter emojis
            "is_paid": False,
            "payment_date": None
        }

        # Processar o arquivo de anexo
        if attachment is not None:
            new_expense["attachment_name"] = attachment.name
            new_expense["attachment_type"] = attachment.type
            new_expense["attachment_data"] = attachment.getvalue()  # Armazena o arquivo como binário

        expenses_collection.insert_one(new_expense)
        return True
    except Exception as e:
        st.error(f"Erro ao adicionar despesa: {e}")
        return False

# Função para editar uma despesa existente, incluindo o campo Observações e anexos
def edit_expense(expense_id, name, amount, date, category, is_paid, payment_date, notes, attachment=None):
    try:
        # Tratamento direto para remover emojis e caracteres especiais do campo categoria
        category = category.replace('💧 ', '').replace('⚡ ', '').replace('🏠 ', '').replace('🌐 ', '')

        update_fields = {
            "name": name,
            "amount": amount,
            "date": convert_to_datetime(date),
            "category": category,  # Categoria sem emojis
            "is_paid": is_paid,
            "notes": notes  # Observações podem conter emojis
        }

        if is_paid:
            update_fields["payment_date"] = convert_to_datetime(payment_date)
        else:
            update_fields["payment_date"] = None

        # Processar o arquivo de anexo
        if attachment is not None:
            update_fields["attachment_name"] = attachment.name
            update_fields["attachment_type"] = attachment.type
            update_fields["attachment_data"] = attachment.getvalue()  # Armazena o arquivo como binário

        expenses_collection.update_one({"_id": expense_id}, {"$set": update_fields})
        return True
    except Exception as e:
        st.error(f"Erro ao editar a despesa: {e}")
        return False



# Função para listar todas as despesas
def get_all_expenses():
    return list(expenses_collection.find().sort("date", -1))

# Página principal - Despesas por Mês com Formulário de Adição
def show_home_page():
    st.title("Despesas por Ano e Mês")

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
        
        # Adicionando novas opções de categorias com emojis
        category = st.selectbox(
            "Categoria", 
            ["💧 Água", "⚡ Energia", "🏠 Aluguel", "🌐 Internet", "🍔 Alimentação", "🚌 Transporte", 
             "🏥 Saúde", "📚 Educação", "🎉 Lazer", "👗 Roupas", "💼 Trabalho", "🏖️ Viagem", "Outros"], 
            key='category_display'
        )
        notes = st.text_area("Observações", key='notes')  # Campo de texto para observações

        # Campo para anexar arquivos (imagem ou PDF)
        attachment = st.file_uploader("Anexar Imagem ou PDF", type=["pdf", "png", "jpg", "jpeg"])

        submit_button = st.form_submit_button("Adicionar")

        # Validação do formulário antes de salvar
        if submit_button:
            if not name:
                st.error("O campo de descrição é obrigatório.")
            elif amount <= 0:
                st.error("O valor deve ser maior que zero.")
            else:
                # Chamada da função add_expense para salvar no MongoDB
                if add_expense(name, amount, date_input, category, notes, attachment):
                    st.success(f"Despesa adicionada com sucesso: {name} - R$ {amount}")
                else:
                    st.error("Erro ao adicionar a despesa.")
                    
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

        # Adicionando a coluna 'Observações' com valor padrão caso não exista
        if 'notes' not in df.columns:
            df['notes'] = ""  # Se a coluna 'notes' não existir, adicionar com valores vazios

        df.rename(columns={
            "name": "Descrição", 
            "amount": "Valor (R$)", 
            "category": "Categoria", 
            "date": "Data", 
            "is_paid": "Paga", 
            "payment_date": "Data de Pagamento",
            "notes": "Observações"  # Incluindo Observações na tabela
        }, inplace=True)

        # Filtrando as despesas com base no mês e ano selecionados
        df['Mês'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.month
        df['Ano'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.year
        filtered_df = df[(df['Mês'] == month) & (df['Ano'] == year)]
        filtered_df['Valor (R$)'] = filtered_df['Valor (R$)'].apply(lambda x: float(str(x).replace(',', '.')))
        total_expenses = filtered_df['Valor (R$)'].sum()

        # Exibindo todas as colunas, incluindo o novo campo 'Observações'
        st.dataframe(filtered_df[['Descrição', 'Valor (R$)', 'Categoria', 'Data', 'Paga', 'Data de Pagamento', 'Observações']])
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
            "payment_date": "Data de Pagamento",
            "notes": "Observações"  # Incluindo Observações na tabela de edição
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
                        notes = st.text_area("Observações", value=expense_data.get("notes", ""))  # Campo para editar as observações

                        # Campo para anexar arquivos (imagem ou PDF)
                        attachment = st.file_uploader("Anexar Imagem ou PDF", type=["pdf", "png", "jpg", "jpeg"])

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
                                payment_date, 
                                notes,  # Incluindo Observações na atualização
                                attachment  # Incluindo anexos na atualização
                            ):
                                st.success(f"Despesa '{new_name}' editada com sucesso!")
                            else:
                                st.error("Erro ao editar a despesa.")
        else:
            st.write(f"Nenhuma despesa registrada para {month}/{year}.")
    else:
        st.write("Nenhuma despesa registrada ainda.")

# Função para apagar despesas selecionadas
def delete_selected_expenses(selected_ids):
    try:
        # Apagar as despesas que correspondem aos IDs selecionados
        result = expenses_collection.delete_many({"_id": {"$in": selected_ids}})
        return result.deleted_count
    except Exception as e:
        st.error(f"Erro ao apagar as despesas: {e}")
        return 0

# Página de exclusão de despesas
def show_delete_page():
    st.title("Apagar Despesas")

    # Filtro por mês e ano
    st.subheader("Filtrar por Mês e Ano para Apagar")
    month = st.selectbox("Mês", list(range(1, 13)), index=datetime.today().month - 1, key='delete_month')
    year = st.number_input("Ano", min_value=2000, max_value=2100, value=datetime.today().year, key='delete_year')

    # Buscar despesas filtradas por mês e ano
    st.subheader("Selecione as Despesas a serem Apagadas")
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

        if not filtered_df.empty:
            # Armazenar IDs das despesas selecionadas
            selected_expenses = []
            for index, row in filtered_df.iterrows():
                expense_id = expenses[index]["_id"]  # Obter o ID da despesa original
                if st.checkbox(f"{row['Descrição']} - R$ {row['Valor (R$)']} - {row['Data']} ({row['Categoria']})", key=expense_id):
                    selected_expenses.append(expense_id)

            # Botão para apagar despesas selecionadas
            if selected_expenses:
                delete_button = st.button("Apagar Despesas Selecionadas")
                if delete_button:
                    deleted_count = delete_selected_expenses(selected_expenses)
                    if deleted_count > 0:
                        st.success(f"{deleted_count} despesas apagadas com sucesso.")
                    else:
                        st.warning("Nenhuma despesa foi apagada.")
            else:
                st.warning("Nenhuma despesa selecionada para apagar.")
        else:
            st.write(f"Nenhuma despesa registrada para {month}/{year}.")
    else:
        st.write("Nenhuma despesa registrada ainda.")

# Função para análise inteligente anual com gráficos mais claros e aluguel incluso, exceto nas dicas e na categoria mais cara

def show_analysis_page():
    st.title("Análise Inteligente dos Gastos Anuais")

    # Filtro por ano
    st.subheader("Selecione o Ano para Análise")
    year = st.number_input("Ano", min_value=2000, max_value=2100, value=datetime.today().year)

    # Buscar todas as despesas filtradas pelo ano
    expenses = get_all_expenses()

    if expenses:
        df = pd.DataFrame(expenses)
        df['date'] = pd.to_datetime(df['date'], dayfirst=True).dt.strftime('%d/%m/%Y')  # Formato brasileiro DD/MM/AAAA
        df['Mês'] = pd.to_datetime(df['date'], format='%d/%m/%Y', dayfirst=True).dt.month
        df['Ano'] = pd.to_datetime(df['date'], format='%d/%m/%Y', dayfirst=True).dt.year

        # Filtrando as despesas pelo ano selecionado
        filtered_df = df[df['Ano'] == year]

        # 1. Gráfico de comparação mensal (Inclui o Aluguel)
        st.subheader(f"Comparação de Gastos Mensais em {year}")
        monthly_expenses_incl_rent = filtered_df.groupby('Mês')['amount'].sum()

        # Gráfico de barras + tendência
        fig = px.bar(monthly_expenses_incl_rent, labels={'x': 'Mês', 'y': 'Total (R$)'}, title="Gastos Mensais com Aluguel")
        fig.add_scatter(x=monthly_expenses_incl_rent.index, y=monthly_expenses_incl_rent, mode='lines+markers', name='Tendência')
        st.plotly_chart(fig)

        # Adicionando a Média Mensal
        monthly_average = monthly_expenses_incl_rent.mean()
        st.write(f"**Média mensal de gastos:** R$ {monthly_average:.2f}".replace('.', ',').replace(',', '.', 1))

        # 2. Gráfico de variação percentual de cada mês (Inclui o Aluguel)
        monthly_expenses_pct_change = monthly_expenses_incl_rent.pct_change().fillna(0) * 100
        st.subheader("Variação Percentual de Gastos")

        # Explicação sobre a variação percentual
        st.write("""
        A **Variação Percentual Mensal** indica o quanto os gastos mudaram de um mês para o outro. Valores positivos indicam que as despesas aumentaram em relação ao mês anterior, enquanto valores negativos indicam uma redução nos gastos.
        """)

        # Ajustando os labels no gráfico
        fig_pct = px.bar(monthly_expenses_pct_change, labels={'x': 'Mês', 'y': 'Variação (%)'}, 
                         title="Variação Percentual Mensal", text=monthly_expenses_pct_change.map("{:.2f}%".format), 
                         color=monthly_expenses_pct_change, color_continuous_scale="RdYlGn")
        
        fig_pct.update_layout(xaxis=dict(tickvals=monthly_expenses_incl_rent.index, ticktext=monthly_expenses_incl_rent.index), 
                              yaxis_title="Variação (%)", xaxis_title="Mês")
        st.plotly_chart(fig_pct)

        # 3. Gráfico de despesas por categoria ao longo do ano (Inclui Aluguel)
        st.subheader(f"Gastos por Categoria em {year}")
        category_expenses_incl_rent = filtered_df.groupby('category')['amount'].sum().sort_values(ascending=False)

        # Gráfico de pizza para destacar as categorias mais caras
        fig_category = px.pie(category_expenses_incl_rent, values='amount', names=category_expenses_incl_rent.index, 
                              title="Distribuição de Gastos por Categoria", hole=0.4)
        st.plotly_chart(fig_category)

        # Destacar a categoria com maior gasto
        st.write(f"**Categoria com maior gasto:** {category_expenses_incl_rent.idxmax()}")

        # 4. Categoria mais cara no ano (Sem Aluguel)
        st.subheader(f"Categoria mais cara no ano de {year}")
        filtered_df_no_rent = filtered_df[filtered_df['category'] != "Aluguel"]
        most_expensive_category_no_rent = filtered_df_no_rent.groupby('category')['amount'].sum().idxmax()
        highest_expense_no_rent = filtered_df_no_rent.groupby('category')['amount'].sum().max()

        st.write(f"**Categoria mais cara no ano:** {most_expensive_category_no_rent} - Total Gasto: R$ {highest_expense_no_rent:,.2f}".replace('.', ',').replace(',', '.', 1))

        # Dicas de economia baseadas na categoria mais cara, excluindo o aluguel
        st.subheader("Dicas para Economia")
        if most_expensive_category_no_rent == "Energia":
            st.write("⚡ **Dica:** Para reduzir o consumo de energia, tente desligar dispositivos quando não estiverem em uso ou investir em aparelhos mais eficientes.")
        elif most_expensive_category_no_rent == "Água":
            st.write("💧 **Dica:** Considere o uso de redutores de fluxo em torneiras e chuveiros para economizar água.")
        elif most_expensive_category_no_rent == "Internet":
            st.write("🌐 **Dica:** Verifique se está pagando por uma velocidade de internet que realmente precisa. Em alguns casos, planos mais baratos podem atender suas necessidades.")

        # 5. Gráfico de picos de gastos diários com categorias e cores diferenciadas (Sem Aluguel)
        st.subheader(f"Picos de Gastos Diários em {year}")

        # Criar coluna para o eixo X (dia e mês) e excluir aluguel
        filtered_df_no_rent['Dia_Mês'] = pd.to_datetime(filtered_df_no_rent['date'], format='%d/%m/%Y').dt.strftime('%d/%m')

        # Agrupando despesas por dia/mês e categoria (sem aluguel)
        daily_expenses_no_rent = filtered_df_no_rent.groupby(['Dia_Mês', 'category'])['amount'].sum().unstack().fillna(0)

        # Gráfico de barras empilhadas com Plotly para identificar picos diários por categoria
        fig_daily = px.bar(daily_expenses_no_rent.reset_index(), 
                           x='Dia_Mês', 
                           y=daily_expenses_no_rent.columns, 
                           labels={'value': 'Total (R$)', 'Dia_Mês': 'Dia/Mês'},
                           title="Picos de Gastos Diários por Categoria",
                           barmode='stack')

        fig_daily.update_layout(xaxis_title='Dia e Mês', yaxis_title='Total Gasto (R$)')
        st.plotly_chart(fig_daily)

        # Analisando possíveis picos anormais
        avg_expense = np.mean(daily_expenses_no_rent.sum(axis=1))
        max_expense = np.max(daily_expenses_no_rent.sum(axis=1))
        if max_expense > 1.5 * avg_expense:  # Se o maior gasto for 50% maior que a média
            st.write(f"⚠️ **Alerta:** Houve um pico de gastos no dia com maior despesa. O valor foi R$ {max_expense:,.2f}, bem acima da média diária de R$ {avg_expense:,.2f}. Verifique as despesas deste dia.")

        # Nova funcionalidade: Previsão de Gastos para o Próximo Mês com base na média móvel
        st.subheader("Previsão de Gastos para o Próximo Mês")
        if len(monthly_expenses_incl_rent) >= 3:  # Verifica se há dados suficientes para calcular a média móvel
            # Calculando a média dos últimos 3 meses
            last_three_months_avg = monthly_expenses_incl_rent.iloc[-3:].mean()

            # Calculando a variação percentual média dos últimos 3 meses
            pct_change_last_three = monthly_expenses_pct_change.iloc[-3:].mean() / 100

            # Previsão do próximo mês com base na média móvel e variação percentual média
            predicted_next_month = last_three_months_avg * (1 + pct_change_last_three)
            st.write(f"**Previsão de gastos para o próximo mês:** R$ {predicted_next_month:.2f}".replace('.', ',').replace(',', '.', 1))
        else:
            st.write("Dados insuficientes para prever o próximo mês.")
        
    else:
        st.write(f"Nenhuma despesa registrada para o ano de {year}.")

     

# Função para exibir visualização de anexos de forma otimizada com download correto
def show_view_files_page():
    st.title("Visualizar Anexos das Despesas")

    # Filtro por mês e ano
    st.subheader("Filtrar por Mês e Ano para Visualização de Anexos")
    month = st.selectbox("Mês", list(range(1, 13)), index=datetime.today().month - 1)
    year = st.number_input("Ano", min_value=2000, max_value=2100, value=datetime.today().year)

    # Buscar despesas filtradas por mês e ano
    st.subheader("Despesas com Anexos")
    expenses = get_all_expenses()

    if expenses:
        df = pd.DataFrame(expenses)
        # Definir `dayfirst=True` explicitamente ao formatar datas
        df['date'] = pd.to_datetime(df['date'], dayfirst=True).dt.strftime('%d/%m/%Y')  # Formato brasileiro DD/MM/AAAA

        # Filtrar despesas por mês e ano
        df['Mês'] = pd.to_datetime(df['date'], format='%d/%m/%Y', dayfirst=True).dt.month
        df['Ano'] = pd.to_datetime(df['date'], format='%d/%m/%Y', dayfirst=True).dt.year
        filtered_df = df[(df['Mês'] == month) & (df['Ano'] == year)]

        if not filtered_df.empty:
            for index, row in filtered_df.iterrows():
                st.write(f"### Despesa: {row['name']} - R$ {row['amount']} - {row['date']}")
                st.write(f"**Categoria:** {row['category']}")
                st.write(f"**Observações:** {row.get('notes', 'Sem observações')}")

                # Se houver um anexo, exibi-lo de forma otimizada
                if 'attachment_data' in row and row['attachment_data']:
                    attachment_name = row.get('attachment_name', 'Anexo')
                    attachment_type = row.get('attachment_type', '')

                    # Garantir que attachment_type seja uma string antes de fazer a comparação
                    if isinstance(attachment_type, str):
                        # Exibir imagem como miniatura clicável
                        if 'image' in attachment_type:
                            st.image(row['attachment_data'], caption=attachment_name, width=150)  # Exibindo a imagem em miniatura
                            if st.button(f"Expandir Imagem {attachment_name}", key=f"expand_{index}"):
                                st.image(row['attachment_data'], caption=attachment_name)  # Exibir imagem em tamanho real

                        # Forçar o download do PDF
                        elif 'pdf' in attachment_type:
                            # Codificar o PDF em base64 para download
                            base64_pdf = base64.b64encode(row['attachment_data']).decode('utf-8')
                            href = f'<a href="data:application/octet-stream;base64,{base64_pdf}" download="{attachment_name}">Baixar PDF: {attachment_name}</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.write(f"Tipo de anexo inválido ou ausente para a despesa: {row['name']}")
                else:
                    st.write("Nenhum anexo disponível para esta despesa.")
        else:
            st.write(f"Nenhuma despesa encontrada para {month}/{year}.")
    else:
        st.write("Nenhuma despesa registrada ainda.")

# Sidebar para navegação
st.sidebar.title("Menu")
page = st.sidebar.selectbox(
    "Selecione a página", 
    ["Despesas por Mês", "Resumo de Despesas", "Análise Inteligente", "Editar Despesas", "Apagar Despesas", "Visualizar Anexos"]
)

# Mostrar a página de acordo com a seleção
if page == "Despesas por Mês":
    show_home_page()
elif page == "Resumo de Despesas":
    show_summary_page()
elif page == "Análise Inteligente":
    show_analysis_page()
elif page == "Editar Despesas":
    show_edit_page()
elif page == "Apagar Despesas":
    show_delete_page()
elif page == "Visualizar Anexos":
    show_view_files_page()
