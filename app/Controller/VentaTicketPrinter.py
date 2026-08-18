import os
import platform
import subprocess
import tempfile
import textwrap
import unicodedata

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPageSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from ..Model.ConfiguracionSistemaModel import ConfiguracionSistemaModel
from ..runtime_paths import ruta_recurso


class TicketVentaPrinter:
    TICKET_WIDTH = 80 * mm
    MARGIN_X = 5 * mm
    LINE_HEIGHT = 4.2 * mm
    TEXT_LINE_WIDTH = 42

    def __init__(self, venta):
        self.venta = venta
        self.ticket_width_mm = ConfiguracionSistemaModel.obtener_ancho_ticket_mm()
        self.TICKET_WIDTH = self.ticket_width_mm * mm
        self.TEXT_LINE_WIDTH = self._calcular_ancho_linea_texto(self.ticket_width_mm)
        self.logo_path = ruta_recurso("app", "Source", "Icons", "logos", "tuleVenta.png")

    def procesar_ticket(self):
        pdf_path = self._generar_pdf_ticket()
        return self._despachar_ticket(pdf_path)

    def _generar_pdf_ticket(self):
        page_height = self._calcular_alto_pagina()
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"ticket_{self._valor_seguro(getattr(self.venta, 'folio', 'venta'))}_",
            suffix=".pdf",
            delete=False,
        )
        temp_file.close()

        pdf = canvas.Canvas(temp_file.name, pagesize=(self.TICKET_WIDTH, page_height))
        pdf.setTitle(f"Ticket {self._valor_seguro(getattr(self.venta, 'folio', 'SIN-FOLIO'))}")

        y = page_height - (6 * mm)
        y = self._dibujar_encabezado(pdf, y)
        y = self._dibujar_datos_venta(pdf, y)
        y = self._dibujar_detalles(pdf, y)
        y = self._dibujar_totales(pdf, y)
        self._dibujar_pie(pdf, y)

        pdf.save()
        return temp_file.name

    def _despachar_ticket(self, pdf_path):
        sistema = platform.system()
        impresora_configurada = ConfiguracionSistemaModel.obtener_impresora_tickets()
        if sistema == "Windows":
            if impresora_configurada:
                resultado_texto = self._imprimir_ticket_texto_windows(impresora_configurada)
                if resultado_texto.get("ok"):
                    resultado_texto.setdefault("path", pdf_path)
                    return resultado_texto

                impresoras_disponibles = self._obtener_impresoras_disponibles()
                if impresora_configurada in impresoras_disponibles:
                    resultado_configurado = self._imprimir_pdf_con_qt(pdf_path, impresora_configurada)
                    if resultado_configurado.get("ok"):
                        return resultado_configurado

                    resultado_fallback = self._imprimir_pdf_con_qt(pdf_path)
                    resultado_fallback["message"] = (
                        f"No se pudo imprimir en '{impresora_configurada}'. {resultado_fallback.get('message', '')}"
                    ).strip()
                    return resultado_fallback

                resultado_fallback = self._imprimir_pdf_con_qt(pdf_path)
                resultado_fallback["message"] = (
                    f"La impresora configurada '{impresora_configurada}' no está disponible. {resultado_fallback.get('message', '')}"
                ).strip()
                return resultado_fallback

            return self._imprimir_pdf_con_qt(pdf_path)

        opener = "open" if sistema == "Darwin" else "xdg-open"
        resultado = os.system(f'{opener} "{pdf_path}"')
        if resultado == 0:
            return {
                "ok": True,
                "message": "Ticket generado y abierto para impresion manual.",
                "path": pdf_path,
            }

        return {
            "ok": False,
            "message": "No se pudo abrir el ticket generado para impresion manual.",
            "path": pdf_path,
        }

    def _imprimir_pdf_con_qt(self, pdf_path, impresora=""):
        documento = QPdfDocument()
        error_carga = documento.load(pdf_path)
        if error_carga != QPdfDocument.Error.None_:
            return {
                "ok": False,
                "message": f"No se pudo cargar el ticket PDF para impresion directa. Codigo: {error_carga}",
                "path": pdf_path,
            }

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)
        printer.setFullPage(True)
        if impresora:
            printer.setPrinterName(impresora)

        if not printer.isValid():
            destino = f"'{impresora}'" if impresora else "la impresora predeterminada"
            return self._abrir_pdf_windows(pdf_path, OSError(f"No se encontró {destino}."))

        total_paginas = documento.pageCount()
        if total_paginas <= 0:
            return {
                "ok": False,
                "message": "El ticket PDF no contiene paginas para imprimir.",
                "path": pdf_path,
            }

        tamanio_pagina = documento.pagePointSize(0)
        if hasattr(tamanio_pagina, "isEmpty") and tamanio_pagina.isEmpty():
            return {
                "ok": False,
                "message": "No se pudo determinar el tamano del ticket para imprimir.",
                "path": pdf_path,
            }

        printer.setPageSize(QPageSize(tamanio_pagina, QPageSize.Unit.Point, "TicketVenta"))

        painter = QPainter()
        try:
            if not painter.begin(printer):
                raise OSError("Qt no pudo iniciar la sesion de impresion.")

            for indice_pagina in range(total_paginas):
                if indice_pagina > 0 and not printer.newPage():
                    raise OSError("Qt no pudo crear una nueva pagina de impresion.")

                area_impresion = printer.pageRect(QPrinter.Unit.DevicePixel)
                tamanio_imagen = area_impresion.size()
                if hasattr(tamanio_imagen, "toSize"):
                    tamanio_imagen = tamanio_imagen.toSize()

                imagen = documento.render(indice_pagina, tamanio_imagen)
                if imagen.isNull():
                    raise OSError(f"Qt no pudo renderizar la pagina {indice_pagina + 1} del ticket.")

                painter.drawImage(QRectF(area_impresion), imagen)
        except Exception as error_impresion:
            if painter.isActive():
                painter.end()
            return self._abrir_pdf_windows(pdf_path, error_impresion)

        if painter.isActive():
            painter.end()

        if impresora:
            return {
                "ok": True,
                "message": f"Ticket enviado a impresion en '{impresora}'.",
                "path": pdf_path,
            }

        return {
            "ok": True,
            "message": "Ticket enviado a impresion en la impresora predeterminada.",
            "path": pdf_path,
        }

    def _abrir_pdf_windows(self, pdf_path, error_impresion):
        try:
            os.startfile(pdf_path)
            return {
                "ok": True,
                "message": (
                    "No se pudo enviar el ticket a impresion automatica. "
                    f"Se abrio la vista previa del ticket. Detalle: {error_impresion}"
                ),
                "path": pdf_path,
            }
        except OSError as error_vista_previa:
            self._mostrar_ubicacion_ticket_windows(pdf_path)
            return {
                "ok": False,
                "message": (
                    "No se pudo imprimir ni abrir el ticket generado. "
                    f"Se mostro la ubicacion del archivo temporal. Detalle: {error_vista_previa}"
                ),
                "path": pdf_path,
            }

    @staticmethod
    def _mostrar_ubicacion_ticket_windows(pdf_path):
        try:
            subprocess.Popen(["explorer", f"/select,{os.path.normpath(pdf_path)}"])
        except OSError:
            return

    def _imprimir_ticket_texto_windows(self, impresora):
        try:
            import ctypes
            from ctypes import wintypes

            class DOCINFO1(ctypes.Structure):
                _fields_ = [
                    ("pDocName", wintypes.LPWSTR),
                    ("pOutputFile", wintypes.LPWSTR),
                    ("pDatatype", wintypes.LPWSTR),
                ]

            winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
            handle = wintypes.HANDLE()
            if not winspool.OpenPrinterW(impresora, ctypes.byref(handle), None):
                raise OSError(ctypes.get_last_error(), "No se pudo abrir la impresora configurada")

            payload = self._construir_payload_ticket_texto()
            buffer = ctypes.create_string_buffer(payload)
            doc_info = DOCINFO1("Ticket de venta", None, "RAW")

            inicio_documento = False
            inicio_pagina = False
            try:
                job_id = winspool.StartDocPrinterW(handle, 1, ctypes.byref(doc_info))
                if not job_id:
                    raise OSError(ctypes.get_last_error(), "No se pudo iniciar el documento de impresion")
                inicio_documento = True

                if not winspool.StartPagePrinter(handle):
                    raise OSError(ctypes.get_last_error(), "No se pudo iniciar la pagina de impresion")
                inicio_pagina = True

                bytes_escritos = wintypes.DWORD(0)
                if not winspool.WritePrinter(handle, buffer, len(payload), ctypes.byref(bytes_escritos)):
                    raise OSError(ctypes.get_last_error(), "No se pudo escribir el ticket en el spooler")
                if bytes_escritos.value != len(payload):
                    raise OSError(0, f"Se escribieron {bytes_escritos.value} de {len(payload)} bytes del ticket")
            finally:
                if inicio_pagina:
                    winspool.EndPagePrinter(handle)
                if inicio_documento:
                    winspool.EndDocPrinter(handle)
                winspool.ClosePrinter(handle)

            return {
                "ok": True,
                "message": f"Ticket enviado al spooler de '{impresora}' en modo texto.",
            }
        except Exception as error_impresion:
            return {
                "ok": False,
                "message": f"No se pudo enviar el ticket en modo texto a '{impresora}': {error_impresion}",
            }

    def _construir_payload_ticket_texto(self):
        contenido = self._generar_ticket_texto()
        texto_seguro = self._normalizar_texto_impresora(contenido)
        return b"\x1b@" + texto_seguro.encode("cp850", errors="replace") + b"\r\n\r\n\r\n\r\n\r\n"

    def _generar_ticket_texto(self):
        lineas = []
        sucursal = getattr(getattr(self.venta, "empleado", None), "sucursal", None)
        nombre_sucursal = self._valor_seguro(getattr(sucursal, "nombre_sucursal", None), "TuleVenta POS")

        lineas.extend(self._centrar_bloque_ticket(nombre_sucursal))

        rfc = self._valor_seguro(getattr(sucursal, "rfc", None))
        if rfc:
            lineas.extend(self._centrar_bloque_ticket(f"RFC: {rfc}"))

        direccion = self._formatear_direccion_sucursal(sucursal)
        if direccion:
            lineas.extend(self._centrar_bloque_ticket(direccion))

        telefono = self._valor_seguro(getattr(sucursal, "num_telefono", None))
        if telefono:
            lineas.extend(self._centrar_bloque_ticket(f"Tel: {telefono}"))

        lineas.append(self._separador_texto_ticket())

        fecha = getattr(self.venta, "fecha", None)
        fecha_texto = fecha.strftime("%d/%m/%Y %H:%M") if fecha else "N/D"
        cliente = self._nombre_cliente(getattr(self.venta, "cliente", None))
        cajero = self._nombre_empleado(getattr(self.venta, "empleado", None))
        forma_pago = self._valor_seguro(getattr(self.venta, "forma_pago", None), "N/D")

        for etiqueta, valor in [
            ("Folio", self._valor_seguro(getattr(self.venta, "folio", None), "SIN-FOLIO")),
            ("Fecha", fecha_texto),
            ("Cliente", cliente),
            ("Cajero", cajero),
            ("Pago", forma_pago),
        ]:
            lineas.extend(self._formatear_campo_ticket(etiqueta, valor))

        lineas.append(self._separador_texto_ticket())
        lineas.extend(self._alinear_columnas_ticket("PRODUCTO", "IMPORTE"))
        lineas.append(self._separador_texto_ticket())

        detalles_ordenados = sorted(self.venta.detalles_ventas or [], key=lambda item: item.id or 0)
        for indice, detalle in enumerate(detalles_ordenados):
            nombre = self._valor_seguro(detalle.nombre_producto, "Producto")
            lineas.extend(self._envolver_texto_ticket(nombre))

            cantidad = float(detalle.cantidad or 0.0)
            precio_unitario = float(detalle.precio_unitario or 0.0)
            total_linea = float(detalle.total_con_iva or 0.0)
            descripcion_linea = f"{cantidad:,.2f} x {self._formatear_moneda(precio_unitario)}"
            lineas.extend(self._alinear_columnas_ticket(descripcion_linea, self._formatear_moneda(total_linea), indent=2))

            descuento = float(detalle.descuento or 0.0)
            if descuento > 0:
                lineas.extend(self._alinear_columnas_ticket("DESC.", f"-{self._formatear_moneda(descuento)}", indent=2))

            if indice < len(detalles_ordenados) - 1:
                lineas.append("")

        lineas.append(self._separador_texto_ticket())

        for etiqueta, valor in [
            ("Subtotal", float(getattr(self.venta, "subtotal", 0.0) or 0.0)),
            ("Descuento", self._calcular_descuento_total()),
            ("IVA", float(getattr(self.venta, "iva", 0.0) or 0.0)),
            ("TOTAL", float(getattr(self.venta, "total", 0.0) or 0.0)),
        ]:
            lineas.extend(self._alinear_columnas_ticket(etiqueta.upper(), self._formatear_moneda(valor)))

        notas = self._obtener_notas_ticket()
        if notas:
            lineas.append(self._separador_texto_ticket())
            lineas.extend(self._centrar_bloque_ticket("NOTAS"))
            for nota in notas:
                lineas.extend(self._formatear_nota_ticket(nota))

        lineas.append(self._separador_texto_ticket())
        lineas.append("")
        lineas.extend(self._centrar_bloque_ticket("Gracias por su compra"))
        lineas.extend(self._centrar_bloque_ticket("TuleVenta POS"))
        return "\r\n".join(lineas)

    def _formatear_campo_ticket(self, etiqueta, valor):
        etiqueta = f"{self._valor_seguro(etiqueta).upper()}:"
        valor = self._valor_seguro(valor, "N/D")

        ancho_valor = max(self.TEXT_LINE_WIDTH - len(etiqueta) - 1, 1)
        lineas_valor = self._envolver_texto_ticket(valor, width=ancho_valor)
        if len(lineas_valor) == 1:
            relleno = max(self.TEXT_LINE_WIDTH - len(etiqueta) - len(lineas_valor[0]), 1)
            return [f"{etiqueta}{' ' * relleno}{lineas_valor[0]}"]

        resultado = [etiqueta]
        for linea in self._envolver_texto_ticket(valor, width=self.TEXT_LINE_WIDTH - 2):
            resultado.append(f"  {linea}")
        return resultado

    def _formatear_nota_ticket(self, texto):
        lineas = self._envolver_texto_ticket(texto, width=self.TEXT_LINE_WIDTH - 2)
        if not lineas:
            return ["- "]

        resultado = [f"- {lineas[0]}"]
        for linea in lineas[1:]:
            resultado.append(f"  {linea}")
        return resultado

    def _envolver_texto_ticket(self, texto, width=None):
        ancho = width or self.TEXT_LINE_WIDTH
        texto = self._valor_seguro(texto)
        if not texto:
            return [""]

        lineas = []
        for fragmento in texto.splitlines() or [texto]:
            envuelto = textwrap.wrap(
                fragmento,
                width=ancho,
                break_long_words=True,
                break_on_hyphens=False,
            )
            lineas.extend(envuelto or [""])
        return lineas

    def _centrar_bloque_ticket(self, texto):
        return [linea.center(self.TEXT_LINE_WIDTH) for linea in self._envolver_texto_ticket(texto)]

    def _alinear_columnas_ticket(self, izquierda, derecha, indent=0):
        izquierda = self._valor_seguro(izquierda)
        derecha = self._valor_seguro(derecha)
        prefijo = " " * max(indent, 0)
        ancho_util = max(self.TEXT_LINE_WIDTH - len(prefijo), 1)
        espacio_disponible = max(ancho_util - len(derecha) - 1, 1)
        lineas_izquierda = self._envolver_texto_ticket(izquierda, width=espacio_disponible)

        if not lineas_izquierda:
            return [f"{prefijo}{derecha.rjust(ancho_util)}"]

        resultado = []
        if len(lineas_izquierda) == 1:
            izquierda_base = lineas_izquierda[0]
            relleno = max(ancho_util - len(izquierda_base) - len(derecha), 1)
            return [f"{prefijo}{izquierda_base}{' ' * relleno}{derecha}"]

        for linea in lineas_izquierda[:-1]:
            resultado.append(f"{prefijo}{linea}")

        ultima = lineas_izquierda[-1]
        relleno = max(ancho_util - len(ultima) - len(derecha), 1)
        resultado.append(f"{prefijo}{ultima}{' ' * relleno}{derecha}")
        return resultado

    def _separador_texto_ticket(self):
        return "-" * self.TEXT_LINE_WIDTH

    @staticmethod
    def _calcular_ancho_linea_texto(ancho_ticket_mm):
        try:
            ancho = float(ancho_ticket_mm)
        except (TypeError, ValueError):
            ancho = 80.0

        ancho = max(40.0, ancho)
        if ancho <= 58.0:
            return 32
        if ancho >= 80.0:
            return 42 + max(0, int(round((ancho - 80.0) * 0.45)))

        proporcion = (ancho - 58.0) / 22.0
        return int(round(32 + (10 * proporcion)))

    @staticmethod
    def _normalizar_texto_impresora(texto):
        texto = unicodedata.normalize("NFKD", texto or "")
        texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
        return texto.replace("\t", " ")

    @staticmethod
    def _obtener_impresoras_disponibles():
        try:
            return {
                info.printerName().strip()
                for info in QPrinterInfo.availablePrinters()
                if info.printerName().strip()
            }
        except Exception:
            return set()

    def _calcular_alto_pagina(self):
        lineas = 22
        for detalle in sorted(self.venta.detalles_ventas or [], key=lambda item: item.id or 0):
            nombre = self._valor_seguro(detalle.nombre_producto, "Producto")
            lineas += max(1, len(simpleSplit(nombre, "Helvetica-Bold", 8, self.TICKET_WIDTH - (2 * self.MARGIN_X))))
            lineas += 1
            if float(detalle.descuento or 0.0) > 0:
                lineas += 1

        for nota in self._obtener_notas_ticket():
            lineas += max(1, len(simpleSplit(nota, "Helvetica", 7, self.TICKET_WIDTH - (2 * self.MARGIN_X))))

        return max(150 * mm, (lineas * self.LINE_HEIGHT) + (28 * mm))

    def _dibujar_encabezado(self, pdf, y):
        if self.logo_path.exists():
            logo_width = min(46 * mm, max(self.TICKET_WIDTH - (2 * self.MARGIN_X), 1 * mm))
            logo_height = logo_width * (12 / 46)
            logo_x = (self.TICKET_WIDTH - logo_width) / 2
            pdf.drawImage(
                str(self.logo_path),
                logo_x,
                y - logo_height,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask="auto",
            )
            y -= logo_height + (4 * mm)

        sucursal = getattr(getattr(self.venta, "empleado", None), "sucursal", None)
        nombre_sucursal = self._valor_seguro(
            getattr(sucursal, "nombre_sucursal", None),
            "TuleVenta POS",
        )
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(self.TICKET_WIDTH / 2, y, nombre_sucursal)
        y -= self.LINE_HEIGHT

        rfc = self._valor_seguro(getattr(sucursal, "rfc", None))
        if rfc:
            pdf.setFont("Helvetica", 7)
            pdf.drawCentredString(self.TICKET_WIDTH / 2, y, f"RFC: {rfc}")
            y -= self.LINE_HEIGHT

        direccion = self._formatear_direccion_sucursal(sucursal)
        for linea in simpleSplit(direccion, "Helvetica", 7, self.TICKET_WIDTH - (2 * self.MARGIN_X)):
            pdf.setFont("Helvetica", 7)
            pdf.drawCentredString(self.TICKET_WIDTH / 2, y, linea)
            y -= self.LINE_HEIGHT

        telefono = self._valor_seguro(getattr(sucursal, "num_telefono", None))
        if telefono:
            pdf.drawCentredString(self.TICKET_WIDTH / 2, y, f"Tel: {telefono}")
            y -= self.LINE_HEIGHT

        return self._dibujar_separador(pdf, y)

    def _dibujar_datos_venta(self, pdf, y):
        fecha = getattr(self.venta, "fecha", None)
        fecha_texto = fecha.strftime("%d/%m/%Y %H:%M") if fecha else "N/D"
        cliente = self._nombre_cliente(getattr(self.venta, "cliente", None))
        cajero = self._nombre_empleado(getattr(self.venta, "empleado", None))
        forma_pago = self._valor_seguro(getattr(self.venta, "forma_pago", None), "N/D")

        datos = [
            ("Folio", self._valor_seguro(getattr(self.venta, "folio", None), "SIN-FOLIO")),
            ("Fecha", fecha_texto),
            ("Cliente", cliente),
            ("Cajero", cajero),
            ("Pago", forma_pago),
        ]

        pdf.setFont("Helvetica", 7.5)
        for etiqueta, valor in datos:
            lineas = simpleSplit(f"{etiqueta}: {valor}", "Helvetica", 7.5, self.TICKET_WIDTH - (2 * self.MARGIN_X))
            for linea in lineas:
                pdf.drawString(self.MARGIN_X, y, linea)
                y -= self.LINE_HEIGHT

        return self._dibujar_separador(pdf, y)

    def _dibujar_detalles(self, pdf, y):
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(self.MARGIN_X, y, "PRODUCTO")
        pdf.drawRightString(self.TICKET_WIDTH - self.MARGIN_X, y, "IMPORTE")
        y -= self.LINE_HEIGHT
        y = self._dibujar_separador(pdf, y)

        for detalle in sorted(self.venta.detalles_ventas or [], key=lambda item: item.id or 0):
            nombre = self._valor_seguro(detalle.nombre_producto, "Producto")
            for linea in simpleSplit(nombre, "Helvetica-Bold", 8, self.TICKET_WIDTH - (2 * self.MARGIN_X)):
                pdf.setFont("Helvetica-Bold", 8)
                pdf.drawString(self.MARGIN_X, y, linea)
                y -= self.LINE_HEIGHT

            cantidad = float(detalle.cantidad or 0.0)
            precio_unitario = float(detalle.precio_unitario or 0.0)
            total_linea = float(detalle.total_con_iva or 0.0)
            pdf.setFont("Helvetica", 7.5)
            pdf.drawString(self.MARGIN_X, y, f"{cantidad:,.2f} x {self._formatear_moneda(precio_unitario)}")
            pdf.drawRightString(self.TICKET_WIDTH - self.MARGIN_X, y, self._formatear_moneda(total_linea))
            y -= self.LINE_HEIGHT

            descuento = float(detalle.descuento or 0.0)
            if descuento > 0:
                pdf.drawString(self.MARGIN_X, y, f"Desc.: -{self._formatear_moneda(descuento)}")
                y -= self.LINE_HEIGHT

        return self._dibujar_separador(pdf, y)

    def _dibujar_totales(self, pdf, y):
        totales = [
            ("Subtotal", float(getattr(self.venta, "subtotal", 0.0) or 0.0)),
            ("Descuento", self._calcular_descuento_total()),
            ("IVA", float(getattr(self.venta, "iva", 0.0) or 0.0)),
            ("TOTAL", float(getattr(self.venta, "total", 0.0) or 0.0)),
        ]

        for etiqueta, valor in totales:
            pdf.setFont("Helvetica-Bold" if etiqueta == "TOTAL" else "Helvetica", 8)
            pdf.drawString(self.MARGIN_X, y, etiqueta)
            pdf.drawRightString(self.TICKET_WIDTH - self.MARGIN_X, y, self._formatear_moneda(valor))
            y -= self.LINE_HEIGHT

        notas = self._obtener_notas_ticket()
        if notas:
            y -= mm
            y = self._dibujar_separador(pdf, y)
            pdf.setFont("Helvetica-Bold", 7.5)
            pdf.drawString(self.MARGIN_X, y, "NOTAS")
            y -= self.LINE_HEIGHT
            pdf.setFont("Helvetica", 7)
            for nota in notas:
                for linea in simpleSplit(nota, "Helvetica", 7, self.TICKET_WIDTH - (2 * self.MARGIN_X)):
                    pdf.drawString(self.MARGIN_X, y, linea)
                    y -= self.LINE_HEIGHT

        return y

    def _dibujar_pie(self, pdf, y):
        y -= mm
        self._dibujar_separador(pdf, y)
        y -= self.LINE_HEIGHT
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(self.TICKET_WIDTH / 2, y, "Gracias por su compra")
        y -= self.LINE_HEIGHT
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(self.TICKET_WIDTH / 2, y, "TuleVenta POS")

    def _dibujar_separador(self, pdf, y):
        pdf.setLineWidth(0.3)
        pdf.line(self.MARGIN_X, y, self.TICKET_WIDTH - self.MARGIN_X, y)
        return y - (2 * mm)

    def _calcular_descuento_total(self):
        subtotal = float(getattr(self.venta, "subtotal", 0.0) or 0.0)
        iva = float(getattr(self.venta, "iva", 0.0) or 0.0)
        total = float(getattr(self.venta, "total", 0.0) or 0.0)
        return round(max(subtotal + iva - total, 0.0), 2)

    def _obtener_notas_ticket(self):
        comentarios = self._valor_seguro(getattr(self.venta, "comentarios", None))
        if not comentarios:
            return []

        notas = []
        for fragmento in comentarios.replace("\n", "|").split("|"):
            texto = fragmento.strip()
            if texto:
                notas.append(texto)
        return notas

    @staticmethod
    def _valor_seguro(valor, valor_por_defecto=""):
        if valor is None:
            return valor_por_defecto
        texto = str(valor).strip()
        return texto if texto else valor_por_defecto

    @staticmethod
    def _formatear_moneda(valor):
        return f"${float(valor or 0.0):,.2f}"

    @staticmethod
    def _nombre_empleado(empleado):
        if empleado is None:
            return "N/D"
        nombre = " ".join(
            fragmento
            for fragmento in [
                getattr(empleado, "nombre", ""),
                getattr(empleado, "apellido_paterno", ""),
                getattr(empleado, "apellido_materno", ""),
            ]
            if str(fragmento).strip()
        )
        return nombre or "N/D"

    @staticmethod
    def _nombre_cliente(cliente):
        if cliente is None:
            return "PUBLICO GENERAL"
        if hasattr(cliente, "apellido_paterno") and getattr(cliente, "apellido_paterno", ""):
            return " ".join(
                fragmento
                for fragmento in [
                    getattr(cliente, "nombre", ""),
                    getattr(cliente, "apellido_paterno", ""),
                    getattr(cliente, "apellido_materno", ""),
                ]
                if str(fragmento).strip()
            )
        razon_social = getattr(cliente, "razon_social", "")
        if str(razon_social).strip():
            return str(razon_social).strip()
        return str(getattr(cliente, "nombre", "PUBLICO GENERAL") or "PUBLICO GENERAL").strip()

    @staticmethod
    def _formatear_direccion_sucursal(sucursal):
        if sucursal is None:
            return ""

        segmentos = [
            getattr(sucursal, "direccion", ""),
            f"CP {getattr(sucursal, 'codigo_postal', '')}" if getattr(sucursal, "codigo_postal", None) else "",
            getattr(sucursal, "ciudad", ""),
            getattr(sucursal, "estado", ""),
            getattr(sucursal, "pais", ""),
        ]
        return ", ".join(segmento.strip() for segmento in segmentos if str(segmento).strip())