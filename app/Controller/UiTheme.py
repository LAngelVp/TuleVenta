import re
from types import MappingProxyType

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSpinBox, QComboBox,
                               QFrame, QGroupBox, QLabel, QLineEdit, QPlainTextEdit,
                               QSizePolicy, QTableWidget, QWidget)
from app.runtime_paths import ruta_recurso
from app.Source import ibootstrap_rc  # noqa: F401  (registra los iconos usados por el QSS)
from .ImagenEstatica import mostrar_imagen_estatica


COLOR_TOKENS = MappingProxyType({
    "surface.main": "#F6F8F7",
    "surface.panel": "#FFFFFF",
    "surface.table": "#FFFFFF",
    "surface.table.alternate": "#EEF3F1",
    "border.subtle": "#DCE4E1",
    "border.control": "#52615E",
    "brand.primary": "#206338",
    "brand.primary.hover": "#194F2D",
    "brand.primary.pressed": "#123C22",
    "brand.secondary": "#0C445A",
    "brand.secondary.hover": "#093547",
    "brand.secondary.pressed": "#072938",
    "text.main": "#182322",
    "text.secondary": "#52615E",
    "text.onAccent": "#FFFFFF",
    "semantic.success": "#206338",
    "semantic.warning": "#B45309",
    "semantic.danger": "#B91C1C",
    "semantic.danger.hover": "#991B1B",
    "semantic.danger.pressed": "#7F1D1D",
    "semantic.info": "#0C445A",
    "focus.ring": "#0C445A",
    "surface.disabled": "#DCE4E1",
    "text.disabled": "#52615E",
})


def render_qss(template):
    return re.sub(r"\$\{([\w.]+)\}", lambda match: COLOR_TOKENS[match.group(1)], template)


def official_window_icon():
    return QIcon(str(ruta_recurso("app", "Source", "Icons", "logos", "TuleVentaIcon.ico")))


def application_palette():
    palette = QPalette()
    roles = {
        QPalette.Window: "surface.main", QPalette.Base: "surface.panel",
        QPalette.AlternateBase: "surface.table.alternate", QPalette.Text: "text.main",
        QPalette.WindowText: "text.main", QPalette.Button: "surface.panel",
        QPalette.ButtonText: "text.main", QPalette.Highlight: "brand.secondary",
        QPalette.HighlightedText: "text.onAccent", QPalette.Mid: "border.control",
        QPalette.ToolTipBase: "brand.secondary", QPalette.ToolTipText: "text.onAccent",
        QPalette.PlaceholderText: "text.secondary",
    }
    for role, token in roles.items():
        palette.setColor(role, QColor(COLOR_TOKENS[token]))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText, QPalette.PlaceholderText):
        palette.setColor(QPalette.Disabled, role, QColor(COLOR_TOKENS["text.disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.Button, QColor(COLOR_TOKENS["surface.disabled"]))
    return palette


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
    "eliminar",
    "borrar",
    "desactivar",
    "quitar",
    "dar de baja",
    "dar_de_baja",
)

NEUTRAL_BUTTON_HINTS = (
    "cerrar",
    "salir",
    "cancelar",
    "volver",
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


MODULE_STYLESHEET = render_qss("""
QWidget[themedModule="true"],
QDialog[themedModule="true"] {
    background-color: ${surface.main};
    color: ${text.main};
}
QWidget[transparentWindow="true"],
QDialog[transparentWindow="true"] {
    background-color: transparent;
}
QFrame[panel="true"],
QGroupBox[panel="true"] {
    background-color: ${surface.table.alternate};
    border: 1px solid ${border.subtle};
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
    color: ${text.main};
}
QLabel {
    color: ${text.main};
}
QLabel[role="title"] {
    color: ${text.main};
    font-size: 20px;
    font-weight: 700;
}
QLabel[role="accent"] {
    color: ${brand.secondary};
    font-weight: 700;
}
QLabel[role="successAccent"] {
    color: ${brand.primary};
    font-size: 22px;
    font-weight: 800;
}
QLabel[role="caption"] {
    color: ${text.secondary};
}
QLineEdit,
QPlainTextEdit,
QComboBox,
QDateEdit {
    min-height: 38px;
    padding: 0 12px;
    background-color: ${surface.panel};
    color: #000000;
    border: 1px solid ${border.control};
    border-radius: 10px;
    selection-background-color: ${brand.secondary};
    selection-color: ${surface.panel};
}
/* Listado desplegable de los QComboBox (picklists). */
QComboBox QAbstractItemView {
    background-color: ${surface.panel};
    alternate-background-color: ${surface.panel};
    color: #000000;
    selection-background-color: ${brand.secondary};
    selection-color: ${surface.panel};
    border: 1px solid ${border.control};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    min-height: 32px;
    padding: 0 10px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: ${surface.table.alternate};
    color: #000000;
}
QComboBox QAbstractItemView::item:selected {
    background-color: ${brand.secondary};
    color: ${surface.panel};
}
/* Los spinboxes NO deben recibir border/padding en el widget externo:
   Qt reduce el QLineEdit interno a 1 px y el texto deja de verse. */
QSpinBox,
QDoubleSpinBox {
    min-height: 38px;
    background-color: transparent;
    color: #000000;
    selection-background-color: ${brand.secondary};
    selection-color: ${surface.panel};
}
QSpinBox QLineEdit,
QDoubleSpinBox QLineEdit {
    padding: 0 8px;
    color: #000000;
}
QPlainTextEdit {
    padding: 10px 12px;
}
QLineEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QDateEdit:focus {
    border: 2px solid ${brand.secondary};
}
QLineEdit:read-only,
QPlainTextEdit:read-only {
    background-color: ${surface.main};
    color: #000000;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    border: none;
    background: transparent;
    width: 24px;
}
QComboBox::down-arrow {
    image: url(:/Icons/Bootstrap/chevron-down.svg);
    width: 13px;
    height: 13px;
}
QDateEdit[calendarPopup="true"]::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 28px;
    border: none;
    background: transparent;
}
QDateEdit[calendarPopup="true"]::down-arrow {
    image: url(:/Icons/Bootstrap/calendar2-date.svg);
    width: 16px;
    height: 16px;
}
QDateEdit[calendarPopup="true"]::up-button,
QDateEdit[calendarPopup="true"]::down-button {
    width: 0;
    height: 0;
    border: none;
    background: transparent;
}
QPushButton,
QToolButton {
    min-height: 38px;
    padding: 0 16px;
    border-radius: 10px;
    border: 1px solid ${border.control};
    background-color: ${surface.panel};
    color: ${text.main};
    font-weight: 700;
}
QPushButton:enabled:hover,
QToolButton:enabled:hover {
    background-color: ${surface.table.alternate};
}
QPushButton:enabled:pressed,
QToolButton:enabled:pressed {
    background-color: ${border.subtle};
}
QPushButton[variant="primary"],
QToolButton[variant="primary"] {
    background-color: ${brand.primary};
    border-color: ${brand.primary};
    color: ${surface.panel};
}
QPushButton[variant="primary"]:enabled:hover,
QToolButton[variant="primary"]:enabled:hover {
    background-color: ${brand.primary.hover};
    border-color: ${brand.primary.hover};
}
QPushButton[variant="primary"]:enabled:pressed,
QToolButton[variant="primary"]:enabled:pressed {
    background-color: ${brand.primary.pressed};
    border-color: ${brand.primary.pressed};
}
QPushButton[variant="secondary"],
QToolButton[variant="secondary"] {
    background-color: ${brand.secondary};
    border-color: ${brand.secondary};
    color: ${surface.panel};
}
QPushButton[variant="secondary"]:enabled:hover,
QToolButton[variant="secondary"]:enabled:hover {
    background-color: ${brand.secondary.hover};
    border-color: ${brand.secondary.hover};
}
QPushButton[variant="secondary"]:enabled:pressed,
QToolButton[variant="secondary"]:enabled:pressed {
    background-color: ${brand.secondary.pressed};
    border-color: ${brand.secondary.pressed};
}
QPushButton[variant="danger"],
QToolButton[variant="danger"] {
    background-color: ${semantic.danger};
    border-color: ${semantic.danger};
    color: ${surface.panel};
}
QPushButton[variant="danger"]:enabled:hover,
QToolButton[variant="danger"]:enabled:hover {
    background-color: ${semantic.danger.hover};
    border-color: ${semantic.danger.hover};
}
QPushButton[variant="danger"]:enabled:pressed,
QToolButton[variant="danger"]:enabled:pressed {
    background-color: ${semantic.danger.pressed};
    border-color: ${semantic.danger.pressed};
}
QPushButton[variant="neutral"],
QToolButton[variant="neutral"] {
    background-color: ${surface.panel};
    border-color: ${border.control};
    color: ${text.secondary};
}
QPushButton[variant="neutral"]:enabled:hover,
QToolButton[variant="neutral"]:enabled:hover {
    background-color: ${surface.table.alternate};
}
QPushButton[variant="neutral"]:enabled:pressed,
QToolButton[variant="neutral"]:enabled:pressed {
    background-color: ${border.subtle};
}
QPushButton:focus,
QToolButton:focus {
    outline: 2px solid ${focus.ring};
}
QPushButton:disabled,
QToolButton:disabled,
QPushButton[variant]:disabled,
QToolButton[variant]:disabled {
    background-color: ${surface.disabled};
    border-color: ${border.subtle};
    color: ${text.disabled};
}
QLineEdit:disabled,
QPlainTextEdit:disabled,
QComboBox:disabled,
QDateEdit:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled {
    background-color: ${surface.disabled};
    border-color: ${border.subtle};
    color: #000000;
}
QTableView,
QTableWidget,
QListView,
QTreeView {
    background-color: ${surface.panel};
    alternate-background-color: ${surface.table.alternate};
    color: ${text.main};
    border: 1px solid ${border.subtle};
    border-radius: 12px;
    gridline-color: ${border.subtle};
    selection-background-color: ${brand.secondary};
    selection-color: ${surface.panel};
}
QHeaderView::section {
    background-color: ${surface.table.alternate};
    color: ${text.main};
    border: none;
    border-bottom: 1px solid ${border.subtle};
    padding: 10px 8px;
    font-weight: 700;
}
QTabWidget::pane {
    border: 1px solid ${border.subtle};
    border-radius: 14px;
    background-color: ${surface.table.alternate};
    top: -1px;
}
QTabBar::tab {
    background-color: ${border.subtle};
    color: ${text.secondary};
    padding: 10px 16px;
    margin-right: 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: ${surface.panel};
    color: ${text.main};
    border: 1px solid ${border.subtle};
    border-bottom-color: ${surface.panel};
}
QCheckBox,
QRadioButton {
    color: ${text.main};
    spacing: 8px;
}
QCheckBox::indicator,
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid ${border.control};
    background-color: ${surface.panel};
}
QCheckBox::indicator {
    border-radius: 5px;
}
QRadioButton::indicator {
    border-radius: 9px;
}
QCheckBox::indicator:checked,
QRadioButton::indicator:checked {
    background-color: ${brand.primary};
    border-color: ${brand.primary};
}
QMenu {
    background-color: ${surface.panel};
    color: ${text.main};
    border: 1px solid ${border.subtle};
    border-radius: 10px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 12px;
    border-radius: 8px;
}
QMenu::item:selected {
    background-color: ${brand.secondary};
    color: ${surface.panel};
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: ${brand.secondary};
    color: ${surface.panel};
    border: none;
}
QCalendarWidget QToolButton {
    background-color: transparent;
    border: none;
    color: ${surface.panel};
    font-weight: 700;
}
QCalendarWidget QWidget#qt_calendar_weekdaybar {
    background-color: ${surface.table.alternate};
    color: ${text.secondary};
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: ${surface.panel};
    color: ${text.main};
    selection-background-color: ${brand.secondary};
    selection-color: ${surface.panel};
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background: ${border.control};
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
""")


ACCESS_STYLESHEET = render_qss("""
#Inicio_Sesion,
#Saludo_bienvenida,
#Bienvenida {
    background: transparent;
    color: ${text.main};
}
#principal {
    background-color: ${surface.main};
    border: 1px solid ${border.subtle};
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
        stop: 0 ${surface.panel},
        stop: 1 ${surface.table.alternate}
    );
    border: 1px solid ${border.subtle};
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
    background-color: ${surface.panel};
    color: #000000;
    border: 1px solid ${border.subtle};
    border-radius: 10px;
    selection-background-color: ${brand.secondary};
    selection-color: ${surface.panel};
}
#txt_User:focus,
#txt_Password:focus {
    border: 2px solid ${brand.secondary};
    background-color: ${surface.panel};
}
#txt_User::placeholder,
#txt_Password::placeholder {
    color: ${text.secondary};
}
#btnAceptar,
#btn_entrar,
#btn_btn_registrar {
    min-height: 32px;
    padding: 0 18px;
    background-color: ${brand.primary};
    color: ${surface.panel};
    border: 1px solid ${brand.primary};
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
}
#btnAceptar:hover,
#btn_entrar:hover,
#btn_btn_registrar:hover {
    background-color: ${brand.primary.hover};
    border-color: ${brand.primary.hover};
}
#btnAceptar:pressed,
#btn_entrar:pressed,
#btn_btn_registrar:pressed {
    background-color: ${brand.primary.pressed};
    border-color: ${brand.primary.pressed};
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
    background-color: ${brand.secondary};
    border: 1px solid ${brand.secondary};
}
#btnMinimizar:hover {
    background-color: ${brand.secondary.hover};
    border-color: ${brand.secondary.hover};
}
#btnMinimizar:pressed {
    background-color: ${brand.secondary.pressed};
    border-color: ${brand.secondary.pressed};
}
#btnCerrar {
    background-color: ${surface.panel};
    border-color: ${border.control};
    color: ${text.secondary};
}
#btnCerrar:hover {
    background-color: ${surface.table.alternate};
    border-color: ${border.control};
}
#btnCerrar:pressed {
    background-color: ${border.subtle};
    border-color: ${border.control};
}
#btnAceptar:disabled,
#btn_entrar:disabled,
#btn_btn_registrar:disabled,
#btnCerrar:disabled,
#btnMinimizar:disabled {
    background-color: ${surface.disabled};
    color: ${text.disabled};
    border-color: ${border.subtle};
}
#contenedor {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 ${surface.panel},
        stop: 1 ${surface.main}
    );
    border: 1px solid ${border.subtle};
    border-radius: 24px;
}
#etiquetaBuendia {
    color: ${brand.secondary};
    font-size: 28px;
    font-weight: 700;
}
#etiquetaNombreUsuario {
    color: ${text.main};
    font-size: 34px;
    font-weight: 800;
}
#etiquetaEslogan {
    color: ${text.secondary};
    font-size: 13px;
    font-weight: 600;
    padding: 0 18px;
}
#etiqueta_titulo {
    color: ${text.main};
    font-size: 22px;
    font-weight: 800;
}
#etiqueta_imagen,
#label {
    background: transparent;
}
""")


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


SHELL_STYLESHEET = render_qss("""
QWidget[themedShell="true"],
QWidget#w_contenedor,
QWidget#w_cuerpo,
QWidget#w_encabezado {
    background-color: ${surface.main};
    color: ${text.main};
}
QWidget#w_cuerpo_menu {
    background-color: ${brand.secondary};
}
QWidget#w_cuerpo_menu QPushButton {
    background-color: ${brand.secondary};
    color: ${text.onAccent};
    border: 2px solid transparent;
    border-radius: 4px;
    min-height: 36px;
    padding: 0 8px;
    text-align: left;
    font-family: "Segoe UI";
    font-size: 14px;
}
QWidget#w_cuerpo_menu QPushButton[navigationExpanded="false"] {
    text-align: center;
    padding: 0;
}
QWidget#w_cuerpo_menu QPushButton:enabled:hover {
    background-color: ${brand.secondary.hover};
}
QWidget#w_cuerpo_menu QPushButton:enabled:pressed {
    background-color: ${brand.primary};
}
QWidget#w_cuerpo_menu QPushButton:focus {
    border-color: ${text.onAccent};
}
QWidget#w_cuerpo_menu QPushButton:disabled {
    background-color: ${surface.disabled};
    color: ${text.disabled};
}
""")


def apply_shell_theme(root_widget):
    if root_widget is None:
        return
    root_widget.setProperty("themedShell", True)
    _aplicar_texto_negro_campos(root_widget)
    root_widget.setStyleSheet(MODULE_STYLESHEET + SHELL_STYLESHEET + TITLE_SCALE_STYLESHEET)


def apply_module_theme(root_widget):
    if root_widget is None:
        return

    root_widget.setProperty("themedModule", True)
    _sync_window_state(root_widget)

    _decorate_panels(root_widget)
    _decorate_buttons(root_widget)
    _decorate_labels(root_widget)
    _decorate_views(root_widget)
    _aplicar_texto_negro_campos(root_widget)
    root_widget.setStyleSheet(MODULE_STYLESHEET + TITLE_SCALE_STYLESHEET)
    QTimer.singleShot(0, lambda widget=root_widget: _sync_window_state(widget, refresh_style=True))


def _aplicar_texto_negro_campos(root_widget):
    """Fuerza texto negro en los campos de captura sin tocar bordes ni tamanos."""
    tipos_campo = (QLineEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox)
    for widget in root_widget.findChildren(QWidget):
        if not isinstance(widget, tipos_campo):
            continue
        estilo = widget.styleSheet() or ""
        if "color: #000000" in estilo.lower():
            continue
        widget.setStyleSheet(estilo + "\ncolor: #000000;")


def apply_access_theme(root_widget):
    if root_widget is None:
        return

    _estabilizar_pixmaps(root_widget)
    _aplicar_texto_negro_campos(root_widget)
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
        elif any(hint in button_key for hint in NEUTRAL_BUTTON_HINTS):
            button.setProperty("variant", "neutral")
        elif any(hint in button_key for hint in PRIMARY_BUTTON_HINTS):
            button.setProperty("variant", "primary")
        elif any(hint in button_key for hint in SECONDARY_BUTTON_HINTS):
            button.setProperty("variant", "secondary")


def _decorate_labels(root_widget):
    _estabilizar_pixmaps(root_widget)
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


def _estabilizar_pixmaps(root_widget):
    for label in root_widget.findChildren(QLabel):
        pixmap = label.pixmap()
        if not pixmap.isNull():
            mostrar_imagen_estatica(label, pixmap)


def _decorate_views(root_widget):
    for view in root_widget.findChildren(QAbstractItemView):
        _apply_view_density(view)
    _configurar_popup_combos(root_widget)


class _ComboPopupWidthFilter(QObject):
    """Mantiene el popup del combo con al menos el ancho del control."""

    def __init__(self, combo):
        super().__init__(combo)
        self._combo_ref = combo

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Show, QEvent.Resize):
            _ajustar_ancho_popup(self._combo_ref)
        return False


def _ajustar_ancho_popup(combo):
    try:
        vista = combo.view()
    except RuntimeError:
        return
    if vista is None:
        return

    metrics = combo.fontMetrics()
    ancho_items = max(
        (metrics.horizontalAdvance(combo.itemText(indice)) for indice in range(combo.count())),
        default=0,
    )
    ancho = max(
        combo.width(),
        combo.minimumSizeHint().width(),
        ancho_items + 40,
    )
    if vista.minimumWidth() != ancho:
        vista.setMinimumWidth(ancho)


def configure_combo_popup(combo):
    if combo is None:
        return
    filtro = getattr(combo, "_vt_popup_filter", None)
    if filtro is None:
        filtro = _ComboPopupWidthFilter(combo)
        combo._vt_popup_filter = filtro
        combo.installEventFilter(filtro)
    vista = combo.view()
    if vista is not None and getattr(vista, "_vt_popup_filter", None) is not filtro:
        vista._vt_popup_filter = filtro
        vista.installEventFilter(filtro)
    if vista is not None:
        vista.setAlternatingRowColors(False)
    _ajustar_ancho_popup(combo)


def _configurar_popup_combos(root_widget):
    for combo in root_widget.findChildren(QComboBox):
        configure_combo_popup(combo)


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


def configure_window_chrome(root_widget, minimum_size=(320, 180), maximizable=False, frameless=False):
    if root_widget is None:
        return

    if frameless:
        root_widget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    floating = bool(root_widget.windowFlags() & Qt.WindowType.FramelessWindowHint) or root_widget.testAttribute(Qt.WA_TranslucentBackground)
    if not floating:
        root_widget.setWindowFlag(Qt.WindowType.CustomizeWindowHint, False)
        root_widget.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        for flag in (Qt.WindowType.WindowTitleHint, Qt.WindowType.WindowSystemMenuHint,
                     Qt.WindowType.WindowCloseButtonHint, Qt.WindowType.WindowMinimizeButtonHint):
            root_widget.setWindowFlag(flag, True)
        root_widget.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, maximizable)
    root_widget.setWindowIcon(official_window_icon())
    maximum = root_widget.maximumSize()
    root_widget.setMinimumSize(
        min(maximum.width(), max(minimum_size[0], root_widget.minimumWidth())),
        min(maximum.height(), max(minimum_size[1], root_widget.minimumHeight())),
    )
    if not floating:
        for drag_filter in getattr(root_widget, "_copilot_drag_filters", []):
            drag_filter.drag_target.removeEventFilter(drag_filter)
            drag_filter.drag_target.unsetCursor()
            drag_filter.deleteLater()
        root_widget._copilot_drag_filters = []
    _sync_window_state(root_widget)


def configure_child_modal(root_widget, drag_widget=None, modal=True, keep_on_top=True, frameless=False):
    if root_widget is None:
        return

    root_widget.setWindowFlag(Qt.WindowType.Dialog, True)
    configure_window_chrome(
        root_widget,
        maximizable=bool(root_widget.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint),
        frameless=frameless,
    )
    if keep_on_top:
        root_widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    if modal and hasattr(root_widget, "setWindowModality"):
        root_widget.setWindowModality(Qt.WindowModality.ApplicationModal)
    if root_widget.windowFlags() & Qt.WindowType.FramelessWindowHint:
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