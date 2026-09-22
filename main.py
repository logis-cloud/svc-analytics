import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pyathena import connect
import pandas as pd

app = FastAPI(
    title="API Rest Consultas Analíticas - Logística y Envíos",
    description="Microservicio 5: Consultas sobre AWS Athena y Catálogo de Glue",
    version="1.0.0"
)

# Permitir CORS para que la Web en AWS Amplify pueda consumir la API libremente
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración leída desde Variables de Entorno
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_STAGING_DIR = os.getenv("S3_STAGING_DIR", "s3://tu-bucket-logistica/athena-results/")
DATABASE_GLUE = os.getenv("DATABASE_GLUE", "bd_logistica_glue")


def get_athena_connection():
    """
    Crea la conexión hacia AWS Athena.
    Usa la autenticación automática del LabRole asignado a la EC2.
    """
    return connect(
        s3_staging_dir=S3_STAGING_DIR,
        region_name=AWS_REGION,
        schema_name=DATABASE_GLUE
    )


@app.get("/", tags=["Health Check"])
def root():
    return {"message": "API Analítica de Logística y Envíos activa"}


@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}


# -------------------------------------------------------------
# Endpoints Analíticos (Consultas a Athena)
# -------------------------------------------------------------

@app.get("/analitica/envios-por-vehiculo", tags=["Consultas Analíticas"])
def get_envios_por_vehiculo():
    """
    Consulta 1: Total de envíos agregados por tipo de vehículo y estado del envío.
    """
    query = """
        SELECT 
            tipo_vehiculo,
            estado_envio,
            COUNT(*) as total_envios
        FROM vista_analitica_envios
        GROUP BY tipo_vehiculo, estado_envio
        ORDER BY total_envios DESC;
    """
    try:
        conn = get_athena_connection()
        df = pd.read_sql(query, conn)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Athena: {str(e)}")


@app.get("/analitica/reporte-ciudades-destino", tags=["Consultas Analíticas"])
def get_reporte_ciudades_destino():
    """
    Consulta 2: Distribución de envíos y paquetes procesados por ciudad de destino.
    """
    query = """
        SELECT 
            ciudad_destino,
            COUNT(DISTINCT cliente_id) as total_clientes,
            COUNT(*) as total_paquetes
        FROM vista_reporte_logistica
        GROUP BY ciudad_destino
        ORDER BY total_paquetes DESC;
    """
    try:
        conn = get_athena_connection()
        df = pd.read_sql(query, conn)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Athena: {str(e)}")
