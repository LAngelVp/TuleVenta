import os
import pandas as pd
from datetime import datetime

class OperacionMasivaCsvController:
    """
    Controlador genérico y reutilizable para la lectura, validación y tipado
    de archivos de importación masiva (CSV y Excel) para cualquier módulo
    (Productos, Clientes, Empleados, etc.).
    """

    @staticmethod
    def leer_y_validar_archivo(documento: str, columnas_requeridas: list, columnas_validas: set = None) -> list:
        """
        Lee un archivo CSV o Excel de forma segura, valida su estructura de columnas,
        y devuelve una lista de diccionarios limpios con valores normalizados.

        :param documento: Ruta absoluta del archivo.
        :param columnas_requeridas: Lista de columnas indispensables que debe tener el archivo.
        :param columnas_validas: Conjunto de columnas válidas basadas en el modelo de base de datos.
                                 Si se especifica, lanzaría un error si hay columnas extrañas.
        :return: Lista de diccionarios, donde cada diccionario representa una fila limpia.
        """
        ext = os.path.splitext(documento)[1].lower()

        # 1. Cargar el DataFrame de forma tolerante a codificaciones
        if ext == '.csv':
            try:
                df = pd.read_csv(documento, na_filter=False)
            except Exception:
                df = pd.read_csv(documento, na_filter=False, encoding='latin-1')
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(documento, na_filter=False)
        else:
            raise ValueError("Formato de archivo no soportado. Debe ser CSV o Excel (.xlsx, .xls)")

        # Normalizar nombres de columnas (limpiar espacios en blanco)
        df.columns = [col.strip() for col in df.columns]

        # 2. Validar columnas requeridas
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if columnas_faltantes:
            raise ValueError(f"Faltan columnas indispensables en el archivo: {', '.join(columnas_faltantes)}")

        # 3. Validar columnas incorrectas (estructura de base de datos)
        if columnas_validas is not None:
            columnas_archivo = set(df.columns)
            columnas_incorrectas = columnas_archivo - columnas_validas
            if columnas_incorrectas:
                raise ValueError(
                    f"El archivo contiene columnas que no pertenecen a la estructura de la base de datos: {', '.join(columnas_incorrectas)}"
                )

        # 4. Convertir cada fila a diccionario limpio
        registros_limpios = []
        for _, row in df.iterrows():
            registro = {}
            for col in df.columns:
                registro[col] = OperacionMasivaCsvController.limpiar_valor(row[col])
            registros_limpios.append(registro)

        return registros_limpios

    @staticmethod
    def limpiar_valor(val):
        """Limpia valores nulos de pandas (NaN, NaT, None) a valores de cadena vacíos estándar"""
        if pd.isnull(val) or str(val).strip().lower() in ['nan', 'none', 'nat']:
            return ""
        return str(val).strip()

    @staticmethod
    def parse_float(val, default=0.0) -> float:
        """Parsea un valor a float de forma completamente segura"""
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ['nan', 'none', 'nat']:
            return default
        try:
            return float(val_str)
        except Exception:
            return default

    @staticmethod
    def parse_int(val, default=0) -> int:
        """Parsea un valor a entero de forma completamente segura"""
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ['nan', 'none', 'nat']:
            return default
        try:
            return int(float(val_str))
        except Exception:
            return default

    @staticmethod
    def parse_date(val, default=None):
        """Parsea un valor a fecha de forma completamente segura"""
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ['', 'nan', 'none', 'nat']:
            return default
        try:
            dt = pd.to_datetime(val_str)
            if pd.isnull(dt):
                return default
            return dt.date()
        except Exception:
            return default
