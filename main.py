import os
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="KPI API - Demo")

# CORS: permite que el frontend (en otro dominio) consuma esta API.
# En produccion conviene restringir allow_origins a tu dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Los datos se cargan UNA vez en memoria del servidor al arrancar.
# Nunca viajan enteros al navegador: el navegador solo pide resumenes.
DATA_PATH = os.path.join(os.path.dirname(__file__), "ventas.csv")
df = pd.read_csv(DATA_PATH, parse_dates=["fecha"])


@app.get("/")
def root():
    return {"status": "ok", "mensaje": "KPI API funcionando"}


@app.get("/api/kpis")
def kpis_generales():
    """Resumen general: lo que se ve en las tarjetas principales del dashboard."""
    return {
        "ventas_totales": round(df["monto"].sum(), 2),
        "cantidad_operaciones": int(len(df)),
        "ticket_promedio": round(df["monto"].mean(), 2),
        "unidades_vendidas": int(df["cantidad"].sum()),
    }


@app.get("/api/ventas-por-categoria")
def ventas_por_categoria():
    """Ventas agrupadas por categoria, ya agregadas en el servidor."""
    agg = (
        df.groupby("categoria")["monto"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
    )
    return [{"categoria": k, "monto": v} for k, v in agg.items()]


@app.get("/api/ventas-por-mes")
def ventas_por_mes():
    """Serie temporal mensual, para el grafico de tendencia."""
    serie = (
        df.set_index("fecha")["monto"]
        .resample("MS")
        .sum()
        .round(2)
    )
    return [{"mes": idx.strftime("%Y-%m"), "monto": val} for idx, val in serie.items()]


@app.get("/api/ventas-por-region")
def ventas_por_region():
    agg = (
        df.groupby("region")["monto"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
    )
    return [{"region": k, "monto": v} for k, v in agg.items()]
