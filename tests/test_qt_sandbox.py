import pytest


@pytest.mark.qt
def test_ref01_qsettings_and_printers_are_isolated(qt_sandbox):
    from pathlib import Path

    from PySide6.QtCore import QSettings
    from PySide6.QtPrintSupport import QPrinter, QPrinterInfo

    settings = QSettings("TuleVenta", "Licencia")
    settings.setValue("licencia_key", "REF01-NOT-A-LICENSE")
    settings.sync()
    assert Path(settings.fileName()).is_relative_to(qt_sandbox.root)
    assert QPrinterInfo.availablePrinters() == []
    with pytest.raises(RuntimeError, match="Impresion bloqueada"):
        QPrinter()