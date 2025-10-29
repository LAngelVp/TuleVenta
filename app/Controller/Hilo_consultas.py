import pandas as pd
from PySide6.QtCore import QObject, Signal, QThread
from ..DataBase.conexionBD import Conexion_base_datos
from contextlib import contextmanager
from typing import Optional, Callable, Dict, Any
import chardet
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
            print(f'hilos eliminados: {worker_id}')
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
            logging.error(f"Error en WorkerDB: {str(e)}", exc_info=True)
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

class ProcesadorArchivoManager:
    """
    Manager global para ProcesadorArchivo - Singleton
    """
    _instance = None
    _workers: Dict[str, 'ProcesadorArchivoWorker'] = {}
    _worker_counter = 0
    
    def __init__(self):
        if ProcesadorArchivoManager._instance is not None:
            raise Exception("ProcesadorArchivoManager es un singleton. Usa ProcesadorArchivoManager.get_instance()")
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ProcesadorArchivoManager()
        return cls._instance
    
    @classmethod
    def create_worker(cls, owner_id: str = "default") -> str:
        """Crea un nuevo worker y retorna su ID"""
        worker_id = f"{owner_id}_procesador_{cls._worker_counter}"
        cls._worker_counter += 1
        
        # Limpiar worker anterior del mismo owner
        cls.cleanup_owner_workers(owner_id)
        
        worker = ProcesadorArchivoWorker()
        cls._workers[worker_id] = worker
        
        if cls._instance:
            cls._instance.logger.debug(f"ProcesadorArchivoWorker creado: {worker_id}")
        
        return worker_id
    
    @classmethod
    def get_worker(cls, worker_id: str) -> Optional['ProcesadorArchivoWorker']:
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
                worker.resultado_productos_masivos_excel.connect(resultado_callback)
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
    def ejecutar_procesamiento(cls, worker_id: str, documento: str, productos_existentes: list):
        """Ejecuta el procesamiento en el worker"""
        worker = cls.get_worker(worker_id)
        if worker:
            worker.ejecutar(documento, productos_existentes)
    
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
            worker.detener()
            
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
            if worker_id.startswith(f"{owner_id}_procesador_")
        ]
        
        for worker_id in workers_to_remove:
            cls.cleanup_worker(worker_id)
    
    @classmethod
    def cleanup_all_workers(cls):
        """Limpia todos los workers activos"""
        for worker_id in list(cls._workers.keys()):
            cls.cleanup_worker(worker_id)
        
        if cls._instance:
            cls._instance.logger.info("Todos los workers de procesamiento han sido limpiados")
    
    @classmethod
    def list_active_workers(cls) -> list:
        """Lista todos los workers activos"""
        return list(cls._workers.keys())
    
class ProcesadorArchivoWorker(QObject):
    terminado = Signal()
    error = Signal(str)
    resultado_productos_masivos_excel = Signal(object, object)  # (productos_nuevos, duplicados)

    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._procesar)
        self._documento = None
        self._productos_existentes = None
        self._activo = False

    def ejecutar(self, documento: str, productos_existentes: list):
        """Configura y ejecuta el procesamiento"""
        if self.thread.isRunning():
            self.detener()
            
        self._documento = documento
        self._productos_existentes = productos_existentes
        self._activo = True
        self.thread.start()

    def _procesar(self):
        """Método que se ejecuta en el hilo secundario"""
        if not self._activo:
            return
        # encoding_detectado = self.detectar_encoding(self._documento)
        # print(f"Codificación detectada: {encoding_detectado}")
        try:
            df = pd.read_excel(self._documento, na_filter=False)
            # Verificar columnas mínimas requeridas
            columnas_requeridas = ["codigo_upc", "nombre_producto"]
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            if columnas_faltantes:
                raise ValueError(f"Columnas requeridas faltantes: {', '.join(columnas_faltantes)}")

            codigos_existentes = {str(p["codigo_barras"]).strip() for p in self._productos_existentes}
            productos_nuevos = []
            duplicados = []

            for _, row in df.iterrows():
                if not self._activo:  # Permitir cancelación
                    break
                    
                codigo = str(row["codigo_upc"]).strip()
                
                if not codigo or codigo.lower() in ['nan', 'none', '']:
                    continue
                    
                if codigo in codigos_existentes:
                    duplicados.append(codigo)
                    continue

                producto = {
                        # Columnas que SÍ están en el Excel
                        "codigo_barras": codigo,
                        "nombre": str(row["nombre_producto"]).strip(),
                        "marca": str(row.get("marca", "")).strip(),
                        "modelo": str(row.get("modelo", "")).strip(),
                        "precio_venta": self._convertir_a_float(row.get("precio", 0)),
                        "existencia": self._convertir_a_float(row.get("existencia", 0)),
                        "color": str(row.get("color", "")).strip(),
                        "material": str(row.get("material", "")).strip(),
                        "costo_inicial": self._convertir_a_float(row.get("costo_inicial", 0)),
                        "costo_final": self._convertir_a_float(row.get("costo_final", 0)),
                        "margen_porcentaje": self._convertir_a_entero(row.get("margen_porcentaje", 0)),
                        "existencia_min": self._convertir_a_float(row.get("existencia_minima", 0)),
                        "existencia_max": self._convertir_a_float(row.get("existencia_maxima", 0)),
                        "peso": self._convertir_a_float(row.get("peso", 0)),
                        "alto_cm": self._convertir_a_float(row.get("alto_cm", 0)),
                        "largo_cm": self._convertir_a_float(row.get("largo_cm", 0)),
                        "ancho_cm": self._convertir_a_float(row.get("ancho_cm", 0)),
                        "fecha_fabricacion": str(row.get("fecha_fabricacion", "")).strip(),
                        "fecha_vencimiento": str(row.get("fecha_vencimiento", "")).strip(),
                        "imagen": str(row.get("imagen", "")).strip(),
                        
                        # Columnas que la BD espera pero el Excel NO tiene - valores por defecto
                        "descripcion_producto": str(row.get("descripcion_producto", "")).strip(),  # No en Excel
                        "notas": str(row.get("notas", "")).strip(),  # No en Excel
                        "categoria": str(row.get("categoria", "")).strip(),  # No en Excel - se mapeará a categoria_id después
                        "proveedor": str(row.get("proveedor", "")).strip(),  # No en Excel
                        "presentacion": str(row.get("presentacion", "")).strip(),  # No en Excel - se mapeará a presentacion_producto_id después
                        "unidad_medida": str(row.get("unidad_medida", "")).strip()  # No en Excel - se mapeará a unidad_medida_productos_id después
                    }
                productos_nuevos.append(producto)
                codigos_existentes.add(codigo)

            if self._activo:
                self.resultado_productos_masivos_excel.emit(productos_nuevos, duplicados)
            
        except Exception as e:
            if self._activo:
                self.error.emit(str(e))
        finally:
            self._limpiar()
            self.terminado.emit()

    def _convertir_a_float(self, valor):
        """Convierte valores a float de forma segura"""
        try:
            return float(valor) if str(valor).strip() else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _convertir_a_entero(self, valor):
        """Convierte valores a entero de forma segura"""
        try:
            return int(float(valor)) if str(valor).strip() else 0
        except (ValueError, TypeError):
            return 0

    def _limpiar(self):
        """Limpia los datos del procesamiento"""
        self._documento = None
        self._productos_existentes = None
        self._activo = False

    def detener(self):
        """Detiene el procesamiento de forma segura"""
        self._activo = False
        if self.thread.isRunning():
            self.thread.quit()
            if not self.thread.wait(1000):  # Esperar máximo 1 segundo
                self.thread.terminate()
                self.thread.wait(500)
        self._limpiar()

    # Métodos estáticos para acceso fácil al manager
    @staticmethod
    def create_managed_worker(owner_id: str = "default") -> str:
        """Crea un worker gestionado globalmente"""
        return ProcesadorArchivoManager.create_worker(owner_id)
    
    @staticmethod
    def connect_managed_signals(worker_id: str,
                              resultado_callback: Optional[Callable] = None,
                              error_callback: Optional[Callable] = None,
                              terminado_callback: Optional[Callable] = None):
        """Conecta señales a un worker gestionado"""
        ProcesadorArchivoManager.connect_worker_signals(
            worker_id, resultado_callback, error_callback, terminado_callback
        )
    
    @staticmethod
    def ejecutar_managed_processing(worker_id: str, documento: str, productos_existentes: list):
        """Ejecuta procesamiento en un worker gestionado"""
        ProcesadorArchivoManager.ejecutar_procesamiento(worker_id, documento, productos_existentes)
    
    @staticmethod
    def get_managed_worker(worker_id: str) -> Optional['ProcesadorArchivoWorker']:
        """Obtiene un worker gestionado"""
        return ProcesadorArchivoManager.get_worker(worker_id)
    
    @staticmethod
    def cleanup_managed_worker(worker_id: str):
        """Limpia un worker gestionado"""
        ProcesadorArchivoManager.cleanup_worker(worker_id)
    
    @staticmethod
    def cleanup_all_managed_workers():
        """Limpia todos los workers gestionados"""
        ProcesadorArchivoManager.cleanup_all_workers()
    
    @staticmethod
    def cleanup_owner_workers(owner_id: str):
        """Limpia workers de un owner específico"""
        ProcesadorArchivoManager.cleanup_owner_workers(owner_id)