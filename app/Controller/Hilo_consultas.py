import pandas as pd
from PySide6.QtCore import QObject, Signal, QThread
from ..DataBase.conexionBD import Conexion_base_datos
from contextlib import contextmanager
from typing import Optional, Callable, Dict, Any
import logging

class WorkerDBManager:
    """
    Manager global para WorkerDB - Singleton
    """
    _instance = None
    _workers: Dict[str, 'WorkerDB'] = {}
    _worker_counter = 0
    
    def __init__(self):
        if WorkerDBManager._instance is not None:
            raise Exception("WorkerDBManager es un singleton. Usa WorkerDBManager.get_instance()")
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = WorkerDBManager()
        return cls._instance
    
    @classmethod
    def create_worker(cls, owner_id: str = "default") -> str:
        """Crea un nuevo worker y retorna su ID"""
        worker_id = f"{owner_id}_worker_{cls._worker_counter}"
        cls._worker_counter += 1
        
        # Limpiar worker anterior del mismo owner
        cls.cleanup_owner_workers(owner_id)
        
        worker = WorkerDB()
        cls._workers[worker_id] = worker
        
        if cls._instance:
            cls._instance.logger.debug(f"Worker creado: {worker_id}")
        
        return worker_id
    
    @classmethod
    def get_worker(cls, worker_id: str) -> Optional['WorkerDB']:
        """Obtiene un worker por su ID"""
        return cls._workers.get(worker_id)
    
    @classmethod
    def connect_worker_signals(cls, worker_id: str,
                             resultado_callback: Optional[Callable] = None,
                             error_callback: Optional[Callable] = None,
                             terminado_callback: Optional[Callable] = None):
        """Conecta señales del worker de manera segura"""
        worker = cls.get_worker(worker_id)
        if not worker:
            if cls._instance:
                cls._instance.logger.warning(f"Worker {worker_id} no encontrado")
            return
        
        try:
            if resultado_callback:
                worker.resultado.connect(resultado_callback)
            if error_callback:
                worker.error.connect(error_callback)
            if terminado_callback:
                worker.terminado.connect(terminado_callback)
                
            if cls._instance:
                cls._instance.logger.debug(f"Señales conectadas para worker: {worker_id}")
                
        except Exception as e:
            if cls._instance:
                cls._instance.logger.error(f"Error conectando señales: {str(e)}")
    
    @classmethod
    def cleanup_worker(cls, worker_id: str):
        """Limpia un worker específico"""
        if worker_id not in cls._workers:
            return
        
        worker = cls._workers[worker_id]
        
        try:
            # Desconectar todas las señales
            try:
                worker.disconnect()
            except (RuntimeError, TypeError):
                pass
            
            # Detener el hilo de manera segura
            if hasattr(worker, 'thread') and worker.thread is not None:
                thread = worker.thread
                if thread.isRunning():
                    thread.quit()
                    if not thread.wait(500):
                        thread.terminate()
                        thread.wait(300)
            
            # Eliminar el worker
            try:
                worker.deleteLater()
            except RuntimeError:
                pass
            
            if cls._instance:
                cls._instance.logger.debug(f"Worker limpiado: {worker_id}")
            
        except Exception as e:
            if cls._instance:
                cls._instance.logger.error(f"Error en cleanup_worker: {str(e)}")
        finally:
            # Eliminar referencia
            if worker_id in cls._workers:
                del cls._workers[worker_id]
    
    @classmethod
    def cleanup_owner_workers(cls, owner_id: str):
        """Limpia todos los workers de un owner específico"""
        workers_to_remove = [
            worker_id for worker_id in cls._workers.keys() 
            if worker_id.startswith(f"{owner_id}_worker_")
        ]
        
        for worker_id in workers_to_remove:
            cls.cleanup_worker(worker_id)
    
    @classmethod
    def cleanup_all_workers(cls):
        """Limpia todos los workers activos"""
        for worker_id in list(cls._workers.keys()):
            cls.cleanup_worker(worker_id)
        
        if cls._instance:
            cls._instance.logger.info("Todos los workers han sido limpiados")
    
    @classmethod
    def list_active_workers(cls) -> list:
        """Lista todos los workers activos"""
        return list(cls._workers.keys())


class WorkerDB(QObject):
    terminado = Signal()
    resultado = Signal(object, bool)  # Simplificado a (data, estado)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._run)
        self._funcion = None
        self._args = ()
        self._kwargs = {}
        
    def ejecutar(self, funcion, *args, **kwargs):
        """Configura la función y parámetros para ejecutar en el hilo"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
            
        self._funcion = funcion
        self._args = args
        self._kwargs = kwargs
        self.thread.start()
        
    def _run(self):
        """Ejecuta la operación en el hilo secundario"""
        try:
            with Conexion_base_datos() as db:
                session = db.abrir_sesion()
                result = self._funcion(session, *self._args, **self._kwargs)
                
                # Emitir resultados según el tipo de retorno
                if isinstance(result, tuple) and len(result) == 2:
                    data, estado = result
                    self.resultado.emit(data, estado)
                else:
                    self.resultado.emit(result, True)
                    
        except Exception as e:
            self.error.emit(f"Error en WorkerDB: {str(e)}")
        finally:
            self.terminado.emit()
            self.thread.quit()
    
    # Métodos estáticos para acceso fácil al manager
    @staticmethod
    def create_managed_worker(owner_id: str = "default") -> str:
        """Crea un worker gestionado globalmente"""
        return WorkerDBManager.create_worker(owner_id)
    
    @staticmethod
    def connect_managed_signals(worker_id: str,
                              resultado_callback: Optional[Callable] = None,
                              error_callback: Optional[Callable] = None,
                              terminado_callback: Optional[Callable] = None):
        """Conecta señales a un worker gestionado"""
        WorkerDBManager.connect_worker_signals(
            worker_id, resultado_callback, error_callback, terminado_callback
        )
    
    @staticmethod
    def get_managed_worker(worker_id: str) -> Optional['WorkerDB']:
        """Obtiene un worker gestionado"""
        return WorkerDBManager.get_worker(worker_id)
    
    @staticmethod
    def cleanup_managed_worker(worker_id: str):
        """Limpia un worker gestionado"""
        WorkerDBManager.cleanup_worker(worker_id)
    
    @staticmethod
    def cleanup_all_managed_workers():
        """Limpia todos los workers gestionados"""
        WorkerDBManager.cleanup_all_workers()
    
    @staticmethod
    def cleanup_owner_workers(owner_id: str):
        """Limpia workers de un owner específico"""
        WorkerDBManager.cleanup_owner_workers(owner_id)

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