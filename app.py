import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Controle Sacolão Queiroz", layout="wide", page_icon="🥬")
LIMITE_ESTOQUE_BAIXO = 5

if 'estoque' not in st.session_state:
    st.session_state.estoque = pd.DataFrame(columns=["codigo", "nome", "preco", "quantidade"])
if 'vendas' not in st.session_state:
    st.session_state.vendas = pd.DataFrame(columns=["data", "codigo", "nome", "quantidade", "valor_unitario", "valor_total"])

def salvar_csv():
    return st.session_state.estoque.to_csv(index=False).encode('utf-8')

def salvar_vendas_csv():
    return st.session_state.vendas.to_csv(index=False).encode('utf-8')

def gerar_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elementos = []
    styles = getSampleStyleSheet()
    titulo = Paragraph(f"Relatório de Vendas - Sacolão Queiroz", styles['Title'])
    data_geracao = Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    elementos.extend([titulo, data_geracao, Spacer(1, 12)])
    dados_tabela = [["Data", "Código", "Produto", "Qtd", "V.Unit", "Total"]]
    total_geral = 0
    for _, v in st.session_state.vendas.iterrows():
        total_geral += v["valor_total"]
        dados_tabela.append([
            v["data"][:10], v["codigo"], v["nome"][:25], str(int(v["quantidade"])),
            f"R$ {v['valor_unitario']:.2f}".replace(".", ","), f"R$ {v['valor_total']:.2f}".replace(".", ",")
        ])
    dados_tabela.append(["", "", "", "", "TOTAL:", f"R$ {total_geral:.2f}".replace(".", ",")])
    tabela = Table(dados_tabela, colWidths=[60, 50, 150, 40, 60, 70])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

st.title("🥬 Controle de Estoque e Vendas - Sacolão Queiroz")
tab1, tab2, tab3, tab4 = st.tabs(["📦 Estoque", "💰 Vendas", "📊 Gráficos", "📄 Relatórios"])

with tab1:
    st.subheader("Cadastrar Produto")
    with st.form("cad_produto", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        codigo = col1.text_input("Código")
        nome = col2.text_input("Nome")
        preco = col3.number_input("Preço R$", min_value=0.0, format="%.2f")
        qtd = col4.number_input("Quantidade", min_value=0, step=1)
        if st.form_submit_button("Cadastrar"):
            if codigo and nome:
                if codigo in st.session_state.estoque["codigo"].values:
                    st.error("❌ Já existe produto com esse código.")
                else:
                    novo = pd.DataFrame([{"codigo": codigo, "nome": nome, "preco": preco, "quantidade": qtd}])
                    st.session_state.estoque = pd.concat([st.session_state.estoque, novo], ignore_index=True)
                    st.success(f"✅ Produto '{nome}' cadastrado!")
            else:
                st.error("Preencha código e nome.")
    st.subheader("Estoque Atual")
    df_estoque = st.session_state.estoque.copy()
    if not df_estoque.empty:
        df_estoque["status"] = df_estoque["quantidade"].apply(lambda x: "⚠️ BAIXO" if x < LIMITE_ESTOQUE_BAIXO else "OK")
        st.dataframe(df_estoque, use_container_width=True)
    else:
        st.info("Estoque vazio.")
    st.download_button("⬇️ Baixar estoque.csv", salvar_csv(), "estoque.csv", "text/csv")

with tab2:
    st.subheader("Registrar Venda")
    if st.session_state.estoque.empty:
        st.warning("Cadastre produtos primeiro.")
    else:
        with st.form("venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            codigo_venda = col1.selectbox("Produto", st.session_state.estoque["codigo"].values)
            qtd_venda = col2.number_input("Quantidade vendida", min_value=1, step=1)
            if st.form_submit_button("Registrar Venda"):
                idx = st.session_state.estoque.index[st.session_state.estoque["codigo"] == codigo_venda][0]
                produto = st.session_state.estoque.loc[idx]
                if qtd_venda > produto["quantidade"]:
                    st.error(f"❌ Só tem {int(produto['quantidade'])} unidades em estoque.")
                else:
                    st.session_state.estoque.at[idx, "quantidade"] -= qtd_venda
                    valor_total = qtd_venda * produto["preco"]
                    nova_venda = pd.DataFrame([{
                        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "codigo": produto["codigo"],
                        "nome": produto["nome"], "quantidade": qtd_venda, "valor_unitario": produto["preco"],
                        "valor_total": valor_total
                    }])
                    st.session_state.vendas = pd.concat([st.session_state.vendas, nova_venda], ignore_index=True)
                    st.success(f"✅ Venda registrada! Total: R$ {valor_total:.2f}")
                    if st.session_state.estoque.at[idx, "quantidade"] < LIMITE_ESTOQUE_BAIXO:
                        st.warning(f"⚠️ ATENÇÃO: Estoque baixo para {produto['nome']}!")
    st.subheader("Últimas Vendas")
    if not st.session_state.vendas.empty:
        st.dataframe(st.session_state.vendas.tail(10), use_container_width=True)
    else:
        st.info("Nenhuma venda registrada.")

with tab3:
    st.subheader("Faturamento Mensal")
    if st.session_state.vendas.empty:
        st.info("Sem vendas para gerar gráfico.")
    else:
        col1, col2, col3 = st.columns(3)
        ano = col1.number_input("Ano", value=datetime.now().year, step=1)
        mes_ini = col2.number_input("Mês inicial", min_value=1, max_value=12, value=1)
        mes_fim = col3.number_input("Mês final", min_value=1, max_value=12, value=12)
        vendas_filtradas = st.session_state.vendas.copy()
        vendas_filtradas["data"] = pd.to_datetime(vendas_filtradas["data"])
        vendas_filtradas = vendas_filtradas[(vendas_filtradas["data"].dt.year == ano) & (vendas_filtradas["data"].dt.month >= mes_ini) & (vendas_filtradas["data"].dt.month <= mes_fim)]
        if vendas_filtradas.empty:
            st.info("Nenhuma venda no período.")
        else:
            fat_mensal = vendas_filtradas.groupby(vendas_filtradas["data"].dt.month)["valor_total"].sum()
            meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            labels = [meses_nomes[m-1] for m in fat_mensal.index]
            fig, ax = plt.subplots()
            ax.bar(labels, fat_mensal.values, color="#2E8B57")
            ax.set_title(f"Faturamento {mes_ini}/{ano} a {mes_fim}/{ano}")
            ax.set_ylabel("Faturamento (R$)")
            st.pyplot(fig)
    st.subheader("Top 10 Produtos Mais Vendidos")
    if st.session_state.vendas.empty:
        st.info("Sem vendas para gerar ranking.")
    else:
        tipo = st.radio("Ver por:", ["Quantidade", "Faturamento"], horizontal=True)
        if tipo == "Quantidade":
            ranking = st.session_state.vendas.groupby("nome")["quantidade"].sum().nlargest(10)
            titulo = "Por Quantidade"
        else:
            ranking = st.session_state.vendas.groupby("nome")["valor_total"].sum().nlargest(10)
            titulo = "Por Faturamento (R$)"
        fig, ax = plt.subplots()
        ax.barh(ranking.index, ranking.values, color="#FF8C00")
        ax.set_title(f"Top 10 - {titulo}")
        ax.invert_yaxis()
        st.pyplot(fig)

with tab4:
    st.subheader("Exportar Dados")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇️ Baixar vendas.csv", salvar_vendas_csv(), "vendas.csv", "text/csv")
    with col2:
        if not st.session_state.vendas.empty:
            st.download_button("⬇️ Baixar Relatório PDF", gerar_pdf(), "relatorio_vendas.pdf", "application/pdf")
    st.subheader("Importar Dados")
    st.warning("Importante: No Streamlit os dados somem quando o app reinicia. Sempre baixe os CSV no final do dia e importe no dia seguinte.")
    arquivo_estoque = st.file_uploader("Importar estoque.csv", type="csv")
    if arquivo_estoque:
        st.session_state.estoque = pd.read_csv(arquivo_estoque)
        st.success("Estoque importado!")
    arquivo_vendas = st.file_uploader("Importar vendas.csv", type="csv")
    if arquivo_vendas:
        st.session_state.vendas = pd.read_csv(arquivo_vendas)
        st.success("Vendas importadas!")
