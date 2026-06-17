import requests
import pandas as pd
from datetime import datetime
import os

# Configuración de las ciudades y parámetros de la API
CIUDADES = [
    {"nombre": "Bogota",    "lat": 4.711,  "lon": -74.072},
    {"nombre": "Medellin",  "lat": 6.244,  "lon": -75.574},
    {"nombre": "Cali",      "lat": 3.451,  "lon": -76.532},
]

START_DATE = "2023-01-01"
END_DATE   = "2026-05-31"
VARIABLES  = "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
TIMEZONE   = 'America/Bogota'
BASE_URL   = "https://archive-api.open-meteo.com/v1/archive"

# Funciones

def fetch_climate_data (ciudad: dict) -> dict:
    "Llama a la API de Open-Meteo para obtener los datos climáticos de una ciudad"
    params = {
        "latitude": ciudad["lat"],
        "longitude": ciudad["lon"],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": VARIABLES,
        "timezone": TIMEZONE
    }
    print(f" Consultando API para {ciudad['nombre']}...")
    response = requests.get(BASE_URL, params=params, timeout=30)
    
    # En producción siempre validas el estatus code
    response.raise_for_status()
    
    return response.json()

def json_a_dataframe(data:dict, nombre_ciudad:str) -> pd.DataFrame:
    """
    Transforma el JSON anidado de la API en un DataFrame plano.
    Este patrón (listas paralelas → columnas) es muy común en APIs.
    """
    daily = data["daily"]

    df = pd.DataFrame({
        "fecha":            daily["time"],
        "ciudad":           nombre_ciudad,
        "temp_max_c":       daily["temperature_2m_max"],
        "temp_min_c":       daily["temperature_2m_min"],
        "precipitacion_mm": daily["precipitation_sum"],
        "viento_max_kmh":   daily["windspeed_10m_max"],
    })

    return df

def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza básica:
    - Convierte fecha a tipo datetime
    - Elimina filas con todos los valores nulos
    - Agrega columna de rango de temperatura
    - Agrega columna con timestamp de ingesta
    """
    
    df['fecha'] = pd.to_datetime(df['fecha'])
    # Eliminar filas donde TODAS las métricas son nulas
    columnas_metricas = ["temp_max_c", "temp_min_c", "precipitacion_mm", "viento_max_kmh"]
    df = df.dropna(subset=columnas_metricas, how='all')
    
    # Feature derivada: Rango de temperatura del día
    df['rango_temp_c'] = df['temp_max_c'] - df['temp_min_c']
    
    # Metadata de ingesta: cuándo fue procesado este dato
    df['ingesta_timestamp'] = datetime.now().isoformat()
    return df

def validar_datos (df:pd.DataFrame) -> bool:
    """
    Validaciones básicas de calidad de datos.
    En producción esto se hace con librerías como Great Expectations.
    Retorna True si los datos son válidos.
    """
    errores = []
    
    # No pueden haber fechas nulas
    if df['fecha'].isnull().any():
        errores.append("Hay fechas nulas.")
        
    # Temperaturas máximas siempre debe ser >= mínima
    if(df['temp_max_c'] < df['temp_min_c']).any():
        errores.append("Hay registros donde la temperatura máxima es menor que la mínima.")
        
    # Precipitación no puede ser negativa
    if (df['precipitacion_mm'] < 0).any():
        errores.append("Hay registros con precipitación negativa.")
        
    if errores:
        for e in errores:
            print(f"  ⚠ Validación fallida: {e}")
        return False

    print(f"  ✓ Validaciones OK — {len(df)} filas válidas")
    return True
            
# Ejecución principal

def main():
    print("=" * 50)
    print("Ingesta de datos climáticos - Open-Meteo API")
    print("=" * 50)
    
    os.makedirs("datos", exist_ok=True)
    
    todos_los_datos = []
    
    for ciudad in CIUDADES:
        print(f"\n[{ciudad['nombre']}]")
        try:
            raw_json   = fetch_climate_data(ciudad)
            df         = json_a_dataframe(raw_json, ciudad["nombre"])
            df         = limpiar_datos(df)
            es_valido  = validar_datos(df)
            
            if es_valido:
                todos_los_datos.append(df)
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error de red para  {ciudad['nombre']}: {e}")
        except Exception as e:
            print(f"  ❌ Error en estrucutra del JSON: {e}")
            
    if not todos_los_datos:
        print("\nNo se obtuvieron datos. Revisa tu conexión.")
        return
    
# Combinar todas las ciudades en un solo DataFrame
    df_final = pd.concat(todos_los_datos, ignore_index=True)

    # Guardar
    output_path = "datos/clima.csv"
    df_final.to_csv(output_path, index=False)

    print(f"\n{'=' * 50}")
    print(f"✓ Proceso completado")
    print(f"  Filas totales:  {len(df_final)}")
    print(f"  Ciudades:       {df_final['ciudad'].nunique()}")
    print(f"  Período:        {df_final['fecha'].min().date()} → {df_final['fecha'].max().date()}")
    print(f"  Archivo:        {output_path}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
            