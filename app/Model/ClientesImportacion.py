from datetime import datetime

from .BaseDatosModel import Clientes_fisicos, Clientes_morales, Categorias_de_clientes, Areas_negocios, Representantes_clientes_morales
from .ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales
from .AdministracionEntrada import validar_longitudes
from ..Controller.OperacionMasivaCsvController import OperacionMasivaCsvController as Lector


COMUNES = {
    "id", "nombre", "correo", "rfc", "telefono", "pais", "estado", "ciudad", "avenidas", "calles",
    "codigo_postal", "direccion_adicional", "entidad_legalizada", "categoria_cliente_id", "categoria_cliente",
    "categoria_id", "credito", "estado_credito", "limite_credito", "porcentaje_interes", "fecha_ultimo_reporte",
    "credito_disponible", "credito_utilizado", "aplica_descuento", "porcentaje_descuento", "comentarios",
    "areas_de_negocios_id", "area_de_negocio_id", "area_de_negocio", "areas_de_negocios",
    "clasificacion_cliente", "area de negocio", "area_id",
}
REQUERIDAS_COMUNES = ["nombre", "correo", "rfc", "telefono", "pais", "estado", "ciudad", "avenidas", "calles", "codigo_postal", "direccion_adicional"]
FISICAS = {"apellido_paterno", "apellido_materno", "curp", "fecha_nacimiento", "num_identificacion", "ocupacion", "ingresos", "estado_civil", "foto", "clasificacion cliente"}
MORALES = {"razon_social", "fecha_constitucion", "web", "sector", "nif", "NIF", "representante_nombre", "representante_telefono", "representante_correo", "representante_puesto", "descuento_autorizado", "clasificacion de cliente"}


class _DuplicadoFila(Exception):
    pass


class ClientesImportacion:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def columnas(tipo):
        extras = FISICAS if tipo == "FISICO" else MORALES
        requeridas = (["apellido_paterno", "apellido_materno", "curp", "fecha_nacimiento", "num_identificacion", "ocupacion", "ingresos", "estado_civil"]
                      if tipo == "FISICO" else ["razon_social", "fecha_constitucion", "web", "sector", "nif", "representante_nombre", "representante_telefono", "representante_correo", "representante_puesto"])
        return COMUNES | extras, REQUERIDAS_COMUNES + requeridas

    @staticmethod
    def valor(row, *aliases, default=""):
        for alias in aliases:
            if alias in row and str(row[alias]).strip():
                return row[alias]
        return default

    @staticmethod
    def booleano(valor):
        return str(valor).strip().lower() in {"1", "true", "t", "si", "s\u00ed", "yes", "y", "x", "verdadero"}

    def preparar(self, row, tipo):
        modelo = Clientes_fisicos if tipo == "FISICO" else Clientes_morales
        datos = {}
        for columna in modelo.__mapper__.columns:
            if getattr(columna.type, "length", None) or columna.key in {"foto", "comentarios", "direccion_adicional"}:
                if columna.key == "NIF":
                    valor = self.valor(row, "nif", "NIF")
                else:
                    valor = self.valor(row, columna.key)
                texto = str(valor).strip()
                datos[columna.key] = texto if columna.key in {"correo", "foto", "web"} else texto.upper()
        datos["tipo_cliente"] = tipo
        datos["credito"] = self.booleano(self.valor(row, "credito"))
        datos["entidad_legalizada"] = self.booleano(self.valor(row, "entidad_legalizada"))
        datos["aplica_descuento"] = self.booleano(self.valor(row, "aplica_descuento", "descuento_autorizado"))
        datos["estado_credito"] = datos["estado_credito"] or ("AUTORIZADO" if datos["credito"] else "SIN AUTORIZAR")
        cp = datos["codigo_postal"]
        if cp.endswith(".0") and cp[:-2].isdigit():
            cp = cp[:-2]
        datos["codigo_postal"] = cp.zfill(5) if cp.isdigit() and len(cp) < 5 else cp
        for campo in ("limite_credito", "porcentaje_interes", "credito_disponible", "credito_utilizado", "porcentaje_descuento") + (("ingresos",) if tipo == "FISICO" else ()):
            valor = self.valor(row, campo)
            numero = Lector.numero_con_reporte(valor)
            if numero["codigo"] not in {"valido", "vacio"}:
                raise ValueError(f"{campo}: numero invalido o no finito.")
            datos[campo] = numero["valor"] if numero["codigo"] == "valido" else (datos["limite_credito"] if campo == "credito_disponible" else 0.0)
        fecha = "fecha_nacimiento" if tipo == "FISICO" else "fecha_constitucion"
        datos[fecha] = Lector.parse_date(self.valor(row, fecha))
        ultimo = Lector.parse_date(self.valor(row, "fecha_ultimo_reporte"), default=datetime.now().date())
        datos["fecha_ultimo_reporte"] = datetime.combine(ultimo, datetime.min.time())
        obligatorios = ["nombre", "rfc", fecha] + (["apellido_paterno", "apellido_materno", "curp"] if tipo == "FISICO" else ["razon_social", "NIF"])
        if not all(datos[campo] for campo in obligatorios):
            raise ValueError("Faltan datos obligatorios o fecha valida.")
        validar_longitudes(modelo, datos)
        if tipo == "MORAL":
            datos["nif"] = datos.pop("NIF")
            representante = {campo: str(self.valor(row, f"representante_{campo}")).strip() for campo in ("nombre", "telefono", "correo", "puesto")}
            for campo in ("nombre", "telefono", "puesto"):
                representante[campo] = representante[campo].upper()
            validar_longitudes(Representantes_clientes_morales, representante)
            datos["datos_representante"] = representante
        return datos

    def resolver_catalogo(self, row, modelo, por_id, por_nombre, ids, nombres):
        valor_id = self.valor(row, *ids)
        try:
            identificador = int(valor_id)
        except (ValueError, TypeError):
            identificador = None
        if identificador in por_id:
            return identificador
        nombre = str(self.valor(row, *nombres)).strip().upper()
        if not nombre:
            raise ValueError("Falta categoria o area de negocio valida.")
        validar_longitudes(modelo, {"nombre": nombre})
        if nombre in por_nombre:
            return por_nombre[nombre]
        entidad = modelo(nombre=nombre, descripcion="CREADO POR IMPORTACION")
        self.session.add(entidad)
        self.session.flush()
        por_id[entidad.id] = entidad
        por_nombre[nombre] = entidad.id
        return entidad.id

    def importar_con_reporte(self, reporte, tipo):
        resultado = dict(exito=not reporte["errores"], tipo_cliente=tipo, agregados=0, duplicados=0, omitidos=0, reporte=reporte)
        if reporte["errores"]:
            return resultado
        categorias = self.session.query(Categorias_de_clientes).all()
        areas = self.session.query(Areas_negocios).all()
        categorias_id = {entidad.id: entidad for entidad in categorias}
        categorias_nombre = {entidad.nombre.strip().upper(): entidad.id for entidad in categorias}
        areas_id = {entidad.id: entidad for entidad in areas}
        areas_nombre = {entidad.nombre.strip().upper(): entidad.id for entidad in areas}
        columnas = ((Clientes_fisicos.curp, Clientes_fisicos.rfc) if tipo == "FISICO" else (Clientes_morales.razon_social, Clientes_morales.rfc, Clientes_morales.NIF))
        existentes = self.session.query(*columnas).all()
        claves = [set(str(fila[indice]).strip().upper() for fila in existentes if fila[indice]) for indice in range(len(columnas))]
        escritor = ClientesFisicosAndMorales(self.session)
        for origen in reporte["filas"]:
            row = origen["valores"]
            try:
                datos = self.preparar(row, tipo)
                for modelo, aliases in ((Categorias_de_clientes, ("categoria_cliente", "clasificacion_cliente", "clasificacion cliente", "clasificacion de cliente")),
                                        (Areas_negocios, ("area_de_negocio", "area de negocio", "areas_de_negocios"))):
                    nombre = str(self.valor(row, *aliases)).strip().upper()
                    if nombre:
                        validar_longitudes(modelo, {"nombre": nombre})
            except ValueError as error:
                reporte["errores"].append(dict(fila=origen["fila"], campo=None, codigo="entrada", mensaje=str(error)))
                resultado["omitidos"] += 1
                continue
            valores = (datos["curp"], datos["rfc"]) if tipo == "FISICO" else (datos["razon_social"], datos["rfc"], datos["nif"])
            if any(valor in conocidas for valor, conocidas in zip(valores, claves)):
                resultado["duplicados"] += 1
                reporte["advertencias"].append(dict(fila=origen["fila"], campo=None, codigo="duplicado", mensaje="Cliente duplicado omitido."))
                continue
            try:
                for ids, nombres, por_id, por_nombre in (
                    (("categoria_cliente_id", "categoria_id"), ("categoria_cliente", "clasificacion_cliente", "clasificacion cliente", "clasificacion de cliente"), categorias_id, categorias_nombre),
                    (("areas_de_negocios_id", "area_de_negocio_id", "area_id"), ("area_de_negocio", "area de negocio", "areas_de_negocios"), areas_id, areas_nombre),
                ):
                    valor_id = self.valor(row, *ids)
                    if not str(valor_id).isdigit() or int(valor_id) not in por_id:
                        if not self.valor(row, *nombres):
                            raise ValueError("Falta categoria o area de negocio valida.")
            except ValueError as error:
                reporte["errores"].append(dict(fila=origen["fila"], campo=None, codigo="catalogo", mensaje=str(error)))
                resultado["omitidos"] += 1
                continue
            categorias_fila_id, categorias_fila_nombre = dict(categorias_id), dict(categorias_nombre)
            areas_fila_id, areas_fila_nombre = dict(areas_id), dict(areas_nombre)
            try:
                with self.session.begin_nested():
                    datos["categoria_cliente_id"] = self.resolver_catalogo(row, Categorias_de_clientes, categorias_fila_id, categorias_fila_nombre, ("categoria_cliente_id", "categoria_id"), ("categoria_cliente", "clasificacion_cliente", "clasificacion cliente", "clasificacion de cliente"))
                    datos["areas_de_negocios_id"] = self.resolver_catalogo(row, Areas_negocios, areas_fila_id, areas_fila_nombre, ("areas_de_negocios_id", "area_de_negocio_id", "area_id"), ("area_de_negocio", "area de negocio", "areas_de_negocios"))
                    if tipo == "MORAL":
                        representante = escritor.agregar_representante_cliente_moral(**datos.pop("datos_representante"))
                        if representante is None:
                            raise RuntimeError("No se pudo persistir representante.")
                        datos["representante_id"] = representante.id
                    _, estado = getattr(escritor, "agregar_cliente_fisico" if tipo == "FISICO" else "agregar_cliente_moral")(**datos)
                    if estado is None:
                        raise _DuplicadoFila()
                    if estado is not True:
                        raise RuntimeError("No se pudo persistir cliente.")
            except _DuplicadoFila:
                resultado["duplicados"] += 1
                reporte["advertencias"].append(dict(fila=origen["fila"], campo=None, codigo="duplicado", mensaje="Cliente duplicado omitido."))
            except ValueError as error:
                resultado["omitidos"] += 1
                reporte["errores"].append(dict(fila=origen["fila"], campo=None, codigo="entrada", mensaje=str(error)))
            else:
                categorias_id, categorias_nombre = categorias_fila_id, categorias_fila_nombre
                areas_id, areas_nombre = areas_fila_id, areas_fila_nombre
                resultado["agregados"] += 1
                for valor, conocidas in zip(valores, claves):
                    conocidas.add(valor)
        return resultado