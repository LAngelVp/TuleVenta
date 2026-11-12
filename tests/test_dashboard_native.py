from datetime import date, datetime
from unittest.mock import Mock

import pytest


@pytest.mark.unit
@pytest.mark.parametrize('metodo', ['obtener_utilidad_categorias', 'obtener_utilidad_productos',
                                  'obtener_patron_horario', 'obtener_patron_semanal',
                                  'obtener_liquidez', 'obtener_inversion_proveedores', 'obtener_cortes_caja'])
def test_dashboard_executive_sql_date_limits(monkeypatch, metodo):
    from sqlalchemy.orm import Query, Session
    from sqlalchemy.dialects import postgresql
    from app.Model.DashboardModel import DashboardModel

    statements = []

    def filas(query):
        statements.append(query.statement.compile(dialect=postgresql.dialect()))
        return []

    monkeypatch.setattr(Query, 'all', filas)
    model = DashboardModel(Session())
    getattr(model, metodo)(date(2026, 11, 2), date(2026, 11, 1), 7)
    assert statements
    for statement in statements:
        assert datetime(2026, 11, 1) in statement.params.values()
        assert datetime(2026, 11, 2, 23, 59, 59, 999999) in statement.params.values()
        if metodo != 'obtener_cortes_caja':
            assert 7 in statement.params.values()
            assert 'sucursal_id' in str(statement)
        else:
            assert 'fecha_cierre' in str(statement)
            assert 'sucursal_id' not in str(statement)
        if metodo not in {'obtener_cortes_caja', 'obtener_inversion_proveedores'}:
            assert 'CANCELADA' in statement.params.values()
            assert 'activo IS true' in str(statement)


@pytest.mark.unit
def test_dashboard_summary_filters_inclusive_and_branch():
    from app.Model.DashboardModel import DashboardModel
    from app.Model.BaseDatosModel import Ventas
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Session

    model = DashboardModel(Session())
    query = model._filtrar_resumen(model.session.query(Ventas), Ventas,
                                  date(2026, 11, 1), date(2026, 11, 2), 7)
    compiled = query.statement.compile(dialect=postgresql.dialect())
    assert datetime(2026, 11, 1) in compiled.params.values()
    assert datetime(2026, 11, 2, 23, 59, 59, 999999) in compiled.params.values()
    assert 7 in compiled.params.values()
    assert 'sucursal_id' in str(compiled)


@pytest.mark.qt
def test_dashboard_native_filters_and_charts(monkeypatch, qtbot):
    from PySide6.QtCharts import QChartView
    from PySide6.QtCore import Qt
    from app.Controller.DashboardController import DashboardController

    monkeypatch.setattr(DashboardController, '_cargar_estados_dashboard', lambda self: None)
    monkeypatch.setattr(DashboardController, '_cargar_tab_dashboard', lambda *args, **kwargs: None)
    request = Mock()
    monkeypatch.setattr(DashboardController, '_solicitar_dashboard', request)
    window = DashboardController(permisos_usuario=['ADMINISTRADOR'])
    qtbot.addWidget(window)
    window.show()
    qtbot.mouseClick(window.resumen_aplicar, Qt.LeftButton)
    assert request.call_args.args[0] == 'resumen'
    assert request.call_args.args[1]['fecha_inicio'] == window.resumen_inicio.date().toPython()
    data = dict(kpis=dict(ventas=100, ticket=100, ordenes=2, ganancia=40),
                tiempo=[dict(label='2026-11-01', ingresos=100, ganancia=40)],
                productos=[dict(label='Producto', value=2, monto=100)],
                pagos=[dict(label='Efectivo', value=100)],
                inventario=[dict(label='Agotados', value=2)], sucursales=[])
    window.cargar_dashboard_resumen(resultado=data)
    assert all(isinstance(view, QChartView) for view in window.resumen_graficas)
    assert all(view.chart().series() for view in window.resumen_graficas)
    assert window.resumen_kpis['Ventas totales'].text() == '$100.00'


@pytest.mark.unit
@pytest.mark.parametrize('metodo', ['obtener_ventas_tiempo', 'obtener_top_productos', 'obtener_ingresos_pago', 'obtener_kpis'])
@pytest.mark.parametrize('invertido', [False, True])
def test_dashboard_metric_queries_date_bounds(monkeypatch, metodo, invertido):
    from sqlalchemy.orm import Query, Session
    from sqlalchemy.dialects import postgresql
    from app.Model.DashboardModel import DashboardModel

    consultas = []

    def registrar(query):
        compiled = query.statement.compile(dialect=postgresql.dialect())
        consultas.append(compiled)

    def filas(query):
        registrar(query)
        return []

    def resumen(query):
        registrar(query)
        return (0, 0)

    def escalar(query):
        registrar(query)
        return 0

    monkeypatch.setattr(Query, 'all', filas)
    monkeypatch.setattr(Query, 'one', resumen)
    monkeypatch.setattr(Query, 'scalar', escalar)
    inicio, fin = date(2026, 11, 1), date(2026, 11, 2)
    if invertido:
        inicio, fin = fin, inicio
    getattr(DashboardModel(Session()), metodo)(inicio, fin, 7)
    assert consultas
    for query in consultas:
        assert datetime(2026, 11, 1) in query.params.values()
        assert datetime(2026, 11, 2, 23, 59, 59, 999999) in query.params.values()
        assert 7 in query.params.values()


@pytest.mark.qt
@pytest.mark.parametrize('tipo', ['barras', 'horizontal', 'lineas', 'pastel'])
def test_dashboard_native_hover_exact_values(qtbot, tipo):
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QToolTip
    from app.View.UserInterfacePy.DashboardResumen import crear_chart_view, renderizar

    view = crear_chart_view(None)
    qtbot.addWidget(view)
    view.show()
    renderizar(view, 'Prueba', [dict(label='Producto completo', value=12.34567, monto=98.765)],
               [('Cantidad', 'value', '#2563EB')], tipo, [('Monto', 'monto', 'currency')])
    serie = view.chart().series()[0]
    if tipo == 'pastel':
        serie.slices()[0].hovered.emit(True)
    elif tipo == 'lineas':
        serie.hovered.emit(QPointF(0, 12.34567), True)
    else:
        serie.barSets()[0].hovered.emit(True, 0)
    assert 'Producto completo' in QToolTip.text()
    assert '12.34567' in QToolTip.text()
    if tipo in {'barras', 'horizontal'}:
        assert '98.765' in QToolTip.text()
    renderizar(view, 'Prueba', [], tipo=tipo)
    assert 'Sin datos' in view.chart().title()


@pytest.mark.qt
def test_dashboard_summary_real_worker_keeps_gui_responsive(monkeypatch, qtbot):
    from threading import Event, get_ident
    from PySide6.QtCore import QTimer
    import app.Controller.Hilo_consultas as workers
    from app.Controller.DashboardController import DashboardController
    from app.Model.DashboardModel import DashboardModel

    entered, release, gui_tick = Event(), Event(), Event()
    gui_thread = get_ident()
    database = Mock()
    session = Mock()
    database.abrir_sesion.return_value = session
    database.__enter__ = Mock(return_value=database)
    database.__exit__ = Mock(return_value=False)

    def query(model, **filtros):
        assert model.session is session
        assert get_ident() != gui_thread
        entered.set()
        if not release.wait(5):
            raise RuntimeError('timeout')
        return dict(kpis=dict(ventas=123, ticket=123, ordenes=1, ganancia=23),
                    tiempo=[], productos=[], pagos=[], inventario=[], sucursales=[]), True, 'OK'

    monkeypatch.setattr(workers, 'Conexion_base_datos', Mock(return_value=database))
    monkeypatch.setattr(DashboardModel, 'get_summary_dashboard', query)
    monkeypatch.setattr(DashboardController, '_cargar_estados_dashboard', lambda self: None)
    monkeypatch.setattr(DashboardController, '_cargar_tab_dashboard', lambda *args, **kwargs: None)
    window = DashboardController(permisos_usuario=['ADMINISTRADOR'])
    qtbot.addWidget(window)
    window.cargar_dashboard_resumen()
    identificador = window._dashboard_workers['resumen']
    try:
        qtbot.waitUntil(entered.is_set)
        QTimer.singleShot(0, gui_tick.set)
        qtbot.waitUntil(gui_tick.is_set)
        assert window.resumen_kpis['Ventas totales'].text() == '...'
        release.set()
        qtbot.waitUntil(lambda: window.resumen_kpis['Ventas totales'].text() == '$123.00')
    finally:
        release.set()
        workers.WorkerDB.cleanup_managed_worker(identificador)
        qtbot.waitUntil(lambda: workers.WorkerDB.get_managed_worker(identificador) is None)
    database.__exit__.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize('metodo,filas,campos', [
    ('obtener_utilidad_categorias', [(1, 'Categoria', -12.5, 90)], ['costo_final', 'costo_inicial', 'cantidad', 'subtotal', 'descuento', 'categoria_id']),
    ('obtener_utilidad_productos', [(1, 'Producto', 12.5, 90)], ['costo_final', 'cantidad', 'subtotal', 'descuento']),
    ('obtener_inversion_proveedores', [(1, 'Proveedor', 100, 2)], ['total_compra', 'proveedor_id']),
    ('obtener_cortes_caja', [(date(2026, 11, 1), 12, -3, 2)], ['diferencia', 'fecha_cierre', 'estado']),
])
def test_dashboard_executive_aggregates_dto(monkeypatch, metodo, filas, campos):
    from sqlalchemy.orm import Query, Session
    from sqlalchemy.dialects import postgresql
    from app.Model.DashboardModel import DashboardModel

    compiled = []

    def resultado(query):
        compiled.append(query.statement.compile(dialect=postgresql.dialect()))
        return filas

    monkeypatch.setattr(Query, 'all', resultado)
    data = getattr(DashboardModel(Session()), metodo)(date(2026, 11, 1), date(2026, 11, 2))
    assert len(data) == 1
    for campo in campos:
        assert campo in str(compiled[0])
    if 'utilidad' in metodo:
        assert data[0]['value'] == filas[0][2]
        assert data[0]['ingresos'] == 90
        assert 'precio' not in str(compiled[0])
        assert 'sum(' in str(compiled[0])
    if metodo == 'obtener_cortes_caja':
        assert data[0]['sobrante'] == 12
        assert data[0]['faltante'] == -3
        assert str(compiled[0]).count('CASE') == 2


@pytest.mark.unit
@pytest.mark.parametrize('metodo,esperado', [('obtener_salud_inventario', 4), ('obtener_riesgo_caducidad', 6),
                                          ('obtener_cartera_clientes', 0), ('obtener_patron_horario', 24),
                                          ('obtener_patron_semanal', 7), ('obtener_liquidez', 3)])
def test_dashboard_executive_empty_and_current_snapshots(monkeypatch, metodo, esperado):
    from datetime import timedelta
    from sqlalchemy.orm import Query, Session
    from sqlalchemy.dialects import postgresql
    from app.Model.DashboardModel import DashboardModel

    statements = []

    def filas(query):
        statements.append(query.statement.compile(dialect=postgresql.dialect()))
        return []

    monkeypatch.setattr(Query, 'all', filas)
    model = DashboardModel(Session())
    hoy = date(2026, 11, 12)
    if metodo == 'obtener_riesgo_caducidad':
        data = model.obtener_riesgo_caducidad(referencia=hoy)
        assert 'fecha_vencimiento IS NULL' in str(statements[0])
        for dias in (0, 7, 15, 30):
            assert hoy + timedelta(days=dias) in statements[0].params.values()
        assert 'existencia >' in str(statements[0])
    elif metodo in {'obtener_salud_inventario', 'obtener_cartera_clientes'}:
        data = getattr(model, metodo)()
    else:
        data = getattr(model, metodo)(hoy, hoy)
    assert len(data) == esperado
    assert all(item['value'] == 0 for item in data)
    if metodo in {'obtener_salud_inventario', 'obtener_riesgo_caducidad', 'obtener_cartera_clientes'}:
        assert 'sucursal_id' not in str(statements[0])
        assert 'Ventas' not in str(statements[0])


@pytest.mark.unit
def test_dashboard_executive_credit_classification_and_no_expiry(monkeypatch):
    from sqlalchemy.orm import Query, Session
    from app.Model.DashboardModel import DashboardModel

    model = DashboardModel(Session())
    monkeypatch.setattr(Query, 'all', lambda query: [('Crédito al cliente', 50), ('Tarjeta de crédito', 100),
                                                 ('Efectivo', 40), ('Credito', 20), ('Otro', 5)])
    data = model.obtener_liquidez(date(2026, 11, 1), date(2026, 11, 2))
    assert {item['label']: item['value'] for item in data} == {'Credito': 70, 'Contado': 140, 'Sin clasificar': 5}
    monkeypatch.setattr(Query, 'all', lambda query: [('Sin caducidad', 2, 5), ('0-7 dias', 1, 3)])
    data = model.obtener_riesgo_caducidad(date(2026, 11, 12))
    assert next(item for item in data if item['label'] == 'Sin caducidad')['value'] == 2
    assert next(item for item in data if item['label'] == 'Vencidos')['value'] == 0


@pytest.mark.qt
def test_dashboard_executive_tabs_tooltips_and_late_results(monkeypatch, qtbot):
    from PySide6.QtWidgets import QToolTip
    import app.Controller.DashboardController as module

    monkeypatch.setattr(module.DashboardController, '_cargar_estados_dashboard', lambda self: None)
    monkeypatch.setattr(module.DashboardController, '_cargar_tab_dashboard', lambda *args, **kwargs: None)
    worker = Mock()
    connect = Mock()
    monkeypatch.setattr(module.WorkerDB, 'create_managed_worker', Mock(side_effect=['primero', 'segundo']))
    monkeypatch.setattr(module.WorkerDB, 'get_managed_worker', Mock(return_value=worker))
    monkeypatch.setattr(module.WorkerDB, 'connect_managed_signals', connect)
    monkeypatch.setattr(module.WorkerDB, 'cleanup_managed_worker', Mock())
    window = module.DashboardController(permisos_usuario=['ADMINISTRADOR'])
    qtbot.addWidget(window)
    window.resize(1366, 768)
    window.show()
    window.cargar_dashboard_resumen()
    anterior = connect.call_args.kwargs['resultado_callback']
    snapshot = worker.ejecutar.call_args.kwargs['filtros']
    window.resumen_inicio.setDate(window.resumen_inicio.date().addDays(1))
    window.cargar_dashboard_resumen()
    assert snapshot['fecha_inicio'] != worker.ejecutar.call_args.kwargs['filtros']['fecha_inicio']
    assert module.WorkerDB.create_managed_worker.call_args.kwargs['cierre_seguro'] is True
    datos = {clave: [dict(label='Decision', value=-12.345, ingresos=90, unidades=3, limite=100,
                          ordenes=2, sobrante=5, faltante=-12.345, cortes=2)]
             for clave in window.resumen_ejecutivas}
    connect.call_args.kwargs['resultado_callback']({'exito': True, 'data': {'ejecutivo': datos}})
    for indice in window.resumen_paginas:
        window.resumen_tabs.setCurrentIndex(indice)
        qtbot.wait(10)
        for view in window.resumen_ejecutivas.values():
            if not view.isVisible():
                continue
            assert view.width() >= 300
            assert view.height() >= 280
            image = view.grab().toImage()
            assert not image.isNull()
            serie = view.chart().series()[0]
            barras = serie.barSets()[-1]
            barras.hovered.emit(True, 0)
            assert 'Decision' in QToolTip.text()
            assert '-12.345' in QToolTip.text()
    anterior({'exito': True, 'data': {'ejecutivo': {}}})
    assert all('Sin datos' not in view.chart().title() for view in window.resumen_ejecutivas.values())


@pytest.mark.qt
@pytest.mark.parametrize('permiso,seccion', [('CREARVENTA', 'ventas'), ('CREARCOMPRA', 'compras'), ('CREARPRODUCTO', 'inventario')])
def test_dashboard_executive_permissions_preserved(monkeypatch, qtbot, permiso, seccion):
    from app.Controller.DashboardController import DashboardController

    monkeypatch.setattr(DashboardController, '_cargar_estados_dashboard', lambda self: None)
    monkeypatch.setattr(DashboardController, '_cargar_tab_dashboard', lambda *args, **kwargs: None)
    request = Mock()
    monkeypatch.setattr(DashboardController, '_solicitar_dashboard', request)
    window = DashboardController(permisos_usuario=[permiso])
    qtbot.addWidget(window)
    window.cargar_dashboard_resumen()
    assert request.call_args.args[1]['secciones'] == [seccion]
    for indice, familia in window.resumen_paginas.items():
        assert window.resumen_tabs.isTabVisible(indice) is (familia == seccion)