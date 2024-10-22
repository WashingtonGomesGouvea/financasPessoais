
# Personal Finances Dashboard

Este é um projeto de **controle financeiro pessoal da casa**, desenvolvido com **Streamlit** para visualização de despesas mensais, resumo de despesas e edição de registros. A aplicação conecta-se a um banco de dados **MongoDB** e exibe gráficos interativos utilizando a biblioteca **Plotly**.

## Funcionalidades

- **Visualização das despesas por mês**: Gráficos de barras que mostram o total de despesas em cada mês.
- **Resumo das despesas**: Filtros por mês e ano para visualização detalhada das despesas.
- **Gráficos interativos**: Utilização de gráficos de pizza e linha para visualização das despesas por categoria e por dia.
- **Edição de despesas**: Possibilidade de editar as despesas cadastradas.

## Requisitos

Para executar esta aplicação, você precisará ter os seguintes pacotes instalados:

- **Python 3.7+**
- **Bibliotecas Python** (listadas no arquivo `requirements.txt`)

### Dependências

O projeto depende das seguintes bibliotecas Python, que estão listadas no arquivo `requirements.txt`:

```
certifi==2024.2.2
pandas==2.2.3
plotly==5.24.1
pymongo==4.7.3
streamlit==1.39.0
toml==0.10.2
```

Para instalar todas as dependências, execute o seguinte comando no terminal:

```bash
pip install -r requirements.txt
```

## Configuração do MongoDB

Este projeto utiliza o MongoDB Atlas como banco de dados. Você deve fornecer sua URI de conexão no arquivo `secrets.toml` da seguinte forma:

### Estrutura do `secrets.toml`

Crie um arquivo chamado `secrets.toml` na pasta `.streamlit` do projeto com a seguinte estrutura:

```toml
MONGODB_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority"
```

Substitua `<username>`, `<password>`, `<cluster>`, e `<dbname>` pelas suas credenciais e informações de conexão com o MongoDB Atlas.

## Executando o Projeto

Após configurar o MongoDB e instalar as dependências, você pode executar a aplicação localmente utilizando o **Streamlit**. No terminal, navegue até a pasta do projeto e execute o seguinte comando:

```bash
streamlit run app.py
```

Isso iniciará a aplicação e abrirá uma janela do navegador com o dashboard de controle financeiro.

## Estrutura do Projeto

- `app.py`: Arquivo principal da aplicação que contém toda a lógica de conexão com o MongoDB e manipulação de dados, além da interface do usuário com o **Streamlit**.
- `requirements.txt`: Arquivo que lista todas as dependências necessárias para rodar a aplicação.
- `.streamlit/secrets.toml`: Arquivo que contém as credenciais para conexão com o banco de dados MongoDB. **Este arquivo deve ser criado manualmente e não deve ser incluído no controle de versão**.

## Como Contribuir

Contribuições são bem-vindas! Sinta-se à vontade para abrir um pull request ou reportar problemas na seção de issues.

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## Contato

Desenvolvido por **Washington Gomes**, atualmente Analista de Dados II. 

- Conecte-se comigo no [LinkedIn](https://www.linkedin.com/in/washington-gomes-7a4131b5/).
