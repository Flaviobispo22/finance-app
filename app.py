import streamlit as st


with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


import pandas as pd
from sqlalchemy import text
from database import engine
from datetime import datetime, date
import io
from fpdf import FPDF
import tempfile

# ======================
# CONFIG STREAMLIT
# ======================
st.set_page_config(page_title="Finance App", layout="wide")
st.title(" Dashboard Financeiro")

# ======================
# FILTRO MÊS / ANO
# ======================
col1, col2 = st.columns(2)
mes = col1.selectbox("Mês", list(range(1, 13)), index=datetime.today().month - 1)
ano = col2.selectbox("Ano", [2024, 2025, 2026], index=1)

# ======================
# CONFIGURAÇÕES GERAIS
# ======================
with engine.begin() as conn:
    config = conn.execute(text("SELECT salario, meta FROM config LIMIT 1")).fetchone()

if not config:
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO config (salario, meta) VALUES (0, 0)"))
    salario, meta = 0, 0
else:
    salario, meta = config

st.header("Configurações")

c1, c2 = st.columns(2)
salario = c1.number_input("Salário mensal (R$)", value=float(salario))
meta = c2.number_input("Meta financeira (R$)", value=float(meta))

with engine.begin() as conn:
    conn.execute(
        text("UPDATE config SET salario=:s, meta=:m"),
        {"s": salario, "m": meta}
    )

# ======================
# DESPESAS
# ======================
st.header(" Despesas")

with st.form("add_despesa"):
    data_despesa = st.date_input("Data", value=date.today())
    categoria = st.selectbox(
        "Categoria",
        ["Moradia", "Alimentação", "Transporte", "Lazer", "Educação", "Saúde", "Outros"]
    )
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor (R$)", min_value=0.0)
    submit = st.form_submit_button("Adicionar")

    if submit and descricao:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO despesas (data, mes, ano, categoria, descricao, valor)
                    VALUES (:d, :m, :a, :c, :ds, :v)
                """),
                {
                    "d": data_despesa,
                    "m": data_despesa.month,
                    "a": data_despesa.year,
                    "c": categoria,
                    "ds": descricao,
                    "v": valor
                }
            )
        st.rerun()

despesas = pd.read_sql(
    text("SELECT * FROM despesas WHERE mes=:m AND ano=:a"),
    engine,
    params={"m": mes, "a": ano}
)

if not despesas.empty:
    st.dataframe(despesas)

# ======================
# INVESTIMENTOS
# ======================
st.header(" Investimentos")

with st.form("add_invest"):
    data_inv = st.date_input("Data investimento", value=date.today(), key="inv_date")
    tipo = st.selectbox("Tipo", ["Renda Fixa", "Ações", "Fundos", "Cripto", "Outros"])
    valor_inv = st.number_input("Valor investido (R$)", min_value=0.0)
    submit = st.form_submit_button("Adicionar")

    if submit:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO investimentos (data, mes, ano, tipo, valor)
                    VALUES (:d, :m, :a, :t, :v)
                """),
                {
                    "d": data_inv,
                    "m": data_inv.month,
                    "a": data_inv.year,
                    "t": tipo,
                    "v": valor_inv
                }
            )
        st.rerun()

investimentos = pd.read_sql(
    text("SELECT * FROM investimentos WHERE mes=:m AND ano=:a"),
    engine,
    params={"m": mes, "a": ano}
)

if not investimentos.empty:
    st.dataframe(investimentos)

# ======================
# RESUMO
# ======================
total_despesas = despesas["valor"].sum() if not despesas.empty else 0
total_invest = investimentos["valor"].sum() if not investimentos.empty else 0
saldo = salario - total_despesas - total_invest

st.header("📊 Resumo")

c1, c2, c3 = st.columns(3)
c1.metric(" Despesas", f"R$ {total_despesas:.2f}")
c2.metric(" Investimentos", f"R$ {total_invest:.2f}")
c3.metric(" Saldo", f"R$ {saldo:.2f}")

# ======================
# META
# ======================
if meta > 0:
    progresso = total_invest / meta
    st.progress(min(progresso, 1.0))
    st.write(f" Faltam R$ {max(meta - total_invest, 0):.2f} para sua meta")

# ======================
# COMPARAÇÃO MENSAL
# ======================
st.header(" Este mês vs mês passado")

if mes == 1:
    mes_passado, ano_passado = 12, ano - 1
else:
    mes_passado, ano_passado = mes - 1, ano

desp_atual = total_despesas

desp_passado = pd.read_sql(
    text("SELECT SUM(valor) as total FROM despesas WHERE mes=:m AND ano=:a"),
    engine,
    params={"m": mes_passado, "a": ano_passado}
)["total"].iloc[0] or 0

comparacao = pd.DataFrame({
    "Mês": ["Mês passado", "Mês atual"],
    "Gastos (R$)": [desp_passado, desp_atual]
})

st.bar_chart(comparacao.set_index("Mês"))

# ======================
# ANÁLISES AUTOMÁTICAS
# ======================
st.header(" Análises automáticas")

if desp_passado > 0:
    variacao = ((desp_atual - desp_passado) / desp_passado) * 100

    if variacao > 0:
        st.warning(f" Seus gastos aumentaram {variacao:.1f}%")
    else:
        st.success(f" Você reduziu seus gastos em {abs(variacao):.1f}%")
else:
    st.info(" Não há dados suficientes para comparação.")

# ======================
# EXPORTAR EXCEL
# ======================
st.header(" Exportar dados")

if st.button(" Exportar para Excel"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        despesas.to_excel(writer, sheet_name="Despesas", index=False)
        investimentos.to_excel(writer, sheet_name="Investimentos", index=False)

    st.download_button(
        " Baixar Excel",
        data=output.getvalue(),
        file_name=f"financeiro_{mes}_{ano}.xlsx"
    )

# ======================
# EXPORTAR PDF
# ======================
if st.button(" Exportar para PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, f"Relatório Financeiro - {mes}/{ano}", ln=True)
    pdf.ln(5)

    pdf.cell(0, 8, f"Salário: R$ {salario:.2f}", ln=True)
    pdf.cell(0, 8, f"Despesas: R$ {total_despesas:.2f}", ln=True)
    pdf.cell(0, 8, f"Investimentos: R$ {total_invest:.2f}", ln=True)
    pdf.cell(0, 8, f"Saldo: R$ {saldo:.2f}", ln=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            st.download_button(
                " Baixar PDF",
                data=f,
                file_name=f"financeiro_{mes}_{ano}.pdf"
            )

