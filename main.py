import os
import datetime
import jwt
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="KPI API - Demo")

# CORS: permite que el frontend (en otro dominio) consuma esta API.
# En produccion conviene restringir allow_origins a tu dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Autenticacion con clave compartida ---
# La clave real NUNCA esta en el codigo ni en el HTML: vive solo como
# variable de entorno en Render. Si no esta configurada, usa un valor
# de prueba para que puedas probar en local, pero en Render SIEMPRE
# hay que sobreescribirla.
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "cambiar-esta-clave")
JWT_SECRET = os.environ.get("JWT_SECRET", "cambiar-este-secreto-tambien")
TOKEN_EXPIRATION_HOURS = 8


class LoginRequest(BaseModel):
    password: str


def crear_token() -> str:
    payload = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRATION_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verificar_token(authorization: str = Header(default=None)):
    """Dependencia que protege un endpoint: exige un Bearer token valido."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el token de autenticacion")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token expiro, volve a iniciar sesion")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")
    return True


# Los datos se cargan UNA vez en memoria del servidor al arrancar.
# Nunca viajan enteros al navegador: el navegador solo pide resumenes.
DATA_PATH = os.path.join(os.path.dirname(__file__), "ventas.csv")
df = pd.read_csv(DATA_PATH, parse_dates=["fecha"])


@app.get("/")
def root():
    return {"status": "ok", "mensaje": "KPI API funcionando"}


@app.post("/api/login")
def login(datos: LoginRequest):
    if datos.password != DASHBOARD_PASSWORD:
        raise HTTPException(status_code=401, detail="Clave incorrecta")
    return {"token": crear_token()}


@app.get("/api/kpis", dependencies=[Depends(verificar_token)])
def kpis_generales():
    """Resumen general: lo que se ve en las tarjetas principales del dashboard."""
    return {
        "ventas_totales": round(df["monto"].sum(), 2),
        "cantidad_operaciones": int(len(df)),
        "ticket_promedio": round(df["monto"].mean(), 2),
        "unidades_vendidas": int(df["cantidad"].sum()),
    }


@app.get("/api/ventas-por-categoria", dependencies=[Depends(verificar_token)])
def ventas_por_categoria():
    """Ventas agrupadas por categoria, ya agregadas en el servidor."""
    agg = (
        df.groupby("categoria")["monto"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
    )
    return [{"categoria": k, "monto": v} for k, v in agg.items()]


@app.get("/api/ventas-por-mes", dependencies=[Depends(verificar_token)])
def ventas_por_mes():
    """Serie temporal mensual, para el grafico de tendencia."""
    serie = (
        df.set_index("fecha")["monto"]
        .resample("MS")
        .sum()
        .round(2)
    )
    return [{"mes": idx.strftime("%Y-%m"), "monto": val} for idx, val in serie.items()]


@app.get("/api/ventas-por-region", dependencies=[Depends(verificar_token)])
def ventas_por_region():
    agg = (
        df.groupby("region")["monto"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
    )
    return [{"region": k, "monto": v} for k, v in agg.items()]
