import pandas as pd
from PySide6.QtCore import QObject, Signal
from ..DataBase.conexionBD import Conexion_base_datos

from PySide6.QtCore import QThread, QObject, Signal
from contextlib import contextmanager

class WorkerDB(QObject):
    terminado = Signal()
    resultado = Signal(object, bool, str)
    error = Signal(str)
    resultado_productos_masivos_excel = Signal(object, object)

    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._run)
        
    def ejecutar(self, funcion, *args, **kwargs):
        """Configura los parámetros para la ejecución del hilo"""
        self._funcion = funcion
        self._args = args
        self._kwargs = kwargs
        self.thread.start()

    def _run(self):
        """Método que se ejecuta en el hilo secundario"""
        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                data, estado = self._funcion(session, *self._args, **self._kwargs)
                if estado:
                    self.resultado.emit(data, estado, "")
                else:
                    self.resultado.emit(None, estado, "No se logró la operación")
        except Exception as e:
            print(e)
            self.error.emit(str(e))
        finally:
            self.terminado.emit()
            self.thread.quit()

    def detener(self):
        """Detiene el hilo de forma segura"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    @contextmanager
    def ejecutar(self, funcion, *args, **kwargs):
        """Context manager para ejecución automática"""
        try:
            self.ejecutar(funcion, *args, **kwargs)
            yield self
        finally:
            self.detener()

class ProcesadorArchivo(QObject):
    terminado = Signal()
    error = Signal(str)
    resultado_productos_masivos_excel = Signal(object, object)  # (productos_nuevos, duplicados)

    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._procesar)

    def iniciar_procesamiento(self, documento, productos_existentes):
        """Configura los parámetros y arranca el hilo"""
        self.documento = documento
        self.productos_existentes = productos_existentes
        self.thread.start()

    def _procesar(self):
        """Método que se ejecuta en el hilo secundario"""
        try:
            columnas_esperadas = [
                "Proveedor", "Código de Barras", "Nombre", "Categoría", "Marca", "Modelo", "Color",
                "Material", "Unidad de Medida", "Presentación", "Costo Inicial","Costo Final", 
                "Margen Porcentaje", "Precio Venta", "Existencia", "Existencia Min", "Existencia Max", 
                "Peso", "Largo Dimensiones", "Alto Dimensiones", "Ancho Dimensiones",
                "Descripción", "Notas", "Fecha Vencimiento", "Fecha Fabricación", "Imagen"
            ]

            df = pd.read_csv(self.documento, na_filter=False)

            columnas_faltantes = [col for col in columnas_esperadas if col not in df.columns]
            if columnas_faltantes:
                raise ValueError(f"Faltan columnas: {', '.join(columnas_faltantes)}")

            df = df[columnas_esperadas]
            productos_nuevos = []
            duplicados = []

            codigos_existentes = set(str(p["codigo_barras"]).strip() for p in self.productos_existentes)

            for _, row in df.iterrows():
                codigo = str(row["Código de Barras"]).strip()
                if codigo in codigos_existentes:
                    duplicados.append(codigo)
                    continue

                producto = {
                    "proveedor": str(row["Proveedor"]).strip(),
                    "codigo_barras": codigo,
                    "nombre": str(row["Nombre"]).strip(),
                    "categoria": str(row["Categoría"]).strip(),
                    "marca": str(row["Marca"]).strip(),
                    "modelo": str(row["Modelo"]).strip(),
                    "color": str(row["Color"]).strip(),
                    "material": str(row["Material"]).strip(),
                    "unidad_medida": str(row["Unidad de Medida"]).strip(),
                    "presentacion": str(row["Presentación"]).strip(),
                    "costo_inicial": float(row["Costo Inicial"]),
                    "costo_final": float(row["Costo Final"]),
                    "margen_porcentaje": int(row["Margen Porcentaje"]),
                    "precio_venta": float(row["Precio Venta"]),
                    "existencia": float(row["Existencia"]),
                    "existencia_min": float(row["Existencia Min"]),
                    "existencia_max": float(row["Existencia Max"]),
                    "peso": float(row["Peso"]),
                    "largo_dimensiones": float(row["Largo Dimensiones"]),
                    "alto_dimensiones": float(row["Alto Dimensiones"]),
                    "ancho_dimensiones": float(row["Ancho Dimensiones"]),
                    "descripcion": str(row["Descripción"]).strip(),
                    "notas": row["Notas"],
                    "fecha_vencimiento": row["Fecha Vencimiento"],
                    "fecha_fabricacion": row["Fecha Fabricación"],
                    "imagen": str(row["Imagen"]).strip()
                }
                productos_nuevos.append(producto)

            self.resultado_productos_masivos_excel.emit(productos_nuevos, duplicados)
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.terminado.emit()
            self.thread.quit()

    def detener(self):
        """Detiene el hilo de forma segura"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    @contextmanager
    def ejecutar(self, documento, productos_existentes):
        """Context manager para ejecución automática"""
        try:
            self.iniciar_procesamiento(documento, productos_existentes)
            yield self
        finally:
            self.detener()