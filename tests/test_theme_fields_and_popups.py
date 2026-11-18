import re

import pytest


@pytest.mark.unit
def test_stylesheet_fuerza_texto_negro_en_campos_de_captura():
    from app.Controller.UiTheme import MODULE_STYLESHEET

    grupo = re.search(
        r"QLineEdit,\s*QPlainTextEdit,\s*QComboBox,\s*QDateEdit\s*{(.*?)}",
        MODULE_STYLESHEET,
        re.S,
    )
    assert grupo is not None
    assert "color: #000000" in grupo.group(1)

    for selector in ("QSpinBox,\nQDoubleSpinBox", "QSpinBox QLineEdit,\nQDoubleSpinBox QLineEdit"):
        bloque = re.search(rf"{selector}\s*{{(.*?)}}", MODULE_STYLESHEET, re.S)
        assert bloque is not None, selector
        assert "color: #000000" in bloque.group(1), selector


@pytest.mark.unit
def test_stylesheet_estiliza_popup_de_combobox():
    from app.Controller.UiTheme import MODULE_STYLESHEET

    bloque = re.search(r"QComboBox QAbstractItemView\s*{(.*?)}", MODULE_STYLESHEET, re.S)
    assert bloque is not None
    reglas = bloque.group(1)
    assert "color: #000000" in reglas
    assert "background-color:" in reglas
    assert "selection-background-color:" in reglas
    assert "border-radius: 8px" in reglas


@pytest.mark.qt
def test_combo_popup_respeta_ancho_del_control(qtbot):
    from PySide6.QtWidgets import QComboBox, QDialog, QLineEdit, QSpinBox, QVBoxLayout
    from PySide6.QtGui import QPalette

    from app.Controller.UiTheme import apply_module_theme

    dialogo = QDialog()
    qtbot.addWidget(dialogo)
    layout = QVBoxLayout(dialogo)
    combo = QComboBox()
    combo.addItems(["Contado", "Tarjeta de credito", "Transferencia bancaria"])
    campo = QLineEdit()
    campo.setText("Texto de prueba")
    decimal = QSpinBox()
    decimal.setButtonSymbols(QSpinBox.NoButtons)
    decimal.setValue(12)
    for widget in (combo, campo, decimal):
        layout.addWidget(widget)

    dialogo.resize(420, 220)
    apply_module_theme(dialogo)
    dialogo.show()

    assert campo.palette().color(QPalette.Text).name() == "#000000"
    assert combo.palette().color(QPalette.Text).name() == "#000000"
    assert decimal.palette().color(QPalette.Text).name() == "#000000"
    assert decimal.findChild(QLineEdit).width() > 10

    combo.showPopup()
    qtbot.wait(50)
    popup = combo.view().window()
    assert popup.width() >= combo.width()
    assert combo.view().alternatingRowColors() is False
    combo.hidePopup()


@pytest.mark.qt
def test_ajustar_caja_opciones_expande_popup_sin_recortar(qtbot):
    from PySide6.QtWidgets import QComboBox

    from app.Controller.AjustarCajaOpcionesGlobal import AjustarcajaOpciones

    combo = QComboBox()
    qtbot.addWidget(combo)
    combo.addItems(["Bebidas", "Productos de limpieza del hogar y cuidado personal"])
    combo.resize(180, 38)
    AjustarcajaOpciones().ajustar_cajadeopciones(combo)

    ancho_texto = max(
        combo.fontMetrics().horizontalAdvance(combo.itemText(i))
        for i in range(combo.count())
    )
    assert combo.view().minimumWidth() >= combo.width()
    assert combo.view().minimumWidth() >= ancho_texto
