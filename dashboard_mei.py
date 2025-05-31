import streamlit as st
import pandas as pd
import pygsheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from datetime import datetime
import matplotlib.pyplot as plt

# Autenticação com Google Sheets e Google Drive
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
gc = pygsheets.authorize(service_file='service_account.json')
drive_service = build('drive', 'v3', credentials=creds)
gs_client = gspread.authorize(creds)

PASTA_ID = '1XNfLWag3PG_Pf1JqIi0xtIDlz1MUN4q9'

# Função para criar nova planilha do cliente
def criar_planilha_cliente(nome_cliente):
    try:
        planilha = gc.create(nome_cliente)
        drive_service.files().update(fileId=planilha.id, addParents=PASTA_ID, removeParents='root').execute()

        abas = ['Clientes e Fornecedores', 'Metas do Ano', 'Receitas', 'Despesas']
        for aba in abas:
            planilha.add_worksheet(aba)

        planilha.del_worksheet(planilha.worksheet_by_title('Sheet1'))
        return planilha
    except Exception as e:
        st.error(f"Erro ao criar planilha: {e}")
        st.stop()

# Função para carregar planilha existente ou criar nova
def carregar_planilha_cliente(nome_cliente):
    try:
        response = drive_service.files().list(
            q=f"'{PASTA_ID}' in parents and name = '{nome_cliente}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed = false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        arquivos = response.get('files', [])

        if arquivos:
            planilha_id = arquivos[0]['id']
            return gc.open_by_key(planilha_id)
        else:
            return criar_planilha_cliente(nome_cliente)
    except Exception as e:
        st.error(f"Erro ao carregar ou criar a planilha: {e}")
        st.stop()

# Tela inicial para cadastro do cliente
def tela_cadastro():
    st.title("Dashboard Financeiro - Cadastro")
    nome = st.text_input("Digite o nome da sua empresa ou seu nome completo")

    if st.button("Entrar"):
        if nome:
            planilha = carregar_planilha_cliente(nome)
            st.session_state.planilha = planilha
            st.session_state.nome_cliente = nome
            st.query_params["cliente"] = nome
            st.rerun()
        else:
            st.warning("Por favor, preencha o campo antes de continuar.")

# Carregamento das abas e interface principal
def interface_principal():
    st.sidebar.title("Menu")
    opcao = st.sidebar.radio("Ir para:", ["Clientes e Fornecedores", "Metas do Ano", "Balanço Geral"])

    planilha = st.session_state.planilha

    if opcao == "Clientes e Fornecedores":
        aba = planilha.worksheet_by_title("Clientes e Fornecedores")
        st.subheader("Cadastro de Clientes e Fornecedores")
        nome = st.text_input("Nome")
        tipo = st.selectbox("Tipo", ["Cliente", "Fornecedor"])
        contato = st.text_input("Contato")

        if st.button("Salvar Cadastro"):
            df = aba.get_as_df(has_header=True, default_blank="")
            novo = pd.DataFrame([[nome, tipo, contato]], columns=['Nome', 'Tipo', 'Contato'])
            df = pd.concat([df, novo], ignore_index=True)
            aba.set_dataframe(df, (1,1))
            st.success("Cadastro salvo com sucesso!")

        df = aba.get_as_df(has_header=True, default_blank="")
        if not df.empty:
            st.dataframe(df)
            nome_excluir = st.selectbox("Selecione um cadastro para excluir:", df['Nome'])
            if st.button("Excluir Cadastro"):
                df = df[df['Nome'] != nome_excluir]
                aba.set_dataframe(df, (1,1))
                st.success("Cadastro excluído!")

    elif opcao == "Metas do Ano":
        aba = planilha.worksheet_by_title("Metas do Ano")
        st.subheader("Metas do Ano")
        meta_receita = st.number_input("Meta de Receita", min_value=0.0, format="%.2f")
        meta_despesa = st.number_input("Meta de Despesa", min_value=0.0, format="%.2f")
        data_meta = st.date_input("Data da Meta")

        if st.button("Salvar Metas"):
            df = aba.get_as_df(has_header=True, default_blank="")
            novo = pd.DataFrame([[meta_receita, meta_despesa, str(data_meta)]], columns=['Meta Receita', 'Meta Despesa', 'Data'])
            df = pd.concat([df, novo], ignore_index=True)
            aba.set_dataframe(df, (1,1))
            st.success("Metas salvas com sucesso!")

        df = aba.get_as_df(has_header=True, default_blank="")
        if not df.empty:
            st.dataframe(df)
            data_excluir = st.selectbox("Selecione a data da meta para excluir:", df['Data'])
            if st.button("Excluir Meta"):
                df = df[df['Data'] != data_excluir]
                aba.set_dataframe(df, (1,1))
                st.success("Meta excluída!")

    elif opcao == "Balanço Geral":
        aba_receitas = planilha.worksheet_by_title("Receitas")
        aba_despesas = planilha.worksheet_by_title("Despesas")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Receita")
            valor_receita = st.number_input("Valor Receita", min_value=0.0, format="%.2f", key="vr")
            data_receita = st.date_input("Data Receita", key="dr")
            descricao_receita = st.text_input("Descrição Receita", key="desc_r")
            if st.button("Salvar Receita"):
                df = aba_receitas.get_as_df(has_header=True, default_blank="")
                novo = pd.DataFrame([[valor_receita, str(data_receita), descricao_receita]], columns=['Valor', 'Data', 'Descrição'])
                df = pd.concat([df, novo], ignore_index=True)
                aba_receitas.set_dataframe(df, (1,1))
                st.success("Receita salva com sucesso!")

        with col2:
            st.subheader("Despesa")
            valor_despesa = st.number_input("Valor Despesa", min_value=0.0, format="%.2f", key="vd")
            data_despesa = st.date_input("Data Despesa", key="dd")
            descricao_despesa = st.text_input("Descrição Despesa", key="desc_d")
            if st.button("Salvar Despesa"):
                df = aba_despesas.get_as_df(has_header=True, default_blank="")
                novo = pd.DataFrame([[valor_despesa, str(data_despesa), descricao_despesa]], columns=['Valor', 'Data', 'Descrição'])
                df = pd.concat([df, novo], ignore_index=True)
                aba_despesas.set_dataframe(df, (1,1))
                st.success("Despesa salva com sucesso!")

        df_r = aba_receitas.get_as_df(has_header=True, default_blank="")
        df_d = aba_despesas.get_as_df(has_header=True, default_blank="")

        total_r = df_r['Valor'].astype(float).sum() if 'Valor' in df_r.columns else 0.0
        total_d = df_d['Valor'].astype(float).sum() if 'Valor' in df_d.columns else 0.0
        saldo = total_r - total_d

        st.metric("Total de Receitas Lançadas", f"R$ {total_r:.2f}")
        st.metric("Total de Despesas Lançadas", f"R$ {total_d:.2f}")
        st.metric("Saldo", f"R$ {saldo:.2f}")

        st.subheader("Evolução Financeira")
        try:
            if 'Data' in df_r.columns and 'Data' in df_d.columns:
                df_r['Data'] = pd.to_datetime(df_r['Data'], errors='coerce')
                df_d['Data'] = pd.to_datetime(df_d['Data'], errors='coerce')

                df_r_grouped = df_r.groupby('Data')['Valor'].sum()
                df_d_grouped = df_d.groupby('Data')['Valor'].sum()

                fig, ax = plt.subplots()
                df_r_grouped.plot(kind='bar', color='green', label='Receitas', ax=ax)
                df_d_grouped.plot(kind='bar', color='red', alpha=0.7, label='Despesas', ax=ax)
                plt.legend()
                plt.xlabel("Data")
                plt.ylabel("Valor (R$)")
                st.pyplot(fig)
            else:
                st.warning("Coluna 'Data' não encontrada nas planilhas de receitas ou despesas.")
        except Exception as e:
            st.warning("Não foi possível gerar o gráfico: " + str(e))

        if not df_r.empty and 'Descrição' in df_r.columns:
            desc_excluir_r = st.selectbox("Excluir Receita:", df_r['Descrição'], key="ex_r")
            if st.button("Excluir Receita"):
                df_r = df_r[df_r['Descrição'] != desc_excluir_r]
                aba_receitas.set_dataframe(df_r, (1,1))
                st.success("Receita excluída.")

        if not df_d.empty and 'Descrição' in df_d.columns:
            desc_excluir_d = st.selectbox("Excluir Despesa:", df_d['Descrição'], key="ex_d")
            if st.button("Excluir Despesa"):
                df_d = df_d[df_d['Descrição'] != desc_excluir_d]
                aba_despesas.set_dataframe(df_d, (1,1))
                st.success("Despesa excluída.")

# Execução principal
params = st.query_params
cliente_param = params.get("cliente")

if "planilha" in st.session_state and "nome_cliente" in st.session_state:
    interface_principal()
elif cliente_param:
    nome = cliente_param
    planilha = carregar_planilha_cliente(nome)
    st.session_state.planilha = planilha
    st.session_state.nome_cliente = nome
    interface_principal()
else:
    tela_cadastro()
