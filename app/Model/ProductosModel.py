from .BaseDatosModel import Productos, Presentacion_productos, Unidad_medida_productos, Movimientos_Inventario, Categorias_productos, Proveedores, Usuarios, ProductoProveedor
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import select, func
from .ProductoEntrada import validar_textos_producto
from dataclasses import dataclass
from .Proveedores_ProductosModel import sincronizar_proveedores_producto


@dataclass(frozen=True)
class CategoriaListadoDTO:
    id: int
    nombre: str
    descripcion: str
    tipo: str = "categoria_producto"


@dataclass(frozen=True)
class CatalogoListadoDTO:
    id: int
    nombre: str
    tipo: str


@dataclass(frozen=True)
class ProductoListadoDTO:
    id: int
    codigo_upc: str
    nombre_producto: str
    descripcion_producto: str
    precio: float
    existencia: float
    categoria: CategoriaListadoDTO | None
    marca: str = ""
    modelo: str = ""
    color: str = ""
    material: str = ""
    notas: str = ""
    imagen: str = ""
    costo_inicial: float = 0.0
    costo_final: float = 0.0
    margen_porcentaje: float = 0.0
    existencia_minima: float = 0.0
    existencia_maxima: float = 0.0
    peso: float = 0.0
    alto_cm: float = 0.0
    largo_cm: float = 0.0
    ancho_cm: float = 0.0
    fecha_fabricacion: object = None
    fecha_vencimiento: object = None
    categoria_id: int | None = None
    presentacion_producto_id: int | None = None
    unidad_medida_productos_id: int | None = None
    presentacion_productos: CatalogoListadoDTO | None = None
    unidad_medida_productos: CatalogoListadoDTO | None = None
    proveedores: tuple = ()

class ProductosModel:
    def __init__(self, session):
        self.session = session

    def codigos_upc_registrados(self):
        return {str(fila[0]).strip() for fila in self.session.query(Productos.codigo_upc).all()}

    def ids_catalogos_importacion(self):
        return {
            "presentacion_producto_id": {fila[0] for fila in self.session.query(Presentacion_productos.id).all()},
            "unidad_medida_productos_id": {fila[0] for fila in self.session.query(Unidad_medida_productos.id).all()},
            "categoria_id": {fila[0] for fila in self.session.query(Categorias_productos.id).all()},
        }

    def buscar_productos_dto(self, nombre, codigo, offset=0, limit=100):
        if bool(nombre) == bool(codigo):
            raise ValueError("Se requiere exactamente un filtro de producto")
        consulta = self.session.query(Productos).options(
            joinedload(Productos.categoria), joinedload(Productos.presentacion_productos),
            joinedload(Productos.unidad_medida_productos), selectinload(Productos.proveedores),
        )
        if nombre:
            consulta = consulta.filter(Productos.nombre_producto.ilike(f"%{nombre}%"))
        else:
            consulta = consulta.filter(Productos.codigo_upc == codigo)
        productos = consulta.order_by(Productos.nombre_producto.asc()).offset(offset).limit(limit).all()
        return [ProductoListadoDTO(
            id=producto.id, codigo_upc=producto.codigo_upc, nombre_producto=producto.nombre_producto,
            descripcion_producto=producto.descripcion_producto, precio=producto.precio,
            existencia=producto.existencia,
            categoria=CategoriaListadoDTO(producto.categoria.id, producto.categoria.nombre, producto.categoria.descripcion)
            if producto.categoria is not None else None,
            presentacion_productos=CatalogoListadoDTO(producto.presentacion_productos.id, producto.presentacion_productos.nombre, "presentacion_producto")
            if producto.presentacion_productos is not None else None,
            unidad_medida_productos=CatalogoListadoDTO(producto.unidad_medida_productos.id, producto.unidad_medida_productos.nombre, "unidad_medida_producto")
            if producto.unidad_medida_productos is not None else None,
            proveedores=tuple(CatalogoListadoDTO(proveedor.id, proveedor.nombre, "proveedor") for proveedor in producto.proveedores),
            **{campo: getattr(producto, campo) for campo in (
                "marca", "modelo", "color", "material", "notas", "imagen", "costo_inicial", "costo_final",
                "margen_porcentaje", "existencia_minima", "existencia_maxima", "peso", "alto_cm", "largo_cm",
                "ancho_cm", "fecha_fabricacion", "fecha_vencimiento", "categoria_id", "presentacion_producto_id",
                "unidad_medida_productos_id",
            )},
        ) for producto in productos]

    def _proveedores_ids(self, proveedores):
        identificadores = set()
        for proveedor in proveedores:
            identificador = proveedor.get("id") if isinstance(proveedor, dict) else proveedor.id
            if not isinstance(identificador, int) or isinstance(identificador, bool) or identificador <= 0:
                raise ValueError("proveedores: ID invalido")
            identificadores.add(identificador)
        return identificadores

    def _sincronizar_proveedores(self, producto, identificadores):
        sincronizar_proveedores_producto(producto, identificadores)

# // presentaciones de los productos:
    def insertar_unida_de_medida_basicas(self):
        query = select(Unidad_medida_productos).limit(1)
        resultado_consulta = self.session.execute(query).fetchone()
        if resultado_consulta is None:
            unidades_productos = [
                {"nombre": 'Sin unidad'},
                {"nombre": 'Kilogramo-(Kg)'},
                {"nombre": 'Gramo-(g)'},
                {"nombre": 'Litro-(L)'},
                {"nombre": 'Mililitro-(ml)'},
                {"nombre": 'Unidad-(u)'},
                {"nombre": 'Caja-(caj)'},
                {"nombre": 'Paquete-(paq)'},
                {"nombre": 'Docena-(dz)'},
                {"nombre": 'Pieza-(pza)'},
                {"nombre": 'Tetra pack-(Tetra)'},
                {"nombre": 'Sobre-(sob)'},
                {"nombre": 'Metro-(m)'},
                {"nombre": 'Centrimetro-(cm)'},
                {"nombre": 'Set-(set)'},
                {"nombre": 'Rol-(rol)'},
                {"nombre": 'Tarro-(tarro)'},
                {"nombre": 'Cilindro-(cil)'},
                {"nombre": 'Saco-(sac)'},
            ]

            self.session.execute(Unidad_medida_productos.__table__.insert(), unidades_productos)
            return True

    def insertar_categorias_basicas(self):
        query = select(Categorias_productos).limit(1)
        resultado_consulta = self.session.execute(query).fetchone()
        if resultado_consulta is None:
            categorias_productos = [
                {"nombre": 'Sin categoria', "descripcion": "Sin descripción"},
                {"nombre": 'Alimentos Perecederos', "descripcion": "Productos que requieren refrigeración, como carnes, pescados, lácteos, frutas y verduras frescas"},
                {"nombre": "Alimentos No Perecederos", "descripcion": "Comestibles que no requieren refrigeración, tales como arroz, pasta, galletas, sopas enlatadas, cereales, y otros productos empaquetados"},
                {"nombre": "Bebidas", "descripcion": "Refrescos, jugos, agua embotellada, bebidas energéticas, y también bebidas alcohólicas como cervezas, vinos, y licores"},
                {"nombre": "Productos de Panadería", "descripcion": "Pan, bollería, pasteles, galletas, y otros productos de panadería que se venden en tiendas de abarrotes"},
                {"nombre": "Congelados", "descripcion": "Alimentos congelados como pizzas, vegetales, carnes y postres helados"},
                {"nombre": "Comidas Preparadas", "descripcion": "Comidas listas para consumir como platos precocinados, ensaladas envasadas, y snacks de comida rápida"},
                {"nombre": "Herramientas Manuales", "descripcion": "Martillos, destornilladores, llaves inglesas, sierras, y otros instrumentos de mano"},
                {"nombre": "Herramientas Eléctricas", "descripcion": "Taladros, sierras eléctricas, lijadoras, y otros equipos que requieren energía para su funcionamiento"},
                {"nombre": "Materiales de Construcción", "descripcion": "Cemento, pintura, clavos, tornillos, maderas, y otros productos para la construcción y remodelación"},
                {"nombre": "Plomería", "descripcion": "Tuberías, grifos, llaves, selladores, y otros accesorios para trabajos de plomería"},
                {"nombre": "Iluminación", "descripcion": "Bombillos, lámparas, focos, linternas y otros productos relacionados con la iluminación"},
                {"nombre": "Accesorios de Jardinería", "descripcion": "Regaderas, fertilizantes, macetas, semillas y otros elementos para el cuidado de jardines"},
                {"nombre": "Snacks y Botanas", "descripcion": "Papas fritas, galletas, nueces, palomitas, y otros aperitivos envasados"},
                {"nombre": "Lácteos y Derivados", "descripcion": "Papas fritas, galletas, nueces, palomitas, y otros"},
                {"nombre": "Productos de Higiene Personal", "descripcion": "Jabón, shampoo, pasta dental, desodorante, toallas sanitarias y otros productos de cuidado personal"},
            ]

            self.session.execute(Categorias_productos.__table__.insert(), categorias_productos)
            return True

    def insertar_presentaciones_basicas(self):
        query = select(Presentacion_productos).limit(1)
        resultado_consulta = self.session.execute(query).fetchone()
        if resultado_consulta is None:
            presentaciones = [
                {"nombre": "Sin presentación"},
                {"nombre": "Unidad"},
                {"nombre": "Pieza"},
                {"nombre": "Paquete"},
                {"nombre": "Caja"},
                {"nombre": "Bolsa"},
                {"nombre": "Saco"},
                {"nombre": "Docena"},
                {"nombre": "Litro"},
                {"nombre": "Mililitro"},
                {"nombre": "Kilogramo"},
                {"nombre": "Gramo"},
                {"nombre": "Tarro"},
                {"nombre": "Tetra pack"},
                {"nombre": "Sobre"},
                {"nombre": "Frasco"},
                {"nombre": "Set"},
                {"nombre": "Rollo"},
                {"nombre": "Cilindro"},
                {"nombre": "Balde"},
                {"nombre": "Metro"},
                {"nombre": "Centímetro"},
                {"nombre": "Galón"},
                {"nombre": "Bidón"},
                {"nombre": "Blíster"},
                {"nombre": "Estuche"}
            ]

            self.session.execute(Presentacion_productos.__table__.insert(), presentaciones)
            return True

    def agregar_presentacion(self, nombre):
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 100:
            raise ValueError("nombre: presentacion requiere entre 1 y 100 caracteres")
        presentacion = self.session.query(Presentacion_productos).filter(Presentacion_productos.nombre == nombre).first()
        if presentacion is not None:
            return presentacion, False

        presentacion = Presentacion_productos(nombre = nombre)
        print(f"esta es la presentacion: {presentacion.nombre}")
        self.session.add(presentacion)
        self.session.flush()
        return presentacion, True

    def obtener_presentaciones(self):
        presentaciones = self.session.query(Presentacion_productos).all()
        if presentaciones:
            return presentaciones, True
        else:
            return [], False

    def eliminar_presentacion_producto(self, presentacion_obj):
        try:
            if presentacion_obj:
                self.session.delete(presentacion_obj)
                self.session.commit()
                return True
            return False
        except Exception as e:
            return False

    def agregar_unidad_medida(self, nombre):
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 100:
            raise ValueError("nombre: unidad de medida requiere entre 1 y 100 caracteres")
        unidad = self.session.query(Unidad_medida_productos).filter(Unidad_medida_productos.nombre == nombre).first()
        if unidad:
            return unidad, False
        unidad = Unidad_medida_productos(nombre = nombre)
        self.session.add(unidad)
        self.session.flush()
        return unidad, True

    def obtener_unidades_medida(self):
        unidades_medida = self.session.query(Unidad_medida_productos).all()
        if unidades_medida:
            return unidades_medida, True
        else:
            return [], False

    def eliminar_unidad_medida(self, unidad_obj):
        try:
            if unidad_obj:
                self.session.delete(unidad_obj)
                self.session.commit()
                return True
            return False
        except Exception as e:
            return False

    def agregar_producto(
        self,
        codigo_upc,
        nombre_producto,
        descripcion_producto,
        costo_inicial,
        costo_final,
        margen_porcentaje,
        precio,
        existencia,
        existencia_minima,
        existencia_maxima,
        marca,
        modelo,
        peso,
        alto_cm,
        largo_cm,
        ancho_cm,
        color,
        material,
        fecha_fabricacion,
        fecha_vencimiento,
        imagen,
        notas,
        presentacion_producto_id,
        unidad_medida_productos_id,
        categoria_id,
        sucursales,
        proveedores
        ):
        validar_textos_producto(
            codigo_upc=codigo_upc, nombre_producto=nombre_producto, marca=marca,
            modelo=modelo, color=color, material=material,
        )
        proveedores_ids = self._proveedores_ids(proveedores)
        try:
            producto = self.session.query(Productos).filter(Productos.codigo_upc == codigo_upc).first()
            if producto:
                return producto, False

            producto = Productos(
                codigo_upc=codigo_upc,
                nombre_producto=nombre_producto,
                descripcion_producto=descripcion_producto,
                costo_inicial=costo_inicial,
                costo_final=costo_final,
                margen_porcentaje = margen_porcentaje,
                precio=precio,
                existencia=existencia,
                existencia_minima=existencia_minima,
                existencia_maxima=existencia_maxima,
                marca=marca,
                modelo=modelo,
                peso=peso,
                alto_cm = alto_cm,
                largo_cm = largo_cm,
                ancho_cm = ancho_cm,
                color=color,
                material=material,
                fecha_fabricacion=fecha_fabricacion,
                fecha_vencimiento=fecha_vencimiento,
                imagen=imagen if imagen is not None else "",
                notas=notas,
                presentacion_producto_id=presentacion_producto_id,
                unidad_medida_productos_id=unidad_medida_productos_id,
                categoria_id=categoria_id,
                sucursales=sucursales
            )
            if not producto:
                return None, False
            self.session.add(producto)
            self._sincronizar_proveedores(producto, proveedores_ids)
            self.session.flush()
            return producto, True
        except Exception as e:
            raise

    def actualizar_producto(self,
                            id_producto,
                            codigo_upc,
                            nombre_producto,
                            descripcion_producto,
                            costo_inicial,
                            costo_final,
                            margen_porcentaje,
                            precio,
                            existencia,
                            existencia_minima,
                            existencia_maxima,
                            marca,
                            modelo,
                            peso,
                            alto_cm,
                            largo_cm,
                            ancho_cm,
                            color,
                            material,
                            fecha_fabricacion,
                            fecha_vencimiento,
                            imagen,
                            notas,
                            presentacion_producto_id,
                            unidad_medida_productos_id,
                            categoria_id,
                            sucursales,
                            proveedores
                        ):
        validar_textos_producto(
            codigo_upc=codigo_upc, nombre_producto=nombre_producto, marca=marca,
            modelo=modelo, color=color, material=material,
        )
        proveedores_ids = self._proveedores_ids(proveedores)
        producto_actual = self.session.get(Productos, id_producto)
        if not producto_actual:
            return None, False

        producto_actual.nombre_producto = nombre_producto
        producto_actual.descripcion_producto = descripcion_producto
        producto_actual.costo_inicial = costo_inicial
        producto_actual.costo_final = costo_final
        producto_actual.margen_porcentaje = margen_porcentaje
        producto_actual.precio = precio
        producto_actual.existencia = existencia
        producto_actual.existencia_minima = existencia_minima
        producto_actual.existencia_maxima = existencia_maxima
        producto_actual.marca = marca
        producto_actual.modelo = modelo
        producto_actual.peso = peso
        producto_actual.alto_cm = alto_cm
        producto_actual.largo_cm = largo_cm
        producto_actual.ancho_cm = ancho_cm
        producto_actual.color = color
        producto_actual.material = material
        producto_actual.fecha_fabricacion = fecha_fabricacion
        producto_actual.fecha_vencimiento = fecha_vencimiento
        producto_actual.imagen = (producto_actual.imagen or "") if imagen is None else imagen
        producto_actual.notas = notas
        producto_actual.presentacion_producto_id = presentacion_producto_id
        producto_actual.unidad_medida_productos_id = unidad_medida_productos_id
        producto_actual.categoria_id = categoria_id
        # producto_actual.sucursales = sucursales
        self._sincronizar_proveedores(producto_actual, proveedores_ids)

        return producto_actual, True

    def obtener_productos(self, offset=0, limit=100):
        try:
            productos = (
                self.session.query(Productos)
                .options(
                    joinedload(Productos.producto_proveedor_asociaciones),
                    joinedload(Productos.categoria),
                    joinedload(Productos.unidad_medida_productos),
                    joinedload(Productos.presentacion_productos),
                    joinedload(Productos.proveedores)
                )
                .order_by(Productos.nombre_producto.asc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            if not productos and offset > 0:
                return [], False

            return productos, bool(productos)

        except Exception as e:
            return [], False

    def eliminar_producto(self, codigo_producto):
        producto = self.session.query(Productos).filter(Productos.codigo_upc == codigo_producto).first()
        if producto:
            self.session.delete(producto)
            self.session.commit()
            return None, True
        else:
            return None, False

    def consultar_por_nombre_exacto(self, nombre, cantidad_inicial=0, cantidad_final=100):
        try:
            productos = (
                self.session.query(Productos)
                .options(
                    joinedload(Productos.producto_proveedor_asociaciones),
                    joinedload(Productos.categoria),
                    joinedload(Productos.unidad_medida_productos),
                    joinedload(Productos.presentacion_productos),
                    joinedload(Productos.proveedores)
                )
                .filter(func.lower(Productos.nombre_producto) == func.lower(nombre))
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            if not productos:
                return [], False

            return productos, bool(productos)

        except Exception as e:
            return [], False

    def consultar_por_nombre(self, nombre, cantidad_inicial=0, cantidad_final=100):
        try:
            productos = (
                self.session.query(Productos)
                .options(
                    joinedload(Productos.producto_proveedor_asociaciones),
                    joinedload(Productos.categoria),
                    joinedload(Productos.unidad_medida_productos),
                    joinedload(Productos.presentacion_productos),
                    joinedload(Productos.proveedores)
                )
                .filter(Productos.nombre_producto.ilike(f"%{nombre}%"))
                .order_by(Productos.nombre_producto.asc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            if not productos and cantidad_inicial > 0:
                return [], False

            return productos, bool(productos)

        except Exception as e:
            return [], False

    def consultar_producto_por_codigoUPC(self, codigo_upc):
        produto = self.session.query(Productos)\
            .options(
                joinedload(Productos.producto_proveedor_asociaciones),
                joinedload(Productos.proveedores),
                joinedload(Productos.categoria),
                joinedload(Productos.unidad_medida_productos),
                joinedload(Productos.presentacion_productos)
            ).filter(Productos.codigo_upc == codigo_upc).first()
        if produto:
            return produto, True
        else:
            return None, False

    def ejecutar_movimiento(self, producto_id, cantidad_cambio, tipo_movimiento, fecha_movimiento, notas, usuarioid):
        if not producto_id or not usuarioid:
            return None, False
        if self.session.get(Usuarios, usuarioid) is None:
            return None, False
        producto = self.session.get(Productos, producto_id)
        if not producto:
            return None, False
        movimiento = Movimientos_Inventario(
            producto_id = producto.id,
            cantidad_cambio = cantidad_cambio,
            tipo_movimiento = tipo_movimiento,
            fecha_movimiento = fecha_movimiento,
            notas = notas,
            usuario_id = usuarioid
            )


        if tipo_movimiento.lower() == "entrada":
            producto.existencia += cantidad_cambio
        elif tipo_movimiento.lower() == "salida":
            producto.existencia -= cantidad_cambio

        self.session.add(movimiento)
        self.session.flush()
        return movimiento, True