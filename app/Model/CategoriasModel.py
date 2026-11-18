from .BaseDatosModel import Categorias_productos, Categorias_de_clientes, Categorias_proveedores
from ..Controller.MensajesAlertasController import Mensaje
from sqlalchemy import select
class CategoriasModel:
    def __init__(self, session):
        self.session = session
        
    def agregar(self, tipo_categoria, nombre, descripcion = None):
        if tipo_categoria == "proveedores":
            if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 150:
                raise ValueError("nombre: categoria de proveedor requiere entre 1 y 150 caracteres")
            if not isinstance(descripcion, str) or not descripcion.strip():
                raise ValueError("descripcion: es obligatoria")
        if tipo_categoria == "productos":
            if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 100:
                raise ValueError("nombre: categoria de producto requiere entre 1 y 100 caracteres")
            if not isinstance(descripcion, str) or not descripcion.strip():
                raise ValueError("descripcion: es obligatoria")
        if tipo_categoria == "clientes":
            if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 100:
                raise ValueError("nombre: categoria de cliente requiere entre 1 y 100 caracteres")
            if not isinstance(descripcion, str) or not descripcion.strip() or len(descripcion) > 255:
                raise ValueError("descripcion: categoria de cliente requiere entre 1 y 255 caracteres")
        modelo = self.__tipo_categoria(tipo_categoria)
        categoria = self.session.scalar(select(modelo).where(modelo.nombre == nombre))
        if categoria is not None:
            return categoria, False
        categoria = modelo(nombre=nombre, descripcion=descripcion)
        self.session.add(categoria)
        self.session.flush()
        return categoria, True
    
    def obtener_todo(self, tipo_categoria):
        modelo = self.__tipo_categoria(tipo_categoria)
        categorias = self.session.query(modelo).all()
        if not categorias:
            return [], False
        return categorias, True
    
    def obtener_id_por_nombre(self, tipo_categoria, nombre):
        modelo = self.__tipo_categoria(tipo_categoria)
        try:
            categoria = self.session.query(modelo).filter_by(nombre=nombre).first()
            return categoria.id
        except Exception as e:
            return None
        
    def obtener_categoria_por_id(self, tipo_categoria, id):
        modelo = self.__tipo_categoria(tipo_categoria)
        try:
            categoria = self.session.query(modelo).filter_by(id == id).first()
            if categoria:
                return categoria
            else:
                return None
        except Exception as e:
            Mensaje().mensaje_critico(f'Error al obtener categoría por id: {e}')
    
    def eliminar(self, categoria_obj, estricto=False):
        # modelo = self.__tipo_categoria(tipo_categoria)
        try:
            if getattr(categoria_obj, "tipo", None) == "categoria_proveedor":
                categoria_obj = self.session.get(Categorias_proveedores, categoria_obj.id)
                if categoria_obj is None:
                    return False
            self.session.delete(categoria_obj)
            return True
        except Exception as e:
            if estricto:
                raise
            return False

    def __tipo_categoria(self, tipo_categoria):
        if tipo_categoria == 'productos':
            return Categorias_productos
        elif tipo_categoria == 'clientes':
            return Categorias_de_clientes
        elif tipo_categoria == 'proveedores':
            return Categorias_proveedores
        return None