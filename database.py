from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData

DATABASE_URL = "sqlite:///finance.db"

engine = create_engine(DATABASE_URL, echo=False)
metadata = MetaData()

despesas = Table(
    "despesas", metadata,
    Column("id", Integer, primary_key=True),
    Column("mes", Integer),
    Column("ano", Integer),
    Column("categoria", String),
    Column("descricao", String),
    Column("valor", Float)
)

investimentos = Table(
    "investimentos", metadata,
    Column("id", Integer, primary_key=True),
    Column("mes", Integer),
    Column("ano", Integer),
    Column("tipo", String),
    Column("valor", Float)
)

config = Table(
    "config", metadata,
    Column("id", Integer, primary_key=True),
    Column("salario", Float),
    Column("meta", Float)
)

metadata.create_all(engine)
