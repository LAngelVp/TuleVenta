from sqlalchemy.orm import joinedload
from sqlalchemy import select, func
from .BaseDatosModel import (Proveedores, Categorias_proveedores, Representantes_proveedores,
                             Productos, ProductoProveedor, NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
import logging
from collections import namedtuple
from .Proveedores_ProductosModel import sincronizar_proveedores_producto

ProveedorListadoDTO = namedtuple("ProveedorListadoDTO", [columna.name for columna in Proveedores.__table__.columns] + ["categoria", "representante"])
RepresentanteListadoDTO = namedtuple("RepresentanteListadoDTO", [columna.name for columna in Representantes_proveedores.__table__.columns])
CategoriaProveedorDTO = namedtuple("CategoriaProveedorDTO", "id nombre descripcion tipo")


def proveedor_snapshot(proveedor):
    categoria = proveedor.categoria
    representante = proveedor.representante
    return ProveedorListadoDTO(
        **{columna.name: getattr(proveedor, columna.name) for columna in Proveedores.__table__.columns},
        categoria=CategoriaProveedorDTO(categoria.id, categoria.nombre, categoria.descripcion, "categoria_proveedor") if categoria else None,
        representante=RepresentanteListadoDTO(**{columna.name: getattr(representante, columna.name)
                                                for columna in Representantes_proveedores.__table__.columns}) if representante else None
    )


def es_proveedor_compra_directa(proveedor):
    if proveedor is None:
        return False
    nombre = getattr(proveedor, "nombre", proveedor)
    return str(nombre or "").strip().upper() == NOMBRE_PROVEEDOR_COMPRA_DIRECTA

def validar_textos_proveedor(entidad, valores):
    for columna in entidad.__table__.columns:
        if columna.name not in valores:
            continue
        limite = getattr(columna.type, "length", None)
        if limite:
            valor = valores[columna.name]
            if not isinstance(valor, str) or len(valor) > limite:
                raise ValueError(f"{columna.name}: maximo {limite} caracteres")

class ProveedoresModel:
    def __init__(self, session):
        self.session = session

    def listar_dto(self, offset=0, limit=100, texto=None):
        consulta = self.session.query(Proveedores).options(joinedload(Proveedores.categoria), joinedload(Proveedores.representante))
        consulta = consulta.filter(Proveedores.nombre != NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
        if texto is not None:
            consulta = consulta.filter(Proveedores.nombre.ilike(f"%{texto}%"))
        proveedores = consulta.order_by(Proveedores.nombre.asc()).offset(offset).limit(limit).all()
        return [proveedor_snapshot(proveedor) for proveedor in proveedores], bool(proveedores)

    def obtener_o_crear_proveedor_compra_directa(self):
        """Devuelve el proveedor reservado para compras directas, creandolo si no existe."""
        try:
            proveedor = (self.session.query(Proveedores)
                         .filter(Proveedores.nombre == NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
                         .first())
            if proveedor is not None:
                return proveedor, False
            proveedor = Proveedores(
                nombre=NOMBRE_PROVEEDOR_COMPRA_DIRECTA,
                pais="", estado="", ciudad="", codigo_postal="",
                calles="", avenidas="", colonia="", direccion_adicional="",
                rfc="", pagina_web="", correo="", telefono="",
                clave_moneda="", tipo_moneda="",
                representante_id=None, categoria_id=None,
            )
            self.session.add(proveedor)
            self.session.flush()
            return proveedor, True
        except Exception:
            return None, False

    def categorias_dto(self):
        categorias = self.session.query(Categorias_proveedores).all()
        return [CategoriaProveedorDTO(categoria.id, categoria.nombre, categoria.descripcion, "categoria_proveedor")
                for categoria in categorias], bool(categorias)

    def importar_con_reporte(self, reporte, estricto=False):
        resultado = {"exito": False, "agregados": 0, "duplicados": 0,
                     "invalidos": 0, "proveedores_duplicados": [], "reporte": reporte}
        if reporte["errores"]:
            return resultado
        try:
            categorias = {fila[0] for fila in self.session.query(Categorias_proveedores.id).all()}
            representantes = {fila[0] for fila in self.session.query(Representantes_proveedores.id).all()}
            nombres = {str(fila[0]).strip().lower() for fila in self.session.query(Proveedores.nombre).all() if fila[0]}
            rfcs = {str(fila[0]).strip().upper() for fila in self.session.query(Proveedores.rfc).all() if fila[0]}
            campos = [columna.name for columna in Proveedores.__table__.columns
                      if columna.name not in ("id", "categoria_id", "representante_id")]
            for origen in reporte["filas"]:
                fila = origen["valores"]
                if str(fila.get("id", "")).strip():
                    reporte["advertencias"].append({"fila": origen["fila"], "campo": "id",
                                                    "codigo": "id_ignorado", "mensaje": "El ID del archivo no se utiliza"})
                datos = {campo: str(fila.get(campo, "")).strip() for campo in campos}
                datos["rfc"] = datos["rfc"].upper()
                try:
                    if not datos["nombre"]:
                        raise ValueError("nombre: es obligatorio")
                    validar_textos_proveedor(Proveedores, datos)
                except ValueError as error:
                    resultado["invalidos"] += 1
                    reporte["errores"].append({"fila": origen["fila"], "campo": str(error).split(":")[0],
                                               "codigo": "entrada_invalida", "mensaje": str(error)})
                    continue
                nombre = datos["nombre"].lower()
                if nombre in nombres or (datos["rfc"] and datos["rfc"] in rfcs):
                    resultado["duplicados"] += 1
                    resultado["proveedores_duplicados"].append(datos["nombre"])
                    reporte["advertencias"].append({"fila": origen["fila"], "campo": "nombre/rfc",
                                                    "codigo": "duplicado", "mensaje": "Fila duplicada omitida"})
                    continue
                for campo, existentes in (("categoria_id", categorias), ("representante_id", representantes)):
                    valor = fila.get(campo, "")
                    try:
                        identificador = int(str(valor).strip()) if str(valor).strip() else None
                    except (ValueError, TypeError):
                        identificador = None
                    datos[campo] = identificador if identificador in existentes else None
                    if str(valor).strip() and datos[campo] is None:
                        reporte["advertencias"].append({"fila": origen["fila"], "campo": campo,
                                                        "codigo": "fk_omitida", "mensaje": "Referencia desconocida omitida"})
                self.session.add(Proveedores(**datos))
                self.session.flush()
                nombres.add(nombre)
                if datos["rfc"]:
                    rfcs.add(datos["rfc"])
                resultado["agregados"] += 1
            resultado["exito"] = True
            resultado["codigo"] = "importado" if resultado["agregados"] else "sin_cambios"
        except Exception:
            if estricto:
                raise
            self.session.rollback()
            resultado["agregados"] = 0
            reporte["errores"].append({"fila": None, "campo": None, "codigo": "persistencia",
                                       "mensaje": "No se confirmo el lote por un error de persistencia"})
        return resultado


    def insertar_categoria_proveedor_basicas(self):
        query = select(Categorias_proveedores).limit(1)
        resultado_consulta = self.session.execute(query).fetchone()
        if resultado_consulta is None:
            categorias_proveedor = [
                {"nombre": 'Bebidas Alcohólicas', "descripcion": "Proveedores que distribuyen cervezas, vinos, tequilas y mezcales, tanto nacionales como internacionales, en diferentes presentaciones. Sus productos son clave en la industria de bebidas para restaurantes, tiendas y supermercados, ofreciendo opciones variadas en calidad y presentación"},
                {"nombre": 'Bebidas No Alcohólicas', "descripcion": "Proveedores que comercializan refrescos, jugos, agua embotellada y bebidas energéticas. Estas marcas están presentes en el mercado ofreciendo productos refrescantes y saludables, con opciones en diferentes sabores y fórmulas, disponibles en varios tamaños y presentaciones"},
                {"nombre": 'Productos Lácteos', "descripcion": "Proveedores que ofrecen leche, yogurt, queso, crema y mantequilla. Estos productos son esenciales en la canasta básica mexicana, garantizando calidad en la producción y distribución en tiendas, supermercados y puntos de venta"},
                {"nombre": 'Alimentos Empacados', "descripcion": "Proveedores que distribuyen productos alimenticios como pan, galletas, cereales, alimentos congelados, sopas, entre otros. Estos productos están disponibles en tiendas de abarrotes, supermercados y puntos de venta especializados, ofreciendo conveniencia y variedad al consumidor"},
                {"nombre": 'Snacks y Botanas', "descripcion": "Proveedores de botanas saladas y dulces, como papas fritas, galletas, nachos y otros aperitivos. Este sector es popular en tiendas de abarrotes, gasolineras y supermercados, proporcionando opciones de snack para diferentes gustos"},
                {"nombre": 'Productos de Higiene y Cuidado Personal', "descripcion": "Proveedores de artículos para la higiene personal, como jabones, champús, cremas, desodorantes y toallas sanitarias. Estos productos son esenciales para el bienestar y cuidado diario, y están disponibles en tiendas y grandes cadenas de distribución"},
                {"nombre": 'Productos de Limpieza', "descripcion": "Proveedores de productos para limpieza del hogar y oficina, como detergentes, desinfectantes, limpiadores multiusos, blanqueadores, entre otros. Estos productos cubren todas las necesidades de limpieza, desde productos para pisos hasta limpieza de superficies"},
                {"nombre": 'Tecnología y Electrónica', "descripcion": "Proveedores de dispositivos electrónicos como computadoras, smartphones, televisores, cámaras y accesorios tecnológicos. Estas empresas ofrecen productos innovadores, siendo esenciales tanto para el hogar como para el ámbito profesional"},
                {"nombre": 'Ferretería y Herramientas', "descripcion": "Proveedores que ofrecen herramientas manuales y eléctricas, materiales de construcción, pinturas, tornillos y otros suministros para proyectos domésticos o industriales. Están presentes en tiendas especializadas y cadenas de ferreterías, ofreciendo productos de alta calidad"},
                {"nombre": 'Automotriz y Repuestos', "descripcion": "Proveedores de autopartes y accesorios para vehículos, como frenos, aceites, filtros, llantas y herramientas automotrices. Estos proveedores garantizan la disponibilidad de repuestos y accesorios necesarios para mantener y reparar vehículos en talleres, distribuidores y tiendas especializadas"},
                {"nombre": 'Ropa y Calzado', "descripcion": "Proveedores que ofrecen ropa y calzado para hombres, mujeres y niños, incluyendo desde ropa casual hasta deportiva, formal y accesorios de moda. Estos productos están disponibles en tiendas de moda, grandes almacenes y comercios en línea"},
                {"nombre": 'Muebles y Decoración', "descripcion": "Proveedores que ofrecen muebles para el hogar, oficina y jardín, como sofás, mesas, camas, sillas y artículos decorativos. Estos productos buscan combinar estética y funcionalidad, y son distribuidos en grandes almacenes y tiendas de decoración"},
                {"nombre": 'Herramientas y Material de Construcción', "descripcion": "Proveedores de materiales para la construcción, como cemento, bloques, varilla, y herramientas como martillos, sierras y taladros. Estos productos son fundamentales para proyectos de obra, desde pequeños proyectos en el hogar hasta grandes desarrollos inmobiliarios"},
                {"nombre": 'Productos para Mascotas', "descripcion": "Proveedores de alimentos, juguetes, accesorios, camas, y artículos de cuidado para mascotas como perros, gatos, aves, entre otros. Estos productos están disponibles en tiendas especializadas y grandes cadenas, atendiendo las necesidades de los dueños de mascotas"},
                {"nombre": 'Artículos de Oficina', "descripcion": "Proveedores que distribuyen productos para oficina como papelería, mobiliario, equipos de computo y accesorios. Estos artículos son necesarios tanto para oficinas corporativas como para el hogar, ayudando a optimizar el trabajo diario con calidad y funcionalidad"},
            ]

            self.session.execute(Categorias_proveedores.__table__.insert(), categorias_proveedor)
            # self.session.commit()
            return True

    def agregar_proveedor(self,
                        categoria_id,
                        representante_id,
                        nombre,
                        pais,
                        estado,
                        ciudad,
                        codigo_postal,
                        calles,
                        avenidas,
                        colonia,
                        direccion_adicional,
                        rfc,
                        pagina_web,
                        correo,
                        telefono,
                        clave_moneda,
                        tipo_moneda,
                        estricto=False
                        ):
        if estricto:
            validar_textos_proveedor(Proveedores, locals())
            if not nombre.strip() or categoria_id is None:
                raise ValueError("nombre/categoria: son obligatorios")
        if str(nombre or "").strip().upper() == NOMBRE_PROVEEDOR_COMPRA_DIRECTA:
            return None, False
        try:
            proveedor = self.session.query(Proveedores).filter_by(nombre=nombre).first()
            if proveedor:
                return proveedor, False  # Proveedor ya existe, no agregarlo

            nuevo_proveedor = Proveedores(
                nombre=nombre,
                pais=pais,
                estado=estado,
                ciudad=ciudad,
                codigo_postal=codigo_postal,
                calles=calles,
                avenidas=avenidas,
                colonia=colonia,
                direccion_adicional=direccion_adicional,
                rfc=rfc,
                pagina_web=pagina_web,
                correo=correo,
                telefono=telefono,
                clave_moneda=clave_moneda,
                tipo_moneda=tipo_moneda,
                representante_id=representante_id,
                categoria_id=categoria_id
            )

            if representante_id:
                try:
                    representante = self.session.query(Representantes_proveedores).filter(
                        Representantes_proveedores.id == representante_id).first()
                    if representante:
                        nuevo_proveedor.representante = representante
                except Exception as e:
                    if estricto:
                        raise
                    self.session.rollback()
                    # Agregar el mensaje de error para el rollback
                    logging.error(f"Error al agregar representante: {e}")

            self.session.add(nuevo_proveedor)
            self.session.flush()
            return nuevo_proveedor, True  # Si todo va bien, devolver el nuevo proveedor y un estado True
        except Exception as e:
            if estricto:
                raise
            # Asegúrate de devolver siempre una tupla, incluso cuando hay un error
            logging.error(f"Error al agregar proveedor: {e}")
            return None, False  # Devolver None y False si hay un error

    def obtener_proveedor_id(self, id):
        try:
            proveedor = self.session.query(Proveedores).get(id)
            if proveedor is None:
                return proveedor, False
            else:
                return proveedor, True
        except Exception as e:
            return None

    def obtener_proveedores(self, offset=0, limit=100):
        proveedores = (self.session.query(Proveedores).options(
            joinedload(Proveedores.categoria),  # Carga anticipada de las categorías
            joinedload(Proveedores.producto_proveedor_asociaciones),   # Carga anticipada de los productos
            joinedload(Proveedores.representante),  # Carga anticipada del representante
            joinedload(Proveedores.compras)  # Carga anticipada de las compras
        )
        .filter(Proveedores.nombre != NOMBRE_PROVEEDOR_COMPRA_DIRECTA)
        .order_by(Proveedores.nombre.asc())
        .offset(offset)
        .limit(limit)
        .all()
        )
        if len(proveedores) > 0:
            return proveedores, True
        else:
            return  None, False

    def obtener_nombre_proveedor(self, texto, offset=0, limit=100):
        texto_busqueda = f"%{texto}%"
        # Realizar la consulta utilizando ilike() para búsqueda insensible a mayúsculas
        proveedores = self.session.query(Proveedores).options(
            joinedload(Proveedores.categoria),  # Carga anticipada de las categorías
            joinedload(Proveedores.producto_proveedor_asociaciones),   # Carga anticipada de los productos
            joinedload(Proveedores.representante),  # Carga anticipada del representante
            joinedload(Proveedores.compras)  # Carga anticipada de las compras
        ).filter(
            Proveedores.nombre != NOMBRE_PROVEEDOR_COMPRA_DIRECTA,
            Proveedores.nombre.ilike(texto_busqueda),
        ).order_by(Proveedores.nombre.asc()).offset(offset).limit(limit).all()
        if len(proveedores) > 0:
            return proveedores, True
        return [], False

    def actualizar_proveedor(self,
                            proveedor_id,
                            categoria_id,
                            representante_id,
                            nombre,
                            pais,
                            estado,
                            ciudad,
                            codigo_postal,
                            calles,
                            avenidas,
                            colonia,
                            direccion_adicional,
                            rfc,
                            pagina_web,
                            correo,
                            telefono,
                            clave_moneda,
                            tipo_moneda,
                            estricto=False
                            ):
        if estricto:
            validar_textos_proveedor(Proveedores, locals())
            if not nombre.strip() or categoria_id is None:
                raise ValueError("nombre/categoria: son obligatorios")
        try:
            # Buscar el proveedor por ID

            proveedor = self.session.query(Proveedores).get(proveedor_id)
            if not proveedor:
                return None, False
            if es_proveedor_compra_directa(proveedor) or str(nombre or "").strip().upper() == NOMBRE_PROVEEDOR_COMPRA_DIRECTA:
                return None, False

            # Actualizar los atributos del proveedor
            proveedor.nombre = nombre
            proveedor.pais = pais
            proveedor.estado = estado
            proveedor.ciudad = ciudad
            proveedor.codigo_postal = codigo_postal
            proveedor.calles = calles
            proveedor.avenidas = avenidas
            proveedor.colonia = colonia
            proveedor.direccion_adicional = direccion_adicional
            proveedor.rfc = rfc
            proveedor.pagina_web = pagina_web
            proveedor.correo = correo
            proveedor.telefono = telefono
            proveedor.clave_moneda = clave_moneda
            proveedor.tipo_moneda = tipo_moneda

            # Actualizar la categoría si se proporciona
            if categoria_id is None:
                return None, False

            try:
                categoria = self.session.query(Categorias_proveedores).get(categoria_id)
                if estricto and categoria is None:
                    raise ValueError("categoria: no existe")
                if categoria:
                    # Limpiar las categorías existentes y agregar la nueva
                    proveedor.categoria = categoria
            except Exception as e:
                if estricto:
                    raise
                self.session.rollback()
                return None, False

            # Actualizar el representante si se proporciona
            if representante_id is None:
                # Si no se proporciona representante_id, eliminar los representantes existentes
                proveedor.representante = None
            try:
                representante = self.session.get(Representantes_proveedores, representante_id) if representante_id is not None else None
                if estricto and representante_id is not None and representante is None:
                    raise ValueError("representante: no existe")
                if representante:
                    proveedor.representante = representante
            except Exception as e:
                if estricto:
                    raise
                self.session.rollback()
                return None, False

            return proveedor, True  # Retorna el ID del proveedor actualizado
        except Exception as e:
            if estricto:
                raise
            self.session.rollback()  # Hacer rollback en caso de error
            logging.error(f"Error al agregar proveedor: {e}")
            return None

    def consultar_proveedor(self, nombre):
        try:
            if nombre is None:
                return None, False
            proveedor = self.session.query(Proveedores).filter(Proveedores.nombre == nombre).first()
            if proveedor is None:
                return proveedor, False
            else:
                return proveedor, True
        except Exception as e:
            return None, False

    def eliminar_proveedor(self, id, estricto=False):
        try:
            proveedor = self.session.get(Proveedores, id)
            if proveedor:
                if es_proveedor_compra_directa(proveedor):
                    return None, False
                self.session.delete(proveedor)
                return None, True
            else:
                return False, False
        except Exception as e:
            if estricto:
                raise
            return None, False

    def filtrar_productos_del_proveedor_exacto_nombre(self, proveedor_id, nombre, cantidad_inicial=0, cantidad_final=100):
        try:
            productos = (
                self.session.query(ProductoProveedor)
                .options(joinedload(ProductoProveedor.producto))
                .join(ProductoProveedor.producto)
                .join(ProductoProveedor.proveedor)
                .filter(
                    func.lower(Productos.nombre_producto) == func.lower(nombre),
                    Proveedores.id == proveedor_id
                )
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            if productos:
                return productos, True
            else:
                return [], False

        except Exception as e:
            print(f"Error al filtrar productos exactos: {e}")
            return [], False

    def filtrar_productos_del_proveedor_contenga_nombre(self, proveedor_id, nombre, cantidad_inicial=0, cantidad_final=100):
        try:
            productos = (
                self.session.query(ProductoProveedor)
                .options(joinedload(ProductoProveedor.producto))
                .join(ProductoProveedor.producto)
                .join(ProductoProveedor.proveedor)
                .filter(
                    Productos.nombre_producto.ilike(f"%{nombre}%"),
                    Proveedores.id == proveedor_id
                )
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            if productos:
                return productos, True
            else:
                return [], False

        except Exception as e:
            print(f"Error al filtrar productos que contengan nombre: {e}")
            return [], False

    def actualizar_productos_al_proveedor(self, proveedor_id, lista_productos, confirmar=True):
        if not confirmar:
            return self._vincular_productos(proveedor_id, lista_productos)
        try:
            resultado, estado = self._vincular_productos(proveedor_id, lista_productos)
            if estado:
                self.session.commit()
            return resultado, estado
        except Exception:
            self.session.rollback()
            return [], False

    def _vincular_productos(self, proveedor_id, lista_productos):
        if not lista_productos or not proveedor_id:
            return [], False
        proveedor = self.session.query(Proveedores).filter_by(id=proveedor_id).first()
        if proveedor is None:
            return [], False
        identificadores = {producto.id for producto in lista_productos}
        if any(not isinstance(identificador, int) or isinstance(identificador, bool) or identificador <= 0
               for identificador in identificadores):
            raise ValueError("Producto invalido")
        productos = [self.session.get(Productos, identificador) for identificador in identificadores]
        if any(producto is None for producto in productos):
            return [], False
        for producto in productos:
            sincronizar_proveedores_producto(producto, {proveedor_id}, reemplazar=False)
        return proveedor, True

