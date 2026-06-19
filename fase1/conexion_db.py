from sqlalchemy import create_engine, text

# Cadena de conexión: postgresql://usuario:password@host:puerto/basededatos
DATABASE_URL = "postgresql://dataeng:dataeng123@localhost:5432/PIPELINE_DB"

engine = create_engine(DATABASE_URL)

# Prueba simple: ejecutar una consulta básica
with engine.connect() as conn:
    resultado = conn.execute(text("SELECT version ();"))
    print(resultado.fetchone())