import inspect
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.parametrize("moral", [False, True])
@pytest.mark.parametrize("field,value", [("rfc", "INVALIDO"), ("curp", "INVALIDA"),
    ("numero telefono", "123"), ("codigo postal", "ABC12"), ("correo", "sin-arroba"),
    ("limite del credito", -1), ("limite del credito", float("nan"))])
def test_client_contact_contract(moral, field, value):
    from app.Model.AdministracionEntrada import validar_contacto_cliente
    data = {"rfc": "ABC010101AB1" if moral else "GODE561231GR8", "curp": "GODE561231HDFRRN09",
            "numero telefono": "5512345678", "codigo postal": "01234", "correo electronico": "test@example.test",
            "correo electronico empresa": "test@example.test", "telefono representante": "5512345678",
            "correo electronico representante": "rep@example.test", "limite del credito": 0}
    validar_contacto_cliente(data, moral)
    if field == "curp" and moral:
        return
    key = ("correo electronico empresa" if moral else "correo electronico") if field == "correo" else field
    data[key] = value
    with pytest.raises(ValueError):
        validar_contacto_cliente(data, moral)


@pytest.mark.unit
@pytest.mark.parametrize("operacion", ["alta", "consulta", "actualizar"])
def test_lote2_personal_no_encontrado_tiene_contrato(operacion):
    from app.Model.EmpleadoModel import EmpleadosModel
    session = Mock()
    session.get.return_value = None
    modelo = EmpleadosModel(session)
    if operacion == "alta":
        assert modelo.alta_empleado(1, None) == (None, False)
    elif operacion == "consulta":
        assert modelo.obtener_empleado_por_id(None) == (None, False)
    else:
        datos = {nombre: None for nombre in inspect.signature(modelo.actualizar_empleado).parameters}
        datos["nombre"] = "PRUEBA"
        assert modelo.actualizar_empleado(**datos) == (None, False)


@pytest.mark.qt
def test_lote2_perfil_dto_con_fk_opcionales(qtbot):
    from datetime import date
    from app.Controller.PerfilUsuarioController import Perfil
    from app.Model.AdministracionEntrada import serializar_resultado
    from app.Model.BaseDatosModel import Usuarios, Empleados
    perfil = Perfil(usuario={"id_usuario": 1, "nombre_usuario": "PRUEBA"})
    qtbot.addWidget(perfil)
    usuario = Usuarios(id=1, usuario="PRUEBA", empleado=Empleados(id=2, nombre="PRUEBA", activo=True, fecha_nacimiento=date(2000, 1, 1), fecha_contratacion=date(2020, 1, 1)))
    perfil.llenarCampos({"exito": True, "data": serializar_resultado(usuario)})
    assert perfil.ui.txt_nombre.text() == "PRUEBA"
    assert perfil.ui.txt_puesto.text() == ""
    assert perfil.ui.txt_departamento.text() == ""
    assert perfil.ui.txt_sucursal.text() == ""


@pytest.mark.unit
def test_lote2_asignacion_usuario_no_declara_exito_sin_fila():
    from app.Model.UsuarioModel import UsuarioModel
    session = Mock()
    session.execute.return_value.rowcount = 0
    assert UsuarioModel(session).asignar_usuario_empleado(SimpleNamespace(id=1), SimpleNamespace(id=2)) is False
    session.flush.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("valor", ["SIN SELECCION", True, -1, 0])
def test_lote2_contrato_rechaza_fk_invalida(valor):
    from app.Model.AdministracionEntrada import validar_longitudes
    from app.Model.BaseDatosModel import Empleados
    with pytest.raises(ValueError):
        validar_longitudes(Empleados, {"puesto_id": valor})


@pytest.mark.unit
@pytest.mark.parametrize("seleccion", ["SIN SELECCION", SimpleNamespace(id=None), SimpleNamespace(id=-1), True])
def test_lote2_id_seleccionado_rechaza_placeholder(seleccion):
    from app.Model.AdministracionEntrada import id_seleccionado
    with pytest.raises(ValueError):
        id_seleccionado(seleccion, "puesto")


@pytest.mark.qt
def test_lote2_validacion_personal_rechaza_catalogo_textual(qtbot, monkeypatch):
    from app.Controller import RegistroInicialController as modulo
    mensaje = Mock()
    monkeypatch.setattr(modulo.QMessageBox, "critical", mensaje)
    datos = {"puesto": "SIN SELECCION", "sucursal": SimpleNamespace(id=1), "departamento": SimpleNamespace(id=2), "rol": SimpleNamespace(id=3)}
    assert modulo.Registro_personal_inicial.validar_datos(SimpleNamespace(), datos) is False
    mensaje.assert_called_once()


@pytest.mark.qt
def test_lote2_alta_sucursal_entrega_snapshot(qtbot, monkeypatch):
    from app.Controller import SucursalesController as modulo
    from app.Model.BaseDatosModel import Sucursales
    modelo = Mock()
    modelo.agregar_sucursal.return_value = (Sucursales(id=1, nombre_sucursal="PRUEBA"), True)
    monkeypatch.setattr(modulo, "SucursalesModel", lambda session: modelo)
    session = Mock()
    resultado = modulo.SucursalesController.agregar_sucursal_query(SimpleNamespace(), session, {"nombre_sucursal": "PRUEBA"})
    assert resultado["exito"] is True
    assert resultado["data"].id == 1
    assert not hasattr(resultado["data"], "_sa_instance_state")


@pytest.mark.unit
def test_lote2_resultado_compuesto_sin_orm_ni_hash():
    from app.Model.AdministracionEntrada import serializar_resultado
    from app.Model.BaseDatosModel import Empleados, Usuarios, Roles, Departamentos, Sucursales, Puestos
    entidades = [Empleados(id=1), Usuarios(id=2), Roles(id=3), Departamentos(id=4), Sucursales(id=5), Puestos(id=6)]
    resultado = serializar_resultado(({"data": entidades}, True))
    assert isinstance(resultado, tuple)
    assert resultado[1] is True
    for original, dto in zip(entidades, resultado[0]["data"]):
        assert dto.id == original.id
        assert not hasattr(dto, "_sa_instance_state")
        assert not hasattr(dto, "contrase\u00f1a")


@pytest.mark.qt
@pytest.mark.parametrize("archivo,clase,query,modelo,lector", [
    ("DepartamentosController", "DepartamentosController", "buscar_departamento_query", "DepartamentosModel", "filtrar_nombre"),
    ("DepartamentosController", "DepartamentosController", "obtener_departamentos_query", "DepartamentosModel", "obtener_todos"),
    ("DepartamentosController", "DepartamentosController", "listar_sucursales_del_sistema_query", "SucursalesModel", "obtener_todo"),
    ("PuestosController", "PuestosController", "filtrar_puestos_query", "PuestoModel", "filtrar_por_nombre"),
    ("PuestosController", "PuestosController", "obtener_puestos_query", "PuestoModel", "obtener_todos"),
    ("PuestosController", "PuestosController", "obtener_departamentos_query", "DepartamentosModel", "obtener_todos"),
    ("SucursalesController", "SucursalesController", "buscar_sucursal_query", "SucursalesModel", "filtrar_nombre"),
    ("SucursalesController", "SucursalesController", "obtener_sucursales_query", "SucursalesModel", "obtener_todo"),
    ("PerfilUsuarioController", "Perfil", "buscarEmpleadoQuery", "UsuarioModel", "obtenerDatosGeneralesUsuario"),
    ("RegistroInicialController", "Registro_personal_inicial", "obtener_sucursales_query", "SucursalesModel", "obtener_todo"),
    ("RegistroInicialController", "Registro_personal_inicial", "obtener_departamentos_query", "DepartamentosModel", "obtener_todos"),
    ("RegistroInicialController", "Registro_personal_inicial", "obtener_puestos_query", "PuestoModel", "obtener_todos"),
])
def test_lote2_consumidores_exigen_dto(qtbot, monkeypatch, archivo, clase, query, modelo, lector):
    import importlib
    modulo = importlib.import_module(f"app.Controller.{archivo}")
    adaptador = Mock()
    getattr(adaptador, lector).return_value = ([SimpleNamespace(id=1)], True)
    monkeypatch.setattr(modulo, modelo, lambda session: adaptador)
    funcion = getattr(getattr(modulo, clase), query)
    argumentos = {nombre: "PRUEBA" for nombre in inspect.signature(funcion).parameters if nombre not in {"self", "session"}}
    respuesta = funcion(SimpleNamespace(), Mock(), **argumentos)
    assert respuesta["exito"] is True
    assert getattr(adaptador, lector).call_args.kwargs["snapshots"] is True


@pytest.mark.qt
@pytest.mark.parametrize("fallo", ["exito", "modelo", "asociacion", "commit", "duplicado"])
def test_lote2_alta_departamento_transaccion_ids(qtbot, monkeypatch, fallo):
    from app.Controller import DepartamentosController as modulo
    modelo = Mock()
    modelo.agregar_departamento.return_value = (SimpleNamespace(id=1, nombre="PRUEBA"), fallo != "duplicado")
    modelo.sincronizar_sucursales.return_value = (1, 0)
    if fallo == "modelo":
        modelo.agregar_departamento.side_effect = RuntimeError("fallo sintetico")
    if fallo == "asociacion":
        modelo.sincronizar_sucursales.side_effect = RuntimeError("fallo sintetico")
    monkeypatch.setattr(modulo, "DepartamentosModel", lambda session: modelo)
    session = Mock()
    if fallo == "commit":
        session.commit.side_effect = RuntimeError("fallo sintetico")
    respuesta = modulo.DepartamentosController.agregar_departamento_query(SimpleNamespace(), session, {"nombre": "PRUEBA"}, sucursales_ids=[2])
    assert respuesta["exito"] is (fallo == "exito")
    if fallo in {"exito", "commit"}:
        session.commit.assert_called_once()
    else:
        session.commit.assert_not_called()
    if fallo != "exito":
        session.rollback.assert_called_once()
    if fallo in {"exito", "commit", "asociacion"}:
        assert modelo.sincronizar_sucursales.call_args.args[1] == [2]


@pytest.mark.unit
@pytest.mark.parametrize("archivo,clase,metodo", [
    ("EmpleadoModel", "EmpleadosModel", "obtener_empleados_detallados"),
    ("EmpleadoModel", "EmpleadosModel", "obtener_empleado_detallado_porId"),
    ("EmpleadoModel", "EmpleadosModel", "eliminar_credenciales"),
    ("DepartamentosModel", "DepartamentosModel", "obtener_todos"),
    ("DepartamentosModel", "DepartamentosModel", "filtrar_nombre"),
    ("DepartamentosModel", "DepartamentosModel", "obtener_departamento_por_id"),
    ("PuestoModel", "PuestoModel", "obtener_todos"),
    ("PuestoModel", "PuestoModel", "obtener_puesto_por_id"),
    ("SucursalesModel", "SucursalesModel", "obtener_todo"),
    ("SucursalesModel", "SucursalesModel", "filtrar_nombre"),
    ("SucursalesModel", "SucursalesModel", "obtener_sucursal_por_id"),
    ("SucursalesModel", "SucursalesModel", "eliminar"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "mostrar_clientes_fisicos"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "mostrar_clientes_morales"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "filtrar_clientes_fisicos_por_nombre"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "filtrar_clientes_morales_por_nombre"),
])
def test_lote2_lecturas_y_bajas_propagan_causa(archivo, clase, metodo):
    import importlib
    session = Mock()
    error = RuntimeError("fallo sintetico")
    session.query.side_effect = error
    session.get.side_effect = error
    session.delete.side_effect = error
    funcion = getattr(getattr(importlib.import_module(f"app.Model.{archivo}"), clase)(session), metodo)
    datos = {nombre: (SimpleNamespace(id=1, usuario=SimpleNamespace(id=2)) if nombre == "empleado" else 1)
             for nombre, parametro in inspect.signature(funcion).parameters.items() if parametro.default is inspect.Parameter.empty}
    with pytest.raises(RuntimeError) as capturada:
        funcion(**datos)
    assert capturada.value is error
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("archivo,clase,metodo,entidad", [
    ("EmpleadoModel", "EmpleadosModel", "obtener_empleado_detallado_porId", "Empleados"),
    ("SucursalesModel", "SucursalesModel", "filtrar_nombre", "Sucursales"),
    ("DepartamentosModel", "DepartamentosModel", "filtrar_nombre", "Departamentos"),
    ("PuestoModel", "PuestoModel", "filtrar_por_nombre", "Puestos"),
    ("UsuarioModel", "UsuarioModel", "obtenerDatosGeneralesUsuario", "Usuarios"),
])
def test_lote2_lectores_restantes_snapshots(archivo, clase, metodo, entidad):
    import importlib
    from app.Model import BaseDatosModel as bd
    registro = getattr(bd, entidad)(id=7)
    consulta = Mock()
    for nombre in ("query", "options", "filter", "filter_by", "where"):
        getattr(consulta, nombre).return_value = consulta
    consulta.all.return_value = [registro]
    consulta.first.return_value = registro
    funcion = getattr(getattr(importlib.import_module(f"app.Model.{archivo}"), clase)(consulta), metodo)
    datos = {nombre: 1 for nombre, parametro in inspect.signature(funcion).parameters.items() if parametro.default is inspect.Parameter.empty}
    resultado, estado = funcion(**datos, snapshots=True)
    dto = resultado[0] if isinstance(resultado, list) else resultado
    assert estado is True
    assert dto.id == 7
    assert not hasattr(dto, "_sa_instance_state")


@pytest.mark.unit
@pytest.mark.parametrize("snapshots", [False, True])
def test_lote2_login_legacy_no_aplica_politica_de_alta(snapshots):
    import bcrypt
    from unittest.mock import MagicMock
    from app.Controller.CreadencialesUsuarioController import CredencialesModel
    from app.Model.BaseDatosModel import Usuarios, Empleados

    password = "corta"
    usuario = Usuarios(id=1, usuario="PRUEBA", empleado=Empleados(id=2, activo=True))
    setattr(usuario, "contrase\u00f1a", bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)))
    conexion = MagicMock()
    session = conexion.__enter__.return_value.abrir_sesion.return_value
    session.query.return_value.options.return_value.filter_by.return_value.first.return_value = usuario
    modelo = CredencialesModel.__new__(CredencialesModel)
    modelo.conexion = conexion
    datos, exito = modelo.verificar_credenciales("PRUEBA", password, snapshots=snapshots)
    assert exito is True
    assert datos.id == 1
    assert datos.empleado.id == 2
    if snapshots:
        assert not hasattr(datos, "_sa_instance_state")
        assert not hasattr(datos, "contrase\u00f1a")
    else:
        assert datos is usuario
    assert modelo.verificar_credenciales("PRUEBA", "incorrecta") == (None, False)


@pytest.mark.unit
@pytest.mark.parametrize("operacion", ["crear", "actualizar", "asignar"])
def test_lote2_usuario_propaga_fallo_tecnico(operacion):
    from app.Model.UsuarioModel import UsuarioModel

    session = Mock()
    session.query.return_value.filter_by.return_value.first.return_value = None
    session.get.return_value = SimpleNamespace(id=1)
    session.execute.return_value.rowcount = 1
    error = RuntimeError("fallo sintetico")
    session.flush.side_effect = error
    modelo = UsuarioModel(session)
    with pytest.raises(RuntimeError) as capturada:
        if operacion == "crear":
            modelo.crear_usuario("PRUEBA", "a" * 12, None)
        elif operacion == "actualizar":
            modelo.actualizar_usuario(1, "PRUEBA", "a" * 12, None)
        else:
            modelo.asignar_usuario_empleado(SimpleNamespace(id=2), SimpleNamespace(id=1))
    assert capturada.value is error
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("subtipo", ["fisico", "moral"])
@pytest.mark.parametrize("campo,valor", [("limite_credito", float("nan")), ("credito_disponible", -1), ("porcentaje_descuento", 101)])
def test_lote2_clientes_rechazan_numeros_invalidos(subtipo, campo, valor):
    from app.Model.ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales

    session = Mock()
    metodo = getattr(ClientesFisicosAndMorales(session), f"actualizar_cliente_{subtipo}")
    datos = {nombre: None for nombre in inspect.signature(metodo).parameters}
    datos.update(id=1, nombre="PRUEBA", **{campo: valor})
    with pytest.raises(ValueError):
        metodo(**datos)
    assert not session.mock_calls


@pytest.mark.unit
@pytest.mark.parametrize("archivo,clase,metodo", [("DepartamentosModel", "DepartamentosModel", "agregar_departamento"), ("DepartamentosModel", "DepartamentosModel", "actualizar_departamento"), ("PuestoModel", "PuestoModel", "crear_puesto"), ("PuestoModel", "PuestoModel", "actualizar")])
def test_lote2_catalogos_rechazan_longitud_antes_sql(archivo, clase, metodo):
    import importlib
    from app.Model.BaseDatosModel import Departamentos, Puestos

    session = Mock()
    funcion = getattr(getattr(importlib.import_module(f"app.Model.{archivo}"), clase)(session), metodo)
    datos = {nombre: None for nombre in inspect.signature(funcion).parameters}
    entidad = Departamentos if archivo == "DepartamentosModel" else Puestos
    datos["nombre"] = "x" * (entidad.__table__.c.nombre.type.length + 1)
    with pytest.raises(ValueError):
        funcion(**datos)
    assert not session.mock_calls


@pytest.mark.qt
def test_lote2_cambio_password_rechaza_antes_de_confirmar(qtbot, monkeypatch):
    from app.Controller import RegistroInicialController as modulo
    mensaje = Mock()
    monkeypatch.setattr(modulo, "Mensaje", lambda *args: mensaje)
    ui = SimpleNamespace(txt_usuario_iniciosesion=Mock(), txt_contrasenia_usuario_iniciosesion=Mock(), cajaOpciones_rol_usuario=Mock())
    ui.txt_usuario_iniciosesion.text.return_value = "PRUEBA"
    ui.txt_contrasenia_usuario_iniciosesion.text.return_value = "corta"
    controlador = SimpleNamespace(WindowRegistroEmpleado=ui, empleado_existente=SimpleNamespace(usuario=SimpleNamespace(id=1)))
    modulo.Registro_personal_inicial.actualizar_credenciales(controlador)
    mensaje.mensaje_pregunta.assert_not_called()
    mensaje.mensaje_alerta.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("subtipo", ["fisico", "moral"])
@pytest.mark.parametrize("resultado", ["exito", "ausente", "error"])
def test_ref25_edicion_cliente_delega_transaccion_y_propaga_error(subtipo, resultado):
    from app.Model.ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales

    session = Mock(spec=["query", "commit", "rollback", "flush", "add"])
    query = session.query.return_value.filter.return_value
    cliente = SimpleNamespace(representante=None)
    query.first.return_value = cliente if resultado == "exito" else None
    error = RuntimeError("fallo sintetico")
    if resultado == "error":
        query.first.side_effect = error
    metodo = getattr(ClientesFisicosAndMorales(session), f"actualizar_cliente_{subtipo}")
    datos = {nombre: "PRUEBA" for nombre in inspect.signature(metodo).parameters}
    datos.update(id=7, categoria_cliente_id=None, areas_de_negocios_id=None)
    for campo in ("limite_credito", "credito_disponible", "credito_utilizado", "porcentaje_descuento", "porcentaje_interes", "ingresos"):
        if campo in datos:
            datos[campo] = 1.0
    for nombre in ("nombre_representante", "telefono_representante", "correo_representante", "puesto_representante"):
        if nombre in datos:
            datos[nombre] = "PRUEBA"

    if resultado == "error":
        with pytest.raises(RuntimeError, match="fallo sintetico") as capturada:
            metodo(**datos)
        assert capturada.value is error
    else:
        assert metodo(**datos) is (resultado == "exito")
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("fisico", [True, False])
@pytest.mark.parametrize("resultado", ["exito", "falso", "error", "commit"])
def test_ref25_coordinador_edicion_revierte_antes_de_responder(qtbot, monkeypatch, fisico, resultado):
    from app.Controller import ClientesController as modulo

    modelo = Mock()
    metodo = modelo.actualizar_cliente_fisico if fisico else modelo.actualizar_cliente_moral
    metodo.return_value = resultado != "falso"
    if resultado == "error":
        metodo.side_effect = RuntimeError("fallo sintetico")
    monkeypatch.setattr(modulo, "ClientesFisicosAndMorales", lambda session: modelo)
    session = Mock(spec=["commit", "rollback"])
    if resultado == "commit":
        session.commit.side_effect = RuntimeError("fallo sintetico")
    from collections import defaultdict

    datos = defaultdict(lambda: "PRUEBA")
    respuesta = modulo.Clientes.actualizar_clientes_query(
        SimpleNamespace(), session, SimpleNamespace(id=7, nombre="PRUEBA"),
        datos, SimpleNamespace(id=1), SimpleNamespace(id=2), fisico,
    )
    assert respuesta["exito"] is (resultado == "exito")
    if resultado in {"exito", "commit"}:
        session.commit.assert_called_once_with()
    else:
        session.commit.assert_not_called()
    if resultado == "exito":
        session.rollback.assert_not_called()
    else:
        session.rollback.assert_called_once_with()


@pytest.mark.unit
@pytest.mark.parametrize("password,valido", [
    ("a" * 11, False), ("a" * 12, True), ("a" * 72, True), ("a" * 73, False),
    ("\u00f1" * 36, True), ("\u00f1" * 37, False), (" " + "a" * 12, False),
    ("a" * 12 + " ", False), ("", False), (None, False),
])
def test_ref23_password_nuevo_sin_truncar(password, valido):
    from app.Model.UsuarioEntrada import validar_password_nuevo

    if valido:
        assert validar_password_nuevo(password) == password
    else:
        with pytest.raises(ValueError):
            validar_password_nuevo(password)


@pytest.mark.qt
def test_ref23_captura_password_no_trunca(qtbot):
    from app.Controller.RegistroInicialController import Registro_personal_inicial
    from PySide6.QtWidgets import QWidget
    from app.View.UserInterfacePy.UI_REGISTRO_EMPLEADO import Ui_RegistroAdministrador

    ventana = QWidget()
    qtbot.addWidget(ventana)
    ui = Ui_RegistroAdministrador()
    ui.setupUi(ventana)
    Registro_personal_inicial.ingresar_validaciones(SimpleNamespace(WindowRegistroEmpleado=ui))
    ui.txt_contrasenia_usuario_iniciosesion.setText("a" * 73)
    assert ui.txt_contrasenia_usuario_iniciosesion.text() == "a" * 73


@pytest.mark.unit
@pytest.mark.parametrize("operacion", ["crear", "actualizar"])
def test_ref23_modelo_rechaza_antes_de_consultar_o_hashear(operacion):
    from app.Model.UsuarioModel import UsuarioModel

    session = Mock()
    modelo = UsuarioModel(session)
    with pytest.raises(ValueError):
        if operacion == "crear":
            modelo.crear_usuario("PRUEBA", "a" * 73, None)
        else:
            modelo.actualizar_usuario(7, "PRUEBA", "a" * 73, None)
    assert not session.mock_calls


@pytest.mark.unit
def test_ref35_departamento_sincroniza_ids_en_su_sesion():
    from app.Model.DepartamentosModel import DepartamentosModel
    from app.Model.BaseDatosModel import Departamentos, Sucursales

    anterior = Sucursales(id=1)
    nueva = Sucursales(id=2)
    departamento = Departamentos(id=7, sucursales=[anterior])
    session = Mock()
    session.get.return_value = nueva
    assert DepartamentosModel(session).sincronizar_sucursales(departamento, [2]) == (1, 1)
    assert departamento.sucursales == [nueva]
    session.get.assert_called_once_with(Sucursales, 2)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("archivo,clase,metodo,entidad", [
    ("EmpleadoModel", "EmpleadosModel", "obtener_empleados_detallados", "Empleados"),
    ("EmpleadoModel", "EmpleadosModel", "filtrar_empleados", "Empleados"),
    ("SucursalesModel", "SucursalesModel", "obtener_todo", "Sucursales"),
    ("DepartamentosModel", "DepartamentosModel", "obtener_todos", "Departamentos"),
    ("PuestoModel", "PuestoModel", "obtener_todos", "Puestos"),
])
def test_ref35_modelos_administrativos_listan_snapshots(archivo, clase, metodo, entidad):
    import importlib
    from app.Model import BaseDatosModel as bd

    registro = getattr(bd, entidad)(id=7)
    consulta = Mock()
    for nombre in ("query", "options", "order_by", "offset", "limit", "filter"):
        getattr(consulta, nombre).return_value = consulta
    consulta.all.return_value = [registro]
    tipo = getattr(importlib.import_module(f"app.Model.{archivo}"), clase)
    datos, estado = getattr(tipo(consulta), metodo)(snapshots=True)
    assert estado is True
    assert datos[0].id == 7
    assert not hasattr(datos[0], "_sa_instance_state")


@pytest.mark.unit
def test_ref35_snapshot_personal_sin_hash_ni_orm():
    from app.Model.BaseDatosModel import Empleados, Usuarios, Roles, Puestos, Departamentos, Sucursales
    from app.Model.AdministracionEntrada import snapshot_empleado

    empleado = Empleados(id=7, nombre="PRUEBA", usuario=Usuarios(id=3, usuario="PRUEBA", rol=Roles(id=1, nombre="PRUEBA")),
                        puesto=Puestos(id=4, nombre="PRUEBA", departamento=Departamentos(id=5, nombre="PRUEBA")),
                        departamento=Departamentos(id=6, nombre="PRUEBA"), sucursal=Sucursales(id=8, nombre_sucursal="PRUEBA"))
    dto = snapshot_empleado(empleado)
    assert dto.usuario.rol.nombre == "PRUEBA"
    assert dto.puesto.departamento.id == 5
    assert not hasattr(dto.usuario, "contrase\u00f1a")
    for entidad in (dto, dto.usuario, dto.puesto, dto.departamento, dto.sucursal):
        assert not hasattr(entidad, "_sa_instance_state")


@pytest.mark.qt
@pytest.mark.parametrize("tipo", ["FISICO", "MORAL"])
@pytest.mark.parametrize("fallo_tardio", [False, True, "duplicado"])
def test_ref30_31_csv_real_y_rollback_tardio(qtbot, tmp_path, monkeypatch, tipo, fallo_tardio):
    import csv
    from app.Controller.ClientesController import Clientes
    from app.Model import ClientesImportacion as modulo
    from app.Model.BaseDatosModel import Categorias_de_clientes, Areas_negocios

    validas, requeridas = modulo.ClientesImportacion.columnas(tipo)
    campos = requeridas + ["categoria_cliente_id", "areas_de_negocios_id"]
    fila = {campo: "PRUEBA" for campo in campos}
    fila.update(categoria_cliente_id="1", areas_de_negocios_id="1", ingresos="10",
                fecha_nacimiento="2000-01-01", fecha_constitucion="2000-01-01")
    fila = {campo: fila[campo] for campo in campos}
    segunda = dict(fila, nombre="OTRO" if fallo_tardio else "A" * 256, rfc="OTRO")
    if tipo == "FISICO":
        segunda["curp"] = "OTRO"
    else:
        segunda.update(razon_social="OTRO", nif="OTRO")
    archivo = tmp_path / "clientes.csv"
    with archivo.open("w", encoding="utf-8", newline="") as salida:
        writer = csv.DictWriter(salida, fieldnames=campos)
        writer.writeheader()
        writer.writerows([fila, segunda])
    session = Mock()
    session.begin_nested = MagicMock()
    def query(*columnas):
        consulta = Mock()
        consulta.all.return_value = [SimpleNamespace(id=1, nombre="PRUEBA")] if len(columnas) == 1 and any(columnas[0] is modelo for modelo in (Categorias_de_clientes, Areas_negocios)) else []
        return consulta
    session.query.side_effect = query
    escritor = Mock()
    escritor.agregar_representante_cliente_moral.return_value = SimpleNamespace(id=3)
    metodo = escritor.agregar_cliente_fisico if tipo == "FISICO" else escritor.agregar_cliente_moral
    metodo.side_effect = ([(None, None), (SimpleNamespace(id=7), True)] if fallo_tardio == "duplicado" else [(SimpleNamespace(id=7), True), RuntimeError("fallo sintetico")])
    monkeypatch.setattr(modulo, "ClientesFisicosAndMorales", lambda session: escritor)
    funcion = Clientes.importar_clientes_fisicos_query if tipo == "FISICO" else Clientes.importar_clientes_morales_query
    resultado = funcion(SimpleNamespace(), session, str(archivo))
    assert resultado["exito"] is (fallo_tardio is not True)
    if fallo_tardio is True:
        assert resultado["agregados"] == 0
        session.rollback.assert_called_once_with()
        session.commit.assert_not_called()
    else:
        assert resultado["agregados"] == 1
        if fallo_tardio == "duplicado":
            assert resultado["duplicados"] == 1
            assert resultado["reporte"]["advertencias"][0]["fila"] == 2
        else:
            assert resultado["omitidos"] == 1
            assert resultado["reporte"]["errores"][0]["fila"] == 3
        session.commit.assert_called_once_with()
        session.add.assert_not_called()


@pytest.mark.unit
def test_ref30_encabezado_invalido_no_toca_sql():
    from app.Model.ClientesImportacion import ClientesImportacion

    session = Mock()
    reporte = {"errores": [{"fila": 1, "codigo": "columna_requerida"}], "advertencias": [], "filas": []}
    assert ClientesImportacion(session).importar_con_reporte(reporte, "FISICO")["exito"] is False
    assert not session.mock_calls


@pytest.mark.unit
@pytest.mark.parametrize("archivo,clase,metodo", [
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "agregar_cliente_fisico"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "agregar_cliente_moral"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "agregar_representante_cliente_moral"),
    ("ClientesFisicosAndMoralesModel", "ClientesFisicosAndMorales", "eliminar_cliente"),
    ("EmpleadoModel", "EmpleadosModel", "baja_empleado"),
    ("DepartamentosModel", "DepartamentosModel", "agregar_departamento"),
    ("DepartamentosModel", "DepartamentosModel", "eliminar_departamento"),
    ("PuestoModel", "PuestoModel", "eliminar_puesto"),
    ("SucursalesModel", "SucursalesModel", "agregar_sucursal"),
    ("SucursalesModel", "SucursalesModel", "actualizar"),
])
def test_ref25_modelos_propagan_causa_sin_rollback(archivo, clase, metodo):
    import importlib

    tipo = getattr(importlib.import_module(f"app.Model.{archivo}"), clase)
    session = Mock()
    error = RuntimeError("fallo sintetico")
    session.query.side_effect = error
    session.get.side_effect = error
    funcion = getattr(tipo(session), metodo)
    argumentos = {nombre: None for nombre in inspect.signature(funcion).parameters if nombre != "kwargs"}
    for nombre in ("nombre", "nombre_sucursal"):
        if nombre in argumentos:
            argumentos[nombre] = "PRUEBA"
    for nombre in ("id", "id_empleado"):
        if nombre in argumentos:
            argumentos[nombre] = 7
    if metodo == "agregar_sucursal":
        argumentos["nombre_sucursal"] = "PRUEBA"
    if metodo == "eliminar_cliente":
        from app.Model.BaseDatosModel import Clientes_fisicos
        argumentos["modelo"] = Clientes_fisicos
    with pytest.raises(RuntimeError) as capturada:
        funcion(**argumentos)
    assert capturada.value is error
    session.rollback.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("archivo,clase,modelo,metodo_modelo,metodo_query", [
    ("EmpleadosController", "EmpleadosController", "EmpleadosModel", "eliminar_empleado", "eliminar_empleado_query"),
    ("DepartamentosController", "DepartamentosController", "DepartamentosModel", "eliminar_departamento", "eliminar_departamento_query"),
    ("SucursalesController", "SucursalesController", "SucursalesModel", "actualizar", "actualizar_sucursal_query"),
    ("PuestosController", "PuestosController", "PuestoModel", "crear_puesto", "agregar_puestos_query"),
    ("PuestosController", "PuestosController", "PuestoModel", "actualizar", "actualizar_puesto_query"),
    ("PuestosController", "PuestosController", "PuestoModel", "eliminar_puesto", "eliminar_puesto_query"),
    ("RegistroInicialController", "Registro_personal_inicial", "EmpleadosModel", "actualizar_empleado", "actualizar_empleado_query"),
])
@pytest.mark.parametrize("fallo", ["exito", "falso", "modelo", "commit"])
def test_ref25_coordinadores_organizacion_rollback(qtbot, monkeypatch, archivo, clase, modelo, metodo_modelo, metodo_query, fallo):
    import importlib
    from collections import defaultdict

    modulo = importlib.import_module(f"app.Controller.{archivo}")
    entidad = SimpleNamespace(id=7, nombre="PRUEBA", nombre_sucursal="PRUEBA")
    escritor = Mock()
    mutacion = getattr(escritor, metodo_modelo)
    estado = fallo != "falso"
    mutacion.return_value = estado if metodo_modelo.startswith("eliminar") else (entidad if estado else None, estado)
    if fallo == "modelo":
        mutacion.side_effect = RuntimeError("fallo sintetico")
    monkeypatch.setattr(modulo, modelo, lambda session: escritor)
    session = Mock()
    if fallo == "commit":
        session.commit.side_effect = RuntimeError("fallo sintetico")
    funcion = getattr(getattr(modulo, clase), metodo_query)
    datos = defaultdict(lambda: "PRUEBA", {"puesto": entidad, "departamento": entidad, "sucursal": entidad})
    argumentos = {nombre: entidad for nombre in inspect.signature(funcion).parameters if nombre not in {"self", "session"}}
    argumentos.update({nombre: datos for nombre in argumentos if nombre == "datos"})
    if "diasLaborales" in argumentos:
        argumentos["diasLaborales"] = ["LUNES"]
    respuesta = funcion(SimpleNamespace(id_departamento=7), session, **argumentos)
    mutacion.assert_called_once()
    assert respuesta["exito"] is (fallo == "exito")
    if fallo == "exito":
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()
    else:
        session.rollback.assert_called_once_with()


@pytest.mark.unit
@pytest.mark.parametrize("tipo", ["fisico", "moral"])
def test_ref35_snapshot_cliente_independiente(tipo):
    from app.Model.BaseDatosModel import Clientes_fisicos, Clientes_morales, Areas_negocios, Categorias_de_clientes
    from app.Model.AdministracionEntrada import snapshot_cliente

    modelo = Clientes_fisicos if tipo == "fisico" else Clientes_morales
    cliente = modelo(id=7, nombre="PRUEBA", areas_de_negocios=Areas_negocios(id=1, nombre="AREA"), categoria=Categorias_de_clientes(id=2, nombre="CATEGORIA"))
    dto = snapshot_cliente(cliente)
    cliente.nombre = "CAMBIADO"
    cliente.categoria.nombre = "CAMBIADA"
    assert dto.id == 7 and dto.nombre == "PRUEBA"
    assert dto.categoria.nombre == "CATEGORIA"
    assert not hasattr(dto, "_sa_instance_state")
    assert not hasattr(dto.categoria, "_sa_instance_state")


@pytest.mark.qt
def test_ref36_query_personal_no_muta_offset(qtbot, monkeypatch):
    from app.Controller import EmpleadosController as modulo

    modelo = Mock()
    modelo.obtener_empleados_detallados.return_value = ([SimpleNamespace(id=7)], True)
    monkeypatch.setattr(modulo, "EmpleadosModel", lambda session: modelo)
    controlador = SimpleNamespace(cantidad_inicial_empleados=100, cantidad_final_empleados=100)
    resultado = modulo.EmpleadosController.obtener_empleados_query(controlador, Mock())
    assert resultado["exito"] is True
    assert controlador.cantidad_inicial_empleados == 100
    modelo.obtener_empleados_detallados.assert_called_once_with(offset=0, limit=100, snapshots=True)


@pytest.mark.unit
@pytest.mark.parametrize("tipo", ["fisico", "moral"])
@pytest.mark.parametrize("filtrado", [False, True])
def test_ref35_lecturas_modelo_materializan_snapshot(tipo, filtrado):
    from app.Model.BaseDatosModel import Clientes_fisicos, Clientes_morales
    from app.Model.ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales

    cliente = (Clientes_fisicos if tipo == "fisico" else Clientes_morales)(id=7, nombre="PRUEBA")
    consulta = Mock()
    for nombre in ("query", "options", "order_by", "offset", "limit", "filter"):
        getattr(consulta, nombre).return_value = consulta
    consulta.all.return_value = [cliente]
    modelo = ClientesFisicosAndMorales(consulta)
    plural = "fisicos" if tipo == "fisico" else "morales"
    nombre = f"filtrar_clientes_{plural}_por_nombre" if filtrado else f"mostrar_clientes_{plural}"
    datos, estado = getattr(modelo, nombre)(**dict(snapshots=True, **({"texto": "PRUEBA"} if filtrado else {})))
    assert estado is True
    assert datos[0].id == 7
    assert not hasattr(datos[0], "_sa_instance_state")


@pytest.mark.qt
@pytest.mark.parametrize("tipo", ["fisicos", "morales"])
def test_ref35_controlador_lectura_recibe_pagina_capturada(qtbot, monkeypatch, tipo):
    from app.Controller import ClientesController as modulo

    modelo = Mock()
    getattr(modelo, f"mostrar_clientes_{tipo}").return_value = ([], True)
    monkeypatch.setattr(modulo, "ClientesFisicosAndMorales", lambda session: modelo)
    getattr(modulo.Clientes, f"clientes_{tipo}_query")(SimpleNamespace(), Mock(), cantidad_inicial=100, cantidad_final=100)
    getattr(modelo, f"mostrar_clientes_{tipo}").assert_called_once_with(
        cantidad_inicial=100, cantidad_final=100, snapshots=True,
    )


@pytest.mark.unit
@pytest.mark.parametrize("archivo", ["ClientesController", "EmpleadosController", "SucursalesController", "DepartamentosController", "PuestosController", "RegistroInicialController", "PerfilUsuarioController"])
def test_ref36_workers_propietario_instancia_y_cierre_seguro(archivo):
    import ast
    from pathlib import Path

    arbol = ast.parse((Path(__file__).resolve().parents[1] / "app" / "Controller" / f"{archivo}.py").read_text(encoding="utf-8"))
    llamadas = [nodo for nodo in ast.walk(arbol) if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)]
    for llamada in llamadas:
        if llamada.func.attr == "create_managed_worker":
            argumentos = {kw.arg: kw.value for kw in llamada.keywords}
            assert isinstance(argumentos["owner_id"], ast.JoinedStr)
            assert argumentos["cierre_seguro"].value is True
        elif llamada.func.attr == "cleanup_owner_workers":
            owner = llamada.args[0] if llamada.args else llamada.keywords[0].value
            assert isinstance(owner, ast.JoinedStr)


@pytest.mark.qt
@pytest.mark.parametrize("archivo,clase,lista", [
    ("ClientesController", "Clientes", "lista_hilos_clientes"),
    ("EmpleadosController", "EmpleadosController", "lista_hilos_empleados"),
    ("SucursalesController", "SucursalesController", "listaHilosSucursales"),
    ("DepartamentosController", "DepartamentosController", "listaHilosDepartamentos"),
    ("PuestosController", "PuestosController", "lista_hilos_puestos"),
    ("RegistroInicialController", "Registro_personal_inicial", "lista_hilos_registroEmpleado"),
    ("PerfilUsuarioController", "Perfil", "lista_hilos_perfil"),
])
def test_ref36_ocultar_cierra_modal_y_workers(qtbot, monkeypatch, archivo, clase, lista):
    import importlib
    from PySide6.QtWidgets import QWidget, QDialog
    from PySide6.QtGui import QHideEvent

    modulo = importlib.import_module(f"app.Controller.{archivo}")
    tipo = getattr(modulo, clase)
    ventana = tipo.__new__(tipo)
    (QDialog if issubclass(tipo, QDialog) else QWidget).__init__(ventana)
    qtbot.addWidget(ventana)
    setattr(ventana, lista, ["sintetico"])
    ventana.manejadorModal = Mock()
    cleanup = Mock()
    monkeypatch.setattr(modulo.WorkerDB, "cleanup_managed_worker", cleanup)
    ventana.hideEvent(QHideEvent())
    cleanup.assert_called_once_with("sintetico")
    assert getattr(ventana, lista) == []
    ventana.manejadorModal.cerrar_modal.assert_called_once_with()


@pytest.mark.qt
@pytest.mark.parametrize("usuario,password", [("", "a" * 12), ("PRUEBA", ""), ("PRUEBA", " " + "a" * 12)])
def test_ref23_ui_rechaza_credenciales_incompletas(qtbot, monkeypatch, usuario, password):
    from app.Controller import RegistroInicialController as modulo

    ui = SimpleNamespace(txt_usuario_iniciosesion=Mock(), txt_contrasenia_usuario_iniciosesion=Mock())
    ui.txt_usuario_iniciosesion.text.return_value = usuario
    ui.txt_contrasenia_usuario_iniciosesion.text.return_value = password
    mensaje = Mock()
    monkeypatch.setattr(modulo, "Mensaje", lambda: mensaje)
    modulo.Registro_personal_inicial.agregar_usuario(SimpleNamespace(
        empleado_existente=SimpleNamespace(id=7), WindowRegistroEmpleado=ui,
    ))
    mensaje.mensaje_alerta.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("entidad", ["Clientes_fisicos", "Clientes_morales", "Empleados", "Sucursales", "Representantes_clientes_morales"])
@pytest.mark.parametrize("delta", [-1, 0, 1])
def test_ref22_longitudes_contra_metadata(entidad, delta):
    from app.Model import BaseDatosModel as bd
    from app.Model.AdministracionEntrada import validar_longitudes

    modelo = getattr(bd, entidad)
    for columna in modelo.__mapper__.columns:
        limite = getattr(columna.type, "length", None)
        if limite:
            datos = {columna.key: "A" * (limite + delta)}
            if delta > 0:
                with pytest.raises(ValueError, match=columna.key):
                    validar_longitudes(modelo, datos)
            else:
                validar_longitudes(modelo, datos)


@pytest.mark.qt
def test_ref22_ui_clientes_limites(qtbot):
    from PySide6.QtWidgets import QWidget
    from app.View.UserInterfacePy.UI_CONTROL_CLIENTES import Ui_Control_Clientes
    from app.Controller.ClientesController import Clientes
    from app.Model.AdministracionEntrada import CAMPOS_CLIENTES

    ventana = QWidget()
    qtbot.addWidget(ventana)
    ui = Ui_Control_Clientes()
    ui.setupUi(ventana)
    Clientes.configurar_limites(SimpleNamespace(WindowClient=ui))
    for widget, (modelo, campo) in CAMPOS_CLIENTES.items():
        limite = modelo.__mapper__.columns[campo].type.length
        assert getattr(ui, widget).maxLength() <= limite
    assert ui.txt_rfc_fisico.maxLength() == 13
    assert ui.txt_rfc_empre_moral.maxLength() == 12
    assert ui.txt_codigopostal_fisico.maxLength() == 5


@pytest.mark.qt
@pytest.mark.parametrize("moral", [False, True])
def test_clients_real_validators_catalog_styles_and_widths(monkeypatch, qtbot, qapp, moral):
    import app.Controller.ClientesController as module
    from PySide6.QtGui import QPalette, QValidator
    from PySide6.QtWidgets import QComboBox
    monkeypatch.setattr(module.Clientes, "listar_areas", Mock())
    monkeypatch.setattr(module.Clientes, "listar_categorias", Mock())
    messages = Mock()
    monkeypatch.setattr(module, "Mensaje", lambda: messages)
    window = module.Clientes()
    qtbot.addWidget(window)
    window.show()
    qapp.processEvents()
    for name in ("btn_btn_nuevacategoriaFisico", "btn_btn_nuevacategoriaMoral",
                 "btn_btn_nuevaareanegocio_fisico", "btn_btn_areasnegocio_moral"):
        button = getattr(window.WindowClient, name)
        assert button.property("variant") == "secondary"
        assert button.palette().color(QPalette.Button).name() == "#0c445a"
        assert button.palette().color(QPalette.ButtonText).name() == "#ffffff"
    for name in ("cajaOpciones_areasnegocio_fisico", "cajaOpciones_categoriaFisico",
                 "cajaOpciones_areasnegocio_moral", "cajaOpciones_categoriaMoral"):
        combo = getattr(window.WindowClient, name)
        assert combo.minimumWidth() >= 240 and combo.view().minimumWidth() >= 360
        assert combo.sizeAdjustPolicy() == QComboBox.AdjustToContents
    field = window.WindowClient.txt_rfc_empre_moral if moral else window.WindowClient.txt_rfc_fisico
    good = "ABC010101AB1" if moral else "GODE561231GR8"
    assert field.validator().validate(good, 0)[0] == QValidator.Acceptable
    assert field.validator().validate("INVALIDO!", 0)[0] == QValidator.Invalid
    getter = window.obtener_datos_cliente_moral if moral else window.obtener_datos_cliente_fisico
    data = {key: ("TEST" if isinstance(value, str) else value) for key, value in getter().items()}
    data.update(rfc=good, curp="GODE561231HDFRRN09")
    data.update({"numero telefono": "5512345678", "codigo postal": "01234", "correo electronico": "test@example.test",
                 "correo electronico empresa": "test@example.test", "telefono representante": "5512345678",
                 "correo electronico representante": "rep@example.test", "area de negocio": SimpleNamespace(id=1),
                 "clasificacion cliente": SimpleNamespace(id=2), "clasificacion de cliente": SimpleNamespace(id=2)})
    validate = window.validacion_campos_cliente_moral if moral else window.validacion_campos_cliente_fisico
    assert validate(data)
    data["rfc"] = "INVALIDO"
    assert not validate(data)
    assert "RFC" in messages.mensaje_informativo.call_args.args[0]


@pytest.mark.qt
def test_ref22_ui_personal_limites_ampliados(qtbot):
    from PySide6.QtWidgets import QWidget
    from app.View.UserInterfacePy.UI_REGISTRO_EMPLEADO import Ui_RegistroAdministrador
    from app.Controller.RegistroInicialController import Registro_personal_inicial

    ventana = QWidget()
    qtbot.addWidget(ventana)
    ui = Ui_RegistroAdministrador()
    ui.setupUi(ventana)
    Registro_personal_inicial.ingresar_validaciones(SimpleNamespace(WindowRegistroEmpleado=ui))
    for nombre in ("nombre", "apellidop", "apellidom", "ciudad", "estado", "pais", "calles", "avenidas", "colonia"):
        assert getattr(ui, f"txt_{nombre}").maxLength() == 100


@pytest.mark.unit
@pytest.mark.parametrize("modelo,metodo", [
    ("clientes", "agregar_cliente_fisico"), ("clientes", "agregar_cliente_moral"),
    ("clientes", "actualizar_cliente_fisico"), ("clientes", "actualizar_cliente_moral"),
    ("clientes", "agregar_representante_cliente_moral"),
    ("personal", "crear_empleado"), ("personal", "actualizar_empleado"),
    ("sucursal", "actualizar"), ("sucursal", "agregar_sucursal"),
])
def test_ref22_escrituras_rechazan_longitudes_antes_de_sql(modelo, metodo):
    from app.Model.ClientesFisicosAndMoralesModel import ClientesFisicosAndMorales
    from app.Model.EmpleadoModel import EmpleadosModel
    from app.Model.SucursalesModel import SucursalesModel

    session = Mock()
    clase = {"clientes": ClientesFisicosAndMorales, "personal": EmpleadosModel, "sucursal": SucursalesModel}[modelo]
    funcion = getattr(clase(session), metodo)
    datos = {nombre: None for nombre in inspect.signature(funcion).parameters}
    datos.pop("kwargs", None)
    datos["nombre_sucursal" if modelo == "sucursal" else "nombre"] = "A" * 301
    with pytest.raises(ValueError):
        funcion(**datos)
    assert not session.mock_calls


@pytest.mark.unit
@pytest.mark.parametrize("tipo", ["FISICO", "MORAL"])
@pytest.mark.parametrize("fallo", ["duplicado", "entrada"])
def test_lote2_importacion_savepoint_aisla_fila_y_cache(tipo, fallo, monkeypatch):
    from contextlib import contextmanager
    from app.Model import ClientesImportacion as modulo

    session = Mock()
    session.query.return_value.all.return_value = []
    objetos = []
    session.add.side_effect = objetos.append
    session.flush.side_effect = lambda: [setattr(objeto, "id", indice + 1) for indice, objeto in enumerate(objetos)]
    reversiones = []
    @contextmanager
    def savepoint():
        inicio = len(objetos)
        try:
            yield
        except Exception:
            del objetos[inicio:]
            reversiones.append(True)
            raise
    session.begin_nested = savepoint
    escritor = Mock()
    def representante(**datos):
        objeto = SimpleNamespace(**datos)
        session.add(objeto)
        session.flush()
        return objeto
    escritor.agregar_representante_cliente_moral.side_effect = representante
    llamadas = []
    def escribir(**datos):
        objeto = SimpleNamespace(**datos)
        session.add(objeto)
        llamadas.append(objeto)
        if len(llamadas) == 1:
            if fallo == "entrada":
                raise ValueError("fila sintetica invalida")
            return None, None
        return objeto, True
    getattr(escritor, "agregar_cliente_fisico" if tipo == "FISICO" else "agregar_cliente_moral").side_effect = escribir
    monkeypatch.setattr(modulo, "ClientesFisicosAndMorales", lambda session: escritor)
    fila = dict(nombre="PRUEBA", apellido_paterno="PRUEBA", apellido_materno="PRUEBA", curp="A" * 18,
                rfc="A" * 13, categoria_cliente="CAT", area_de_negocio="AREA", fecha_nacimiento="2000-01-01",
                razon_social="PRUEBA", nif="A", fecha_constitucion="2000-01-01", representante_nombre="PRUEBA")
    reporte = dict(errores=[], advertencias=[], filas=[dict(fila=2, valores=fila), dict(fila=3, valores=dict(fila, rfc="B" * 13, curp="B" * 18, razon_social="OTRA", nif="B"))])
    resultado = modulo.ClientesImportacion(session).importar_con_reporte(reporte, tipo)
    assert resultado["agregados"] == 1
    assert resultado["duplicados" if fallo == "duplicado" else "omitidos"] == 1
    assert len(reversiones) == 1
    assert llamadas[0] not in objetos
    assert len(objetos) == (4 if tipo == "MORAL" else 3)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("tipo", ["FISICO", "MORAL"])
def test_ref30_31_importacion_reporta_filas_y_no_confirma(tipo, monkeypatch):
    from app.Model import ClientesImportacion as modulo
    from app.Model.BaseDatosModel import Categorias_de_clientes, Areas_negocios

    session = Mock()
    session.begin_nested = MagicMock()
    def query(*columnas):
        consulta = Mock()
        consulta.all.return_value = (
            [SimpleNamespace(id=1, nombre="PRUEBA")] if len(columnas) == 1 and any(columnas[0] is modelo for modelo in (Categorias_de_clientes, Areas_negocios)) else []
        )
        return consulta
    session.query.side_effect = query
    escritor = Mock()
    escritor.agregar_cliente_fisico.return_value = (SimpleNamespace(id=7), True)
    escritor.agregar_cliente_moral.return_value = (SimpleNamespace(id=7), True)
    escritor.agregar_representante_cliente_moral.return_value = SimpleNamespace(id=3)
    monkeypatch.setattr(modulo, "ClientesFisicosAndMorales", lambda session: escritor)
    fila = dict(nombre="PRUEBA", apellido_paterno="PRUEBA", apellido_materno="PRUEBA", curp="A" * 18,
        rfc="A" * 13, categoria_cliente_id="1", areas_de_negocios_id="1", fecha_nacimiento="2000-01-01",
        razon_social="PRUEBA", nif="A", fecha_constitucion="2000-01-01", representante_nombre="PRUEBA",
        representante_telefono="0" * 10, representante_correo="prueba@example.invalid", representante_puesto="PRUEBA")
    reporte = {"errores": [], "advertencias": [], "filas": [
        {"fila": 2, "valores": fila}, {"fila": 4, "valores": dict(fila, nombre="A" * 256)},
        {"fila": 5, "valores": fila.copy()},
    ]}
    resultado = modulo.ClientesImportacion(session).importar_con_reporte(reporte, tipo)
    assert resultado["agregados"] == 1
    assert resultado["duplicados"] == 1
    assert resultado["omitidos"] == 1
    assert {item["fila"] for item in reporte["errores"]} == {4}
    assert {item["fila"] for item in reporte["advertencias"]} == {5}
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.qt
@pytest.mark.parametrize("tipo", ["fisicos", "morales"])
@pytest.mark.parametrize("fallo", [None, "modelo", "commit"])
def test_ref30_31_coordinador_lote_atomico(qtbot, monkeypatch, tipo, fallo):
    from app.Controller import ClientesController as modulo

    reporte = {"filas": [], "errores": [], "advertencias": []}
    monkeypatch.setattr(modulo.OperacionMasivaCsvController, "leer_con_reporte", lambda **kwargs: reporte)
    modelo = Mock()
    modelo.importar_con_reporte.return_value = dict(exito=True, agregados=2, duplicados=0, omitidos=0, reporte=reporte)
    if fallo == "modelo":
        modelo.importar_con_reporte.side_effect = RuntimeError("fallo sintetico")
    fabrica = Mock(return_value=modelo)
    fabrica.columnas = modulo.ClientesImportacion.columnas
    monkeypatch.setattr(modulo, "ClientesImportacion", fabrica)
    session = Mock()
    if fallo == "commit":
        session.commit.side_effect = RuntimeError("fallo sintetico")
    resultado = getattr(modulo.Clientes, f"importar_clientes_{tipo}_query")(SimpleNamespace(), session, "sintetico.csv")
    assert resultado["exito"] is (fallo is None)
    if fallo:
        assert resultado["agregados"] == 0
        session.rollback.assert_called_once_with()
    else:
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()