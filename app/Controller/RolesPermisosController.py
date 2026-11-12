from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from ..Model.GruposyPermisosModel import PermisosModel, RolesModel
from .MensajesAlertasController import Mensaje
from ..DataBase.conexionBD import Conexion_base_datos
from ..View.UserInterfacePy.UI_CONTROL_ROLES import Ui_Control_Roles_Permisos
from .UiTheme import apply_module_theme, configure_child_modal


class ControlRolesController(QWidget):
    def __init__(self, parent=None, permisos_usuario=None):
        super().__init__(parent)
        self.ui = Ui_Control_Roles_Permisos()
        self.ui.setupUi(self)
        self.btn_cancelar = QPushButton("Cancelar", self.ui.contenedor)
        self.btn_cancelar.setObjectName("btn_cancelar_roles")
        self.btn_cancelar.setProperty("variant", "neutral")
        self.btn_cancelar.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.btn_cancelar.clicked.connect(self.close)
        self.ui.gridLayout_4.addWidget(self.btn_cancelar, 2, 0, Qt.AlignRight)
        configure_child_modal(self, drag_widget=getattr(self.ui, "contenedor", None), frameless=True)
        apply_module_theme(self)
        #// MOSTRAR VENTANA EN EL CENTRO DE LA PANTALLA
        pantalla = self.frameGeometry()
        pantalla.moveCenter(self.screen().availableGeometry().center())
        self.move(pantalla.topLeft())
        #//LIMITE CARACTERES
        self.ui.txt_nombrerol.setMaxLength(100)
        self.ui.txt_descripcionrol.setMaxLength(255)
        self.permisos_usuario = {
            str(permiso).strip().upper()
            for permiso in (permisos_usuario or [])
            if str(permiso).strip()
        }
        self.es_administrador = "ADMINISTRADOR" in self.permisos_usuario
        self.puede_crear_roles = self._tiene_algun_permiso({"CREARGRUPOPERMISOS"})
        self.puede_modificar_roles = self._tiene_algun_permiso({"MODIFICARGRUPOPERMISOS"})
        self.puede_eliminar_roles = self._tiene_algun_permiso({"ELIMINARGRUPOPERMISOS"})
        #-------------------
        #// VARIABLES
        self.permisos = set()
        self.seleccion_conectada_tabla = None
        self.registro_seleccionado = None
        self.rol_seleccionado = None
        self.rol_en_edicion_id = None
        self.checkboxes_permisos = self._obtener_checkboxes_permisos()
        self.indice_tab_lista = self.ui.contenedor_funcionesroles.indexOf(self.ui.contenedor_funcionlistaroles)
        self.indice_tab_formulario = self.ui.contenedor_funcionesroles.indexOf(self.ui.contenedor_funcioncrearroles)
        self.texto_tab_formulario = self.ui.contenedor_funcionesroles.tabText(self.indice_tab_formulario)
        self._cambio_programatico_a_edicion = False
        #-----------------
        # SEÑALES: BOTONES
        self.ui.btn_btn_agregar.clicked.connect(self.agregar_roles_al_sistema)
        self.ui.btn_btn_buscar.clicked.connect(self.buscar_roles_del_sistema)
        self.ui.btn_btn_eliminarrol.clicked.connect(self.eliminar_rol_del_sistema)
        self.ui.btn_btn_modificarrol.clicked.connect(self.modificar_rol_del_sistema)
        self.ui.txt_nombrerol.returnPressed.connect(self.agregar_roles_al_sistema)
        self.ui.txt_Buscar_nombrerol.returnPressed.connect(self.buscar_roles_del_sistema)
        self.ui.contenedor_funcionesroles.currentChanged.connect(self._manejar_cambio_tab_roles)
        #--------------------
        self._asegurar_catalogo_roles()
        self.mostrar_roles_existentes()
        self._aplicar_permisos_ui()

        #COMMENT: RECORRER LOS ATRIBUTOS DE LA VENTANA QUE COMIENZAN CON "OPCION_"
        for caja in self.checkboxes_permisos:
            caja.stateChanged.connect(self.comprobar_caja_verificacion)  # COMMENTLINE: AL DAR CLIC, SE EJECUTA EL METODO

    def _tiene_algun_permiso(self, permisos_requeridos):
        if not permisos_requeridos:
            return True
        if self.es_administrador:
            return True
        return bool(self.permisos_usuario.intersection({permiso.upper() for permiso in permisos_requeridos}))

    def _aplicar_permisos_ui(self):
        if not self.puede_modificar_roles:
            self.ui.btn_btn_modificarrol.setEnabled(False)
            self.ui.btn_btn_modificarrol.hide()
        if not self.puede_eliminar_roles:
            self.ui.btn_btn_eliminarrol.setEnabled(False)
            self.ui.btn_btn_eliminarrol.hide()
        self._actualizar_estado_formulario_por_permisos()

    def _actualizar_estado_formulario_por_permisos(self):
        en_edicion = self.rol_en_edicion_id is not None
        puede_usar_formulario = self.puede_crear_roles or en_edicion
        puede_guardar = self.puede_modificar_roles if en_edicion else self.puede_crear_roles
        self.ui.contenedor_funcionesroles.setTabEnabled(self.indice_tab_formulario, puede_usar_formulario)
        self.ui.btn_btn_agregar.setVisible(puede_guardar)
        self.ui.btn_btn_agregar.setEnabled(puede_guardar)

    def _asegurar_catalogo_roles(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                PermisosModel(session).crear_permisos_principal
                RolesModel(session).crear_grupo_principal

    def _obtener_checkboxes_permisos(self):
        return [
            getattr(self.ui, atributo)
            for atributo in dir(self.ui)
            if atributo.startswith("opcion_") and isinstance(getattr(self.ui, atributo), QCheckBox)
        ]

    def _sincronizar_permisos_seleccionados(self):
        self.permisos = {
            checkbox.objectName().replace("opcion_", "", 1).upper()
            for checkbox in self.checkboxes_permisos
            if checkbox.isChecked()
        }
        return sorted(self.permisos)

    def _marcar_permisos_formulario(self, permisos):
        permisos_normalizados = {
            (permiso or "").strip().upper()
            for permiso in (permisos or [])
            if (permiso or "").strip()
        }
        for checkbox in self.checkboxes_permisos:
            permiso_checkbox = checkbox.objectName().replace("opcion_", "", 1).upper()
            checkbox.blockSignals(True)
            checkbox.setChecked(permiso_checkbox in permisos_normalizados)
            checkbox.blockSignals(False)
        self.permisos = permisos_normalizados

    def _limpiar_formulario_rol(self):
        self.ui.txt_nombrerol.clear()
        self.ui.txt_descripcionrol.clear()
        self._marcar_permisos_formulario(set())

    def _restablecer_modo_creacion(self, limpiar_formulario=True):
        self.rol_en_edicion_id = None
        self.rol_seleccionado = None
        self.ui.etiquetaTitulo_rol.setText("Nuevo Rol")
        self.ui.btn_btn_agregar.setText("GUARDAR")
        self.ui.contenedor_funcionesroles.setTabText(self.indice_tab_formulario, self.texto_tab_formulario)
        if limpiar_formulario:
            self._limpiar_formulario_rol()
        self._actualizar_estado_formulario_por_permisos()

    def _cargar_rol_en_formulario(self, rol):
        self.rol_en_edicion_id = rol.id
        self.rol_seleccionado = rol
        self.ui.etiquetaTitulo_rol.setText("Editar Rol")
        self.ui.btn_btn_agregar.setText("ACTUALIZAR")
        self.ui.contenedor_funcionesroles.setTabText(self.indice_tab_formulario, "Editar rol")
        self.ui.txt_nombrerol.setText(rol.nombre or "")
        self.ui.txt_descripcionrol.setText(rol.descripcion or "")
        self._marcar_permisos_formulario({permiso.nombre for permiso in getattr(rol, "permisos", [])})
        self._actualizar_estado_formulario_por_permisos()

    def _refrescar_listado_roles(self):
        if self.ui.txt_Buscar_nombrerol.text().strip():
            self.buscar_roles_del_sistema()
            return
        self.mostrar_roles_existentes()

    def _manejar_cambio_tab_roles(self, index):
        if index != self.indice_tab_formulario:
            return
        if self.rol_en_edicion_id is None and not self.puede_crear_roles:
            self.ui.contenedor_funcionesroles.setCurrentIndex(self.indice_tab_lista)
            return
        if self._cambio_programatico_a_edicion:
            self._cambio_programatico_a_edicion = False
            return
        if self.rol_en_edicion_id is not None:
            self._restablecer_modo_creacion(limpiar_formulario=True)

    def comprobar_caja_verificacion(self, state):
        sender = self.sender()
        verificacion = sender.objectName()
        permiso = verificacion.replace("opcion_", "", 1).upper()
        if state == Qt.Checked:
            self.permisos.add(permiso)
        else:
            self.permisos.discard(permiso)

    def agregar_roles_al_sistema(self):
        if self.rol_en_edicion_id is None and not self.puede_crear_roles:
            Mensaje().mensaje_informativo("No cuentas con permisos para crear roles.")
            return
        if self.rol_en_edicion_id is not None and not self.puede_modificar_roles:
            Mensaje().mensaje_informativo("No cuentas con permisos para modificar roles.")
            return
        nombre = self.ui.txt_nombrerol.text().strip().upper()
        descripcion = self.ui.txt_descripcionrol.text().strip().upper()
        permisos_mayusculas = self._sincronizar_permisos_seleccionados()

        if not nombre:
            Mensaje().mensaje_informativo("Debes ingresar un nombre para el rol.")
            return

        if len(permisos_mayusculas) == 0:
            Mensaje().mensaje_informativo("Para que puedar almacenar un nuevo rol de usuario, debes de seleccionar por lo menos una familia de permisos.")
            return

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                if self.rol_en_edicion_id is not None:
                    rol, status_rol, mensaje = RolesModel(session).actualizar_rol(
                        id_rol=self.rol_en_edicion_id,
                        nombre=nombre,
                        descripcion=descripcion,
                        permisos=permisos_mayusculas,
                    )
                else:
                    rol, status_rol, mensaje = RolesModel(session).crear_Rol(
                        nombre=nombre,
                        descripcion=descripcion,
                        permisos=permisos_mayusculas,
                    )
        if not status_rol:
            Mensaje().mensaje_alerta(mensaje)
            return

        Mensaje().mensaje_informativo(mensaje)
        self._restablecer_modo_creacion(limpiar_formulario=True)
        self._refrescar_listado_roles()
        self.ui.contenedor_funcionesroles.setCurrentIndex(self.indice_tab_lista)
        return

    def mostrar_roles_existentes(self):
        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                lista_roles, status_lista_roles = RolesModel(session).todos_roles_con_permisos()
                self.mostrar_roles_en_tabla(lista_roles if status_lista_roles else [])

    def buscar_roles_del_sistema(self):
        nombre_rol = self.ui.txt_Buscar_nombrerol.text().strip()
        if not nombre_rol:
            self.mostrar_roles_existentes()
            return

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                lista_roles, status_lista_roles = RolesModel(session).buscar_roles_por_nombre(nombre_rol)

        self.mostrar_roles_en_tabla(lista_roles)
        if not status_lista_roles:
            Mensaje().mensaje_informativo(f"No se encontraron roles con el nombre {nombre_rol.upper()}.")

    def modificar_rol_del_sistema(self):
        if not self.puede_modificar_roles:
            Mensaje().mensaje_informativo("No cuentas con permisos para modificar roles.")
            return
        if self.registro_seleccionado is None:
            Mensaje().mensaje_informativo("Debes seleccionar un rol para poder modificarlo.")
            return

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                rol, status_rol = RolesModel(session).obtener_rol_por_id(self.registro_seleccionado)

        if not status_rol:
            Mensaje().mensaje_alerta("No se encontró el rol seleccionado para editar.")
            return

        self.ui.contenedor_funcionesroles.setTabEnabled(self.indice_tab_formulario, True)
        self._cambio_programatico_a_edicion = True
        self._cargar_rol_en_formulario(rol)
        self.ui.contenedor_funcionesroles.setCurrentIndex(self.indice_tab_formulario)
        self.ui.txt_nombrerol.setFocus()
        self.ui.txt_nombrerol.selectAll()

    # REVIEW
    def mostrar_roles_en_tabla(self, lista_elementos = None):
        # Si no existe el modelo, lo creamos, sino lo limpiamos
        if not hasattr(self, 'modelo_lista_roles'):
            self.modelo_lista_roles = QStandardItemModel()
        else:
            self.modelo_lista_roles.clear()  # Limpiar el modelo si ya existe

        selection_model = self.ui.tabla_listaroles.selectionModel()
        if self.seleccion_conectada_tabla and selection_model:
            try:
                selection_model.currentChanged.disconnect(self.seleccion_elemento_tabla_roles)
            except (RuntimeError, TypeError):
                pass
            self.seleccion_conectada_tabla = False

        self.registro_seleccionado = None
        self.rol_seleccionado = None

        # Establecer los encabezados de las columnas
        self.modelo_lista_roles.setHorizontalHeaderLabels(["Id", "Nombre", "Descripción", "Permisos"])

        # Recorrer los roles y agregar cada uno como una fila en el modelo
        for rol in (lista_elementos or []):
            if rol is not None:
                permisos = ", ".join(sorted({permiso.nombre for permiso in getattr(rol, 'permisos', [])})) or "Sin permiso"
                # Preparar los datos de la fila
                row_data = [
                    str(rol.id),  # Id del rol
                    rol.nombre,  # Nombre del rol
                    rol.descripcion if rol.descripcion else "No disponible",  # Descripción del rol
                    permisos,
                ]

                # Crear los elementos de la fila para la tabla
                items = [QStandardItem(item) for item in row_data]

                # Asociar el rol con cada item para poder acceder a los objetos más tarde
                for item in items:
                    item.setData(rol, Qt.UserRole)

                # Añadir la fila al modelo
                self.modelo_lista_roles.appendRow(items)

        # Asignar el modelo al QTableView solo una vez, después de llenar el modelo
        self.ui.tabla_listaroles.setModel(self.modelo_lista_roles)

        # Conectar la señal a la función que obtiene el ID del elemento seleccionado
        nuevo_selection_model = self.ui.tabla_listaroles.selectionModel()
        if nuevo_selection_model:
            nuevo_selection_model.currentChanged.connect(self.seleccion_elemento_tabla_roles)
            self.seleccion_conectada_tabla = True  # Marcar como conectada

    def seleccion_elemento_tabla_roles(self, current, previus):
        if current.isValid() and current.column() >= 0:  # Verifica si es la primera columna
            indice_fila = current.row()
            elemento = self.modelo_lista_roles.item(indice_fila, 0)
            if elemento is not None:
                rol = elemento.data(Qt.UserRole)
                if rol:
                    self.registro_seleccionado = rol.id
                    self.rol_seleccionado = rol
            else:
                return

    def eliminar_rol_del_sistema(self):
        if not self.puede_eliminar_roles:
            Mensaje().mensaje_informativo("No cuentas con permisos para eliminar roles.")
            return
        if self.registro_seleccionado is None:
            Mensaje().mensaje_informativo("Debes de seleccionar un registro para poder ejecutar la función de eliminar.")
            return

        with Conexion_base_datos() as db:
            session = db.abrir_sesion()
            with session.begin():
                status_rol_eliminado = RolesModel(session).eliminar_rol_con_permisos(id=self.registro_seleccionado)

                # Verifica el estado de la eliminación
                if not status_rol_eliminado:
                    Mensaje().mensaje_alerta("No se logró eliminar el registro de la base de datos.")
                    return

                # Mensaje informativo de eliminación exitosa
                Mensaje().mensaje_informativo("Se eliminó el rol de la base de datos de forma correcta.")
            self._restablecer_modo_creacion(limpiar_formulario=True)
            self._refrescar_listado_roles()  # Actualizamos la tabla