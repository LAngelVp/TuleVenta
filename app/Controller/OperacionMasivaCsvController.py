import csv
import math
import os
from collections import Counter
from contextlib import closing
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError
from datetime import date, datetime

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from openpyxl.utils.exceptions import InvalidFileException

class OperacionMasivaCsvController:
    """
    Controlador genérico y reutilizable para la lectura, validación y tipado
    de archivos de importación masiva (CSV y Excel) para cualquier módulo
    (Productos, Clientes, Empleados, etc.).
    """

    @staticmethod
    def _es_valor_nulo(val) -> bool:
        if val is None:
            return True
        if isinstance(val, float):
            try:
                return math.isnan(val)
            except ValueError:
                return False
        if isinstance(val, str):
            return val.strip().lower() in ['', 'nan', 'none', 'nat']
        return False

    @staticmethod
    def _leer_csv(documento: str, con_origen=False):
        ultimo_error = None
        for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                with open(documento, 'r', encoding=encoding, newline='') as archivo:
                    lector = csv.DictReader(archivo)
                    columnas = [str(columna).strip() for columna in (lector.fieldnames or [])]
                    registros = []
                    filas_origen = []
                    for fila in lector:
                        if not fila:
                            continue
                        registro = {}
                        for columna_original, valor in fila.items():
                            columna = str(columna_original).strip()
                            if not columna:
                                continue
                            registro[columna] = OperacionMasivaCsvController.limpiar_valor(valor)
                        if any(not OperacionMasivaCsvController._es_valor_nulo(valor) for valor in registro.values()):
                            registros.append(registro)
                            filas_origen.append({"fila": lector.line_num, "valores": registro,
                                                 "originales": {str(campo).strip(): "" if valor is None else str(valor)
                                                                for campo, valor in fila.items()}})
                    return (columnas, registros, filas_origen) if con_origen else (columnas, registros)
            except UnicodeDecodeError as e:
                ultimo_error = e
                continue
            except Exception as e:
                ultimo_error = e
                break
        raise ValueError(f"No se pudo leer el archivo CSV: {ultimo_error}")

    @staticmethod
    def _leer_excel(documento: str, ext: str, con_origen=False):
        if ext == '.xls':
            raise ValueError('Los archivos .xls no son compatibles en esta instalación. Guarda el archivo como .xlsx o .csv.')

        with closing(load_workbook(documento, read_only=True, data_only=True)) as workbook:
            hoja = workbook.active
            filas = hoja.iter_rows(values_only=True)
            encabezados = next(filas, None)
            if not encabezados:
                return ([], [], []) if con_origen else ([], [])
            columnas = [str(columna).strip() if columna is not None else '' for columna in encabezados]
            registros = []
            filas_origen = []
            for numero, fila in enumerate(filas, start=2):
                if fila is None or all(OperacionMasivaCsvController._es_valor_nulo(valor) for valor in fila):
                    continue
                registro = {}
                for indice, columna in enumerate(columnas):
                    if not columna:
                        continue
                    valor = fila[indice] if indice < len(fila) else ''
                    registro[columna] = OperacionMasivaCsvController.limpiar_valor(valor)
                registros.append(registro)
                filas_origen.append({"fila": numero, "valores": registro,
                                     "originales": {columna: "" if valor is None else str(valor)
                                                    for columna, valor in zip(columnas, fila)}})
            return (columnas, registros, filas_origen) if con_origen else (columnas, registros)

    @staticmethod
    def leer_con_reporte(documento, columnas_requeridas, columnas_validas=None):
        reporte = {"columnas": [], "filas": [], "errores": [], "advertencias": []}
        try:
            extension = os.path.splitext(documento)[1].lower()
            if extension == ".csv":
                columnas, _, filas = OperacionMasivaCsvController._leer_csv(documento, con_origen=True)
            elif extension in (".xlsx", ".xls"):
                columnas, _, filas = OperacionMasivaCsvController._leer_excel(documento, extension, con_origen=True)
            else:
                raise ValueError("Formato compatible: .csv o .xlsx")
        except (ValueError, OSError, BadZipFile, ParseError, InvalidFileException):
            reporte["errores"].append({"fila": None, "campo": None, "codigo": "lectura",
                                       "mensaje": "No se pudo leer el archivo; formatos compatibles: .csv y .xlsx"})
            return reporte
        reporte["columnas"] = columnas
        reporte["filas"] = filas
        for columna, cantidad in Counter(columnas).items():
            if not columna:
                codigo = "encabezado_vacio"
            elif cantidad > 1:
                codigo = "encabezado_duplicado"
            elif columnas_validas is not None and columna not in columnas_validas:
                codigo = "columna_desconocida"
            else:
                continue
            reporte["errores"].append({"fila": 1, "campo": columna, "codigo": codigo,
                                       "mensaje": "Encabezado no valido"})
        for columna in columnas_requeridas:
            if columna not in columnas:
                reporte["errores"].append({"fila": 1, "campo": columna, "codigo": "columna_requerida",
                                           "mensaje": "Falta columna requerida"})
        return reporte

    @staticmethod
    def numero_con_reporte(valor):
        if valor is None or not str(valor).strip():
            return {"valor": None, "codigo": "vacio"}
        try:
            numero = float(valor)
        except (ValueError, TypeError, OverflowError):
            return {"valor": None, "codigo": "invalido"}
        if not math.isfinite(numero):
            return {"valor": None, "codigo": "no_finito"}
        return {"valor": numero, "codigo": "valido"}

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

        # 1. Cargar registros desde CSV/Excel sin depender de pandas
        if ext == '.csv':
            columnas, registros_limpios = OperacionMasivaCsvController._leer_csv(documento)
        elif ext in ['.xlsx', '.xls']:
            columnas, registros_limpios = OperacionMasivaCsvController._leer_excel(documento, ext)
        else:
            raise ValueError("Formato de archivo no soportado. Debe ser CSV o Excel (.xlsx, .xls)")

        # 2. Validar columnas requeridas
        columnas_faltantes = [col for col in columnas_requeridas if col not in columnas]
        if columnas_faltantes:
            raise ValueError(f"Faltan columnas indispensables en el archivo: {', '.join(columnas_faltantes)}")

        # 3. Validar columnas incorrectas (estructura de base de datos)
        if columnas_validas is not None:
            columnas_archivo = set(columnas)
            columnas_incorrectas = columnas_archivo - columnas_validas
            if columnas_incorrectas:
                raise ValueError(
                    f"El archivo contiene columnas que no pertenecen a la estructura de la base de datos: {', '.join(columnas_incorrectas)}"
                )

        return registros_limpios

    @staticmethod
    def limpiar_valor(val):
        """Normaliza valores vacíos a cadena vacía conservando fechas y números válidos."""
        if OperacionMasivaCsvController._es_valor_nulo(val):
            return ""
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return val
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
        if OperacionMasivaCsvController._es_valor_nulo(val):
            return default
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        if isinstance(val, (int, float)):
            try:
                return from_excel(val).date()
            except Exception:
                return default

        val_str = str(val).strip()
        try:
            return datetime.fromisoformat(val_str.replace('Z', '+00:00')).date()
        except Exception:
            pass

        formatos = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d',
            '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S'
        ]
        for formato in formatos:
            try:
                return datetime.strptime(val_str, formato).date()
            except ValueError:
                continue
        return default
