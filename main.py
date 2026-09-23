import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pyathena import connect
import pandas as pd

app = FastAPI(
    title="API Rest Consultas Analíticas - Logística y Envíos",
    description="Microservicio 5: Consultas sobre AWS Athena y Catálogo de Glue",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DATABASE_GLUE = os.getenv("DATABASE_GLUE", "logis_analytics")
ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "logis-analytics-wg")
S3_STAGING_DIR = os.getenv("S3_STAGING_DIR")


def get_athena_connection():
    """Crea una conexión a Athena usando la configuración de Glue/WorkGroup."""
    if not S3_STAGING_DIR:
        raise RuntimeError(
            "Falta la variable de entorno S3_STAGING_DIR con el bucket de resultados de Athena."
        )

    return connect(
        s3_staging_dir=S3_STAGING_DIR,
        region_name=AWS_REGION,
        schema_name=DATABASE_GLUE,
        work_group=ATHENA_WORKGROUP,
    )


def execute_query(query: str):
    """Ejecuta una consulta fija en Athena y devuelve una lista JSON."""
    conn = None
    try:
        conn = get_athena_connection()
        df = pd.read_sql(query, conn)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en Athena: {str(e)}")
    finally:
        if conn is not None:
            conn.close()


@app.get("/", tags=["Health Check"])
def root():
    return {"message": "API Analítica de Logística y Envíos activa"}


@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}


# -------------------------------------------------------------
# Endpoints Analíticos
# Las consultas son fijas: no se acepta SQL enviado por el cliente.
# -------------------------------------------------------------

@app.get("/analitica/envios-por-vehiculo", tags=["Consultas Analíticas"])
def get_envios_por_vehiculo():
    """Consulta 1: envíos por tipo de vehículo y estado."""
    query = """
        SELECT
            e."vehiculoasignado.tipo" AS tipo_vehiculo,
            e.estado AS estado_envio,
            COUNT(*) AS total_envios
        FROM envios e
        WHERE e."vehiculoasignado.tipo" IS NOT NULL
        GROUP BY e."vehiculoasignado.tipo", e.estado
        ORDER BY total_envios DESC
    """
    return execute_query(query)


@app.get("/analitica/reporte-ciudades-destino", tags=["Consultas Analíticas"])
def get_reporte_ciudades_destino():
    """Consulta 2: clientes y paquetes por ciudad de destino."""
    query = """
        SELECT
            e."direccionentrega.ciudad" AS ciudad_destino,
            COUNT(DISTINCT e.clienteid) AS total_clientes,
            COUNT(*) AS total_paquetes
        FROM envios e
        WHERE e."direccionentrega.ciudad" IS NOT NULL
        GROUP BY e."direccionentrega.ciudad"
        ORDER BY total_paquetes DESC
    """
    return execute_query(query)


@app.get("/analitica/rendimiento-conductores", tags=["Consultas Analíticas"])
def get_rendimiento_conductores():
    """Consulta 3: rendimiento de conductores según envíos asignados y entregados."""
    query = """
        SELECT
            e."conductorasignado.nombre" AS nombre_conductor,
            e."conductorasignado.apellido" AS apellido_conductor,
            e."vehiculoasignado.placa" AS placa_vehiculo,
            e."vehiculoasignado.tipo" AS tipo_vehiculo,
            COUNT(e._id) AS total_envios_asignados,
            COUNT(CASE WHEN e.estado = 'ENTREGADO' THEN 1 END) AS envios_entregados
        FROM envios e
        WHERE e."conductorasignado.nombre" IS NOT NULL
        GROUP BY
            e."conductorasignado.nombre",
            e."conductorasignado.apellido",
            e."vehiculoasignado.placa",
            e."vehiculoasignado.tipo"
        ORDER BY total_envios_asignados DESC
    """
    return execute_query(query)


@app.get("/analitica/top-clientes-demanda", tags=["Consultas Analíticas"])
def get_top_clientes_demanda():
    """Consulta 4: clientes con mayor cantidad de envíos realizados."""
    query = """
        SELECT
            cl.nombre AS nombre_cliente,
            cl.email AS email_cliente,
            COUNT(e._id) AS total_envios_realizados,
            MAX(e."direccionentrega.ciudad") AS ciudad_mas_frecuente
        FROM envios e
        JOIN clientes cl
            ON e.clienteid = cl.id
        GROUP BY cl.nombre, cl.email
        ORDER BY total_envios_realizados DESC
        LIMIT 10
    """
    return execute_query(query)


@app.get("/analitica/flujo-origen-destino", tags=["Consultas Analíticas"])
def get_flujo_origen_destino():
    """Consulta 5: volumen de envíos entre ciudad de origen y destino."""
    query = """
        SELECT
            d.ciudad AS ciudad_origen,
            e."direccionentrega.ciudad" AS ciudad_destino,
            COUNT(e._id) AS volumen_envios
        FROM envios e
        JOIN direcciones d
            ON e.clienteid = d.cliente_id
        GROUP BY d.ciudad, e."direccionentrega.ciudad"
        ORDER BY volumen_envios DESC
    """
    return execute_query(query)


@app.get("/analitica/reporte-360-operaciones", tags=["Consultas Analíticas"])
def get_reporte_360_operaciones():
    """Consulta 6: vista resumida de las operaciones logísticas."""
    query = """
        SELECT
            e._id AS envio_id,
            cl.nombre AS cliente,
            e."conductorasignado.nombre" AS conductor,
            e."vehiculoasignado.placa" AS vehiculo_placa,
            d.ciudad AS origen,
            e."direccionentrega.ciudad" AS destino,
            e.estado AS estado_envio
        FROM envios e
        JOIN clientes cl
            ON e.clienteid = cl.id
        LEFT JOIN direcciones d
            ON e.clienteid = d.cliente_id
        LIMIT 50
    """
    return execute_query(query)
