from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QAbstractButton, QAbstractItemView, QFrame, QGroupBox, QLabel, QSizePolicy, QTableWidget, QWidget


PRIMARY_BUTTON_HINTS = (
    "agregar",
    "guardar",
    "registrar",
    "crear",
    "aceptar",
    "aplicar",
    "cobrar",
    "enviar",
    "recibir",
    "generar",
    "terminar",
)

DANGER_BUTTON_HINTS = (
    "cancelar",
    "eliminar",
    "borrar",
    "desactivar",
    "cerrar",
    "salir",
    "quitar",
)

SECONDARY_BUTTON_HINTS = (
    "buscar",
    "refrescar",
    "editar",
    "modificar",
    "ver",
    "mostrar",
    "consultar",
    "paginar",
    "obtener",
    "filtrar",
    "detalle",
    "seleccionar",
    "importar",
    "exportar",
)

PANEL_NAME_EXCLUDE = {
    "contenedor_paginas",
    "contenedortabglobal",
    "contenedor_pila",
    "wpc_contenedor_pila",
    "contenedor_controlcentral",
    "contenedor_general",
    "widget",
    "scrollarea",
}

PANEL_NAME_HINTS = (
    "contenedor",
    "formulario",
    "detalle",
    "resumen",
    "credito",
    "descuento",
    "perfil",
    "datos",
    "acciones",
    "opciones",
    "filtro",
    "tabla",
    "busqueda",
    "panel",
    "tarjeta",
    "grupo",
    "card",
)

DRAG_HANDLE_HINTS = (
    "contenedor_encabezado",
    "contenedormodal_encabezado",
    "contenedor_principal",
    "contenedormodal_general",
    "encabezado",
    "header",
    "contenedor",
    "principal",
)


MODULE_STYLESHEET = """
QWidget[themedModule="true"],
QDialog[themedModule="true"] {
    background-color: #F8FAFC;
    color: #0F172A;
}
QWidget[transparentWindow="true"],
QDialog[transparentWindow="true"] {
    background-color: transparent;
}
QFrame[panel="true"],
QGroupBox[panel="true"] {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
}
QGroupBox[panel="true"] {
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 700;
}
QGroupBox[panel="true"]::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #0F172A;
}
QLabel {
    color: #0F172A;
}
QLabel[role="title"] {
    color: #0F172A;
    font-size: 20px;
    font-weight: 700;
}
QLabel[role="accent"] {
    color: #5A7D8F;
    font-weight: 700;
}
QLabel[role="successAccent"] {
    color: #15803D;
    font-size: 22px;
    font-weight: 800;
}
QLabel[role="caption"] {
    color: #64748B;
}
QLineEdit,
QPlainTextEdit,
QComboBox,
QDateEdit,
QSpinBox,
QDoubleSpinBox {
    min-height: 38px;
    padding: 0 12px;
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    selection-background-color: #5A7D8F;
    selection-color: #FFFFFF;
}
QPlainTextEdit {
    padding: 10px 12px;
}
QLineEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 2px solid #5A7D8F;
}
QLineEdit:read-only,
QPlainTextEdit:read-only {
    background-color: #F8FAFC;
    color: #64748B;
}
QComboBox::drop-down,
QDateEdit::drop-down,
QSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button {
    border: none;
    background: transparent;
    width: 20px;
}
QPushButton,
QToolButton {
    min-height: 38px;
    padding: 0 16px;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    color: #0F172A;
    font-weight: 700;
}
QPushButton:hover,
QToolButton:hover {
    background-color: #F1F5F9;
}
QPushButton:pressed,
QToolButton:pressed {
    background-color: #E2E8F0;
}
QPushButton[variant="primary"],
QToolButton[variant="primary"] {
    background-color: #15803D;
    border-color: #15803D;
    color: #FFFFFF;
}
QPushButton[variant="primary"]:hover,
QToolButton[variant="primary"]:hover {
    background-color: #166534;
    border-color: #166534;
}
QPushButton[variant="primary"]:pressed,
QToolButton[variant="primary"]:pressed {
    background-color: #14532D;
    border-color: #14532D;
}
QPushButton[variant="secondary"],
QToolButton[variant="secondary"] {
    background-color: #5A7D8F;
    border-color: #5A7D8F;
    color: #FFFFFF;
}
QPushButton[variant="secondary"]:hover,
QToolButton[variant="secondary"]:hover {
    background-color: #4C6C7B;
    border-color: #4C6C7B;
}
QPushButton[variant="secondary"]:pressed,
QToolButton[variant="secondary"]:pressed {
    background-color: #405A66;
    border-color: #405A66;
}
QPushButton[variant="danger"],
QToolButton[variant="danger"] {
    background-color: #EF4444;
    border-color: #EF4444;
    color: #FFFFFF;
}
QPushButton[variant="danger"]:hover,
QToolButton[variant="danger"]:hover {
    background-color: #DC2626;
    border-color: #DC2626;
}
QPushButton[variant="danger"]:pressed,
QToolButton[variant="danger"]:pressed {
    background-color: #B91C1C;
    border-color: #B91C1C;
}
QPushButton:disabled,
QToolButton:disabled,
QLineEdit:disabled,
QPlainTextEdit:disabled,
QComboBox:disabled,
QDateEdit:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled {
    background-color: #E2E8F0;
    border-color: #E2E8F0;
    color: #94A3B8;
}
QTableView,
QTableWidget,
QListView,
QTreeView {
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    gridline-color: #E2E8F0;
    selection-background-color: #5A7D8F;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #F1F5F9;
    color: #0F172A;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    padding: 10px 8px;
    font-weight: 700;
}
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    background-color: #F1F5F9;
    top: -1px;
}
QTabBar::tab {
    background-color: #E2E8F0;
    color: #64748B;
    padding: 10px 16px;
    margin-right: 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    border-bottom-color: #FFFFFF;
}
QCheckBox,
QRadioButton {
    color: #0F172A;
    spacing: 8px;
}
QCheckBox::indicator,
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
}
QCheckBox::indicator {
    border-radius: 5px;
}
QRadioButton::indicator {
    border-radius: 9px;
}
QCheckBox::indicator:checked,
QRadioButton::indicator:checked {
    background-color: #15803D;
    border-color: #15803D;
}
QMenu {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 12px;
    border-radius: 8px;
}
QMenu::item:selected {
    background-color: #5A7D8F;
    color: #FFFFFF;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #5A7D8F;
    color: #FFFFFF;
    border: none;
}
QCalendarWidget QToolButton {
    background-color: transparent;
    border: none;
    color: #FFFFFF;
    font-weight: 700;
}
QCalendarWidget QWidget#qt_calendar_weekdaybar {
    background-color: #F1F5F9;
    color: #64748B;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #FFFFFF;
    color: #0F172A;
    selection-background-color: #5A7D8F;
    selection-color: #FFFFFF;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    border: none;
    background: transparent;
    height: 0;
}
"""


ACCESS_STYLESHEET = """
#Inicio_Sesion,
#Saludo_bienvenida,
#Bienvenida {
    background: transparent;
    color: #0F172A;
}
#principal {
    background-color: #F8FAFC;
    border: 1px solid #D7E4F3;
    border-radius: 28px;
}
#principal QLabel,
#Conteneror_imgLogin QLabel,
#contenedor QLabel {
    background: transparent;
}
#Conteneror_imgLogin {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #F6FAFD,
        stop: 1 #EAF2F8
    );
    border: 1px solid #D7E4F3;
    border-radius: 30px;
}
#imgFormulario {
    background: transparent;
    image: url(:/logos/Icons/logos/tuleVenta.png);
    padding: 38px;
}
#img_Login {
    image: url(:/Icons/IconosSVG/security.png);
}
#txt_User,
#txt_Password {
    min-height: 30px;
    max-height: 30px;
    padding: 0 10px;
    background-color: #FCFDFE;
    color: #0F172A;
    border: 1px solid #D7E4F3;
    border-radius: 10px;
    selection-background-color: #5A7D8F;
    selection-color: #FFFFFF;
}
#txt_User:focus,
#txt_Password:focus {
    border: 2px solid #5A7D8F;
    background-color: #FFFFFF;
}
#txt_User::placeholder,
#txt_Password::placeholder {
    color: #94A3B8;
}
#btnAceptar,
#btn_entrar,
#btn_btn_registrar {
    min-height: 32px;
    padding: 0 18px;
    background-color: #15803D;
    color: #FFFFFF;
    border: 1px solid #15803D;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
}
#btnAceptar:hover,
#btn_entrar:hover,
#btn_btn_registrar:hover {
    background-color: #166534;
    border-color: #166534;
}
#btnAceptar:pressed,
#btn_entrar:pressed,
#btn_btn_registrar:pressed {
    background-color: #14532D;
    border-color: #14532D;
}
#btn_entrar {
    min-height: 40px;
    font-size: 18px;
}
#btnCerrar,
#btnMinimizar {
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    padding: 0;
    border-radius: 12px;
    background-color: #5A7D8F;
    border: 1px solid #5A7D8F;
}
#btnMinimizar:hover {
    background-color: #4C6C7B;
    border-color: #4C6C7B;
}
#btnMinimizar:pressed {
    background-color: #405A66;
    border-color: #405A66;
}
#btnCerrar {
    background-color: #EF4444;
    border-color: #EF4444;
}
#btnCerrar:hover {
    background-color: #DC2626;
    border-color: #DC2626;
}
#btnCerrar:pressed {
    background-color: #B91C1C;
    border-color: #B91C1C;
}
#contenedor {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #FFFFFF,
        stop: 1 #F8FAFC
    );
    border: 1px solid #D7E4F3;
    border-radius: 24px;
}
#etiquetaBuendia {
    color: #5A7D8F;
    font-size: 28px;
    font-weight: 700;
}
#etiquetaNombreUsuario {
    color: #0F172A;
    font-size: 34px;
    font-weight: 800;
}
#etiquetaEslogan {
    color: #475569;
    font-size: 13px;
    font-weight: 600;
    padding: 0 18px;
}
#etiqueta_titulo {
    color: #0F172A;
    font-size: 22px;
    font-weight: 800;
}
#etiqueta_imagen,
#label {
    background: transparent;
}
"""


TITLE_SCALE_STYLESHEET = """
QLabel[role="title"],
QLabel[objectName^="etiquetaTitulo_"],
QLabel[objectName*="etiquetaTitulo_"] {
    font-size: 17px;
    font-weight: 700;
}

QLabel[role="subtitle"],
QLabel[objectName^="etiquetasubtitulo_"],
QLabel[objectName*="etiquetasubtitulo_"] {
    font-size: 16px;
    font-weight: 700;
}
"""


def apply_module_theme(root_widget):
    if root_widget is None:
        return

    root_widget.setProperty("themedModule", True)
    _sync_window_state(root_widget)

    _decorate_panels(root_widget)
    _decorate_buttons(root_widget)
    _decorate_labels(root_widget)
    _decorate_views(root_widget)
    root_widget.setStyleSheet(MODULE_STYLESHEET + TITLE_SCALE_STYLESHEET)
    QTimer.singleShot(0, lambda widget=root_widget: _sync_window_state(widget, refresh_style=True))


def apply_access_theme(root_widget):
    if root_widget is None:
        return

    root_widget.setStyleSheet(ACCESS_STYLESHEET + TITLE_SCALE_STYLESHEET)


def apply_title_text_scale(root_widget):
    if root_widget is None:
        return

    stylesheet = root_widget.styleSheet() or ""
    if TITLE_SCALE_STYLESHEET.strip() in stylesheet:
        return

    root_widget.setStyleSheet(stylesheet + "\n" + TITLE_SCALE_STYLESHEET)


def _sync_window_state(root_widget, refresh_style=False):
    try:
        is_transparent = root_widget.testAttribute(Qt.WA_TranslucentBackground) or bool(root_widget.windowFlags() & Qt.FramelessWindowHint)
    except RuntimeError:
        return

    root_widget.setProperty("transparentWindow", bool(is_transparent))
    if refresh_style:
        root_widget.setStyleSheet(MODULE_STYLESHEET + TITLE_SCALE_STYLESHEET)


def _decorate_panels(root_widget):
    for child, depth in _iter_widget_tree(root_widget, max_depth=2):
        if not isinstance(child, (QFrame, QGroupBox)):
            continue

        object_name = (child.objectName() or "").strip().lower()
        if not object_name or object_name in PANEL_NAME_EXCLUDE:
            continue

        if isinstance(child, QGroupBox) or _is_panel_candidate(object_name, depth):
            child.setProperty("panel", True)


def _decorate_buttons(root_widget):
    for button in root_widget.findChildren(QAbstractButton):
        if button.property("variant"):
            continue

        button_key = f"{button.objectName()} {button.text()}".strip().lower()
        if not button_key:
            continue

        if any(hint in button_key for hint in DANGER_BUTTON_HINTS):
            button.setProperty("variant", "danger")
        elif any(hint in button_key for hint in PRIMARY_BUTTON_HINTS):
            button.setProperty("variant", "primary")
        elif any(hint in button_key for hint in SECONDARY_BUTTON_HINTS):
            button.setProperty("variant", "secondary")


def _decorate_labels(root_widget):
    for label in root_widget.findChildren(QLabel):
        if label.property("role"):
            continue

        object_name = (label.objectName() or "").strip().lower()
        if not object_name:
            continue

        if "totalresultado" in object_name or ("total" in object_name and "resultado" in object_name):
            label.setProperty("role", "successAccent")
        elif "resultado" in object_name or "status" in object_name:
            label.setProperty("role", "accent")
        elif "subtitulo" in object_name:
            label.setProperty("role", "subtitle")
        elif "titulo" in object_name or "encabezado" in object_name:
            label.setProperty("role", "title")
        elif object_name.startswith("etiqueta") or object_name.startswith("label"):
            label.setProperty("role", "caption")


def _decorate_views(root_widget):
    for view in root_widget.findChildren(QAbstractItemView):
        _apply_view_density(view)


def stabilize_item_view(view, min_height=220):
    if view is None:
        return

    _apply_view_density(view)
    if view.minimumHeight() < min_height:
        view.setMinimumHeight(min_height)
    view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)


def _apply_view_density(view):
    view.setAlternatingRowColors(True)
    view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

    horizontal_header_getter = getattr(view, "horizontalHeader", None)
    if callable(horizontal_header_getter):
        horizontal_header = horizontal_header_getter()
        if horizontal_header is not None and horizontal_header.minimumHeight() < 38:
            horizontal_header.setMinimumHeight(38)

    vertical_header_getter = getattr(view, "verticalHeader", None)
    if callable(vertical_header_getter):
        vertical_header = vertical_header_getter()
        if vertical_header is not None:
            if vertical_header.minimumSectionSize() < 28:
                vertical_header.setMinimumSectionSize(28)
            if vertical_header.defaultSectionSize() < 34:
                vertical_header.setDefaultSectionSize(34)

    if isinstance(view, QTableWidget):
        view.setShowGrid(False)


def configure_child_modal(root_widget, drag_widget=None, modal=True, keep_on_top=True, frameless=False):
    if root_widget is None:
        return

    root_widget.setWindowFlag(Qt.WindowType.Dialog, True)
    if frameless:
        root_widget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    if keep_on_top:
        root_widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    if modal and hasattr(root_widget, "setWindowModality"):
        root_widget.setWindowModality(Qt.WindowModality.ApplicationModal)
    if frameless:
        _ensure_escape_shortcut(root_widget)

    enable_window_drag(root_widget, drag_widget)


def enable_window_drag(root_widget, drag_widget=None):
    if root_widget is None:
        return

    drag_widget = drag_widget or _find_drag_handle(root_widget)
    if drag_widget is None:
        return

    installed_filters = getattr(root_widget, "_copilot_drag_filters", [])
    if any(getattr(filter_obj, "drag_target", None) is drag_widget for filter_obj in installed_filters):
        return

    drag_filter = _WindowDragFilter(root_widget, drag_widget)
    drag_widget.installEventFilter(drag_filter)
    drag_widget.setCursor(Qt.CursorShape.OpenHandCursor)
    installed_filters.append(drag_filter)
    root_widget._copilot_drag_filters = installed_filters


def bring_window_to_front(root_widget):
    if root_widget is None:
        return

    root_widget.show()
    root_widget.raise_()
    root_widget.activateWindow()


def _ensure_escape_shortcut(root_widget):
    if getattr(root_widget, "_copilot_escape_shortcut", None) is not None:
        return

    shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), root_widget)
    shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
    shortcut.activated.connect(root_widget.close)
    root_widget._copilot_escape_shortcut = shortcut


class _WindowDragFilter(QObject):
    def __init__(self, window_widget, drag_target):
        super().__init__(window_widget)
        self.window_widget = window_widget
        self.drag_target = drag_target
        self.drag_offset = None

    def eventFilter(self, watched, event):
        if watched is not self.drag_target:
            return False

        if event.type() == QEvent.Type.MouseButtonPress and getattr(event, "button", lambda: None)() == Qt.MouseButton.LeftButton:
            global_point = _extract_global_point(event)
            if global_point is not None:
                self.drag_offset = global_point - self.window_widget.frameGeometry().topLeft()
        elif event.type() == QEvent.Type.MouseMove and self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            global_point = _extract_global_point(event)
            if global_point is not None:
                self.window_widget.move(global_point - self.drag_offset)
                return True
        elif event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.WindowDeactivate):
            self.drag_offset = None

        return False


def _extract_global_point(event):
    global_position = getattr(event, "globalPosition", None)
    if callable(global_position):
        return global_position().toPoint()

    global_pos = getattr(event, "globalPos", None)
    if callable(global_pos):
        return global_pos()

    return None


def _find_drag_handle(root_widget):
    for child in root_widget.findChildren(QWidget):
        object_name = (child.objectName() or "").strip().lower()
        if object_name in DRAG_HANDLE_HINTS:
            return child

    for child, _depth in _iter_widget_tree(root_widget, max_depth=1):
        object_name = (child.objectName() or "").strip().lower()
        if object_name.startswith(("contenedor", "header", "encabezado", "principal")):
            return child

    return root_widget


def _iter_widget_tree(parent_widget, max_depth, depth=0):
    if depth >= max_depth:
        return

    for child in parent_widget.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
        yield child, depth
        yield from _iter_widget_tree(child, max_depth, depth + 1)


def _is_panel_candidate(object_name, depth):
    if any(hint in object_name for hint in PANEL_NAME_HINTS):
        return True
    return depth == 0 and object_name.startswith(("frame", "widget", "control", "principal"))