from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from .BaseDatosModel import Permisos, Roles, Usuarios, rol_permiso

class PermisosModel:
    def __init__(self,session):
        self.session = session
        self.lista_permisos = [
                'administrador',
                'crearventa', 'eliminarventa', 'modificarventa',
                'crearcompra', 'eliminarcompra', 'modificarcompra',
                'crearproducto', 'eliminarproducto', 'modificarproducto',
                'crearempleado', 'eliminarempleado', 'modificarempleado',
                'crearproveedor', 'eliminarproveedor', 'modificarproveedor',
                'crearcliente', 'eliminarcliente', 'modificarcliente',
                'crearsucursal', 'eliminarsucursal', 'modificarsucursal',
                'creardepartamento', 'eliminardepartamento', 'modificardepartamento',
                'crearpuestos', 'eliminarpuesto', 'modificarpuesto',
                'creargrupopermisos', 'eliminargrupopermisos', 'modificargrupopermisos',
                'creartrasacciones', 'eliminartransacciones', 'modificartransacciones',
                'crearturnos', 'eliminarturnos', 'modificarturnos',
                'crearusuarios', 'eliminarusuarios', 'modificarusuarios'
        ]
    @property
    def crear_permisos_principal(self):
        # Verificar si los permisos ya existen en la base de datos
        permisos_existentes = self.session.query(Permisos.nombre).filter(Permisos.nombre.in_([p.upper() for p in self.lista_permisos])).all()
        permisos_existentes = set([p[0] for p in permisos_existentes])  # Convertir a set para eficiencia en las búsquedas

        # Añadir solo los permisos que no existen
        for permiso in self.lista_permisos:
            permiso_upper = permiso.upper()
            if permiso_upper not in permisos_existentes:
                permiso_creado = Permisos(nombre=permiso_upper)
                self.session.add(permiso_creado)

    def buscar_por_nombre(self, nombre):
        if nombre is not None:
            permiso = self.session.query(Permisos).filter_by(nombre=nombre.upper()).first()
            if permiso:
                return permiso, True
        return None, False

class RolesModel:
    def __init__(self, session):
        self.session = session
        self.rol_propietario = {
            'nombre' : 'administrador',
            'descripcion' :  'Administrador del sistema',
            'permisos' : 'administrador'
        }
    @property
    def crear_grupo_principal(self):
        try:
            rol_principal = self.session.query(Roles).filter_by(nombre = self.rol_propietario['nombre'].upper()).first()
            if not rol_principal:
                rol_creado = Roles(nombre = self.rol_propietario['nombre'].upper(),
                                descripcion = self.rol_propietario['descripcion'].upper(),
                                )
                permiso, estadoPermiso = PermisosModel(self.session).buscar_por_nombre(self.rol_propietario['permisos'].upper())
                if estadoPermiso:
                    rol_creado.permisos.append(permiso)
                self.session.add(rol_creado)
            self.session.flush()
            return True
        except Exception as e:
            return False

    def crear_Rol(self, nombre, descripcion = None, permisos=None):
        try:
            nombre_normalizado = (nombre or "").strip().upper()
            descripcion_normalizada = (descripcion or "").strip().upper()
            permisos_normalizados = sorted(
                {
                    (permiso or "").strip().upper()
                    for permiso in (permisos or [])
                    if (permiso or "").strip()
                }
            )

            if not nombre_normalizado:
                return None, False, "Debes ingresar un nombre para el rol."

            rol_existente = self.session.query(Roles).filter_by(nombre=nombre_normalizado).first()
            if rol_existente:
                return rol_existente, False, f"Ya existe un rol registrado con el nombre {nombre_normalizado}."

            if not permisos_normalizados:
                return None, False, "Debes seleccionar al menos un permiso para crear el rol."

            PermisosModel(self.session).crear_permisos_principal
            conjunto_permisos = self.session.query(Permisos).filter(Permisos.nombre.in_(permisos_normalizados)).all()
            permisos_encontrados = {permiso.nombre for permiso in conjunto_permisos}
            permisos_faltantes = [permiso for permiso in permisos_normalizados if permiso not in permisos_encontrados]
            if permisos_faltantes:
                return None, False, f"No se encontraron permisos válidos para: {', '.join(permisos_faltantes)}"

            nuevo_rol = Roles(
                nombre=nombre_normalizado,
                descripcion=descripcion_normalizada,
            )
            nuevo_rol.permisos.extend(conjunto_permisos)
            self.session.add(nuevo_rol)
            self.session.flush()
            return nuevo_rol, True, f"Rol {nuevo_rol.nombre} creado correctamente."
        except IntegrityError as e:
            self.session.rollback()  # Revierte la transacción si ocurre un error
            return None, False, f"No se pudo crear el rol por un conflicto de integridad: {e}"
        except Exception as e:
            self.session.rollback()  # Revierte la transacción en caso de otros errores
            return None, False, f"Ocurrió un error al crear el rol: {e}"

    def obtener_todos(self):
        try:
            roles_todos = self.session.query(Roles).all()
            if roles_todos:
                return roles_todos, True
            else:
                return [], False
        except Exception as e:
            return [], False

    def todos_roles_con_permisos(self):
        roles = (
            self.session.query(Roles)
            .options(joinedload(Roles.permisos))
            .order_by(Roles.nombre.asc())
            .all()
        )
        if not roles:
            return [], False
        return roles, True

    def buscar_roles_por_nombre(self, nombre):
        termino = (nombre or "").strip().upper()
        consulta = (
            self.session.query(Roles)
            .options(joinedload(Roles.permisos))
            .order_by(Roles.nombre.asc())
        )
        if termino:
            consulta = consulta.filter(Roles.nombre.ilike(f"%{termino}%"))

        roles = consulta.all()
        if not roles:
            return [], False
        return roles, True

    def obtener_rol_por_id(self, id_rol):
        rol = (
            self.session.query(Roles)
            .options(joinedload(Roles.permisos))
            .filter(Roles.id == id_rol)
            .first()
        )
        if rol is None:
            return None, False
        return rol, True

    def actualizar_rol(self, id_rol, nombre, descripcion=None, permisos=None):
        try:
            rol = (
                self.session.query(Roles)
                .options(joinedload(Roles.permisos))
                .filter(Roles.id == id_rol)
                .first()
            )
            if rol is None:
                return None, False, "No se encontró el rol seleccionado para actualizar."

            nombre_normalizado = (nombre or "").strip().upper()
            descripcion_normalizada = (descripcion or "").strip().upper()
            permisos_normalizados = sorted(
                {
                    (permiso or "").strip().upper()
                    for permiso in (permisos or [])
                    if (permiso or "").strip()
                }
            )

            if not nombre_normalizado:
                return None, False, "Debes ingresar un nombre para el rol."

            rol_duplicado = (
                self.session.query(Roles)
                .filter(Roles.nombre == nombre_normalizado, Roles.id != id_rol)
                .first()
            )
            if rol_duplicado:
                return None, False, f"Ya existe un rol registrado con el nombre {nombre_normalizado}."

            if not permisos_normalizados:
                return None, False, "Debes seleccionar al menos un permiso para actualizar el rol."

            PermisosModel(self.session).crear_permisos_principal
            conjunto_permisos = self.session.query(Permisos).filter(Permisos.nombre.in_(permisos_normalizados)).all()
            permisos_encontrados = {permiso.nombre for permiso in conjunto_permisos}
            permisos_faltantes = [permiso for permiso in permisos_normalizados if permiso not in permisos_encontrados]
            if permisos_faltantes:
                return None, False, f"No se encontraron permisos válidos para: {', '.join(permisos_faltantes)}"

            rol.nombre = nombre_normalizado
            rol.descripcion = descripcion_normalizada
            rol.permisos = list(conjunto_permisos)
            self.session.flush()
            return rol, True, f"Rol {rol.nombre} actualizado correctamente."
        except IntegrityError as e:
            self.session.rollback()
            return None, False, f"No se pudo actualizar el rol por un conflicto de integridad: {e}"
        except Exception as e:
            self.session.rollback()
            return None, False, f"Ocurrió un error al actualizar el rol: {e}"

    def obtener_contexto_usuario(self, usuario_id):
        usuario = (
            self.session.query(Usuarios)
            .options(joinedload(Usuarios.rol).joinedload(Roles.permisos))
            .filter(Usuarios.id == usuario_id)
            .first()
        )
        if usuario is None:
            return {
                "rol_id": None,
                "rol_nombre": None,
                "permisos": [],
            }, False

        rol = usuario.rol
        permisos = sorted({permiso.nombre for permiso in getattr(rol, "permisos", [])}) if rol else []
        return {
            "rol_id": rol.id if rol else None,
            "rol_nombre": rol.nombre if rol else None,
            "permisos": permisos,
        }, True

    def eliminar_rol_con_permisos(self, id):
        rol = self.session.query(Roles).filter(Roles.id == id).first()
        if rol is None:
            return False
        self.session.delete(rol)
        return True
