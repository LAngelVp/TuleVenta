import tempfile
import os
import reportlab.pdfgen.canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, LongTable, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape
from app.runtime_paths import ruta_recurso


def texto_pdf(entidad, campo):
    return escape(str(getattr(entidad, campo, None) or ""))


def fecha_pdf(fecha):
    return str(fecha.date() if isinstance(fecha, datetime) else fecha or "")

class NumberedCanvas(reportlab.pdfgen.canvas.Canvas):
    """Canvas personalizado para agregar número de página"""
    def __init__(self, *args, **kwargs):
        reportlab.pdfgen.canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Agrega número de página a cada página"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            reportlab.pdfgen.canvas.Canvas.showPage(self)
        reportlab.pdfgen.canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Dibuja el número de página en el pie"""
        page = f"Página {self._pageNumber} de {page_count}"
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.gray)
        # Posicionar en la parte inferior centrada
        self.drawCentredString(A4[0]/2, 15*mm, page)

class PurchaseOrderPDF:
    def __init__(self, data=None):
        self.data = data
        self.buffer = BytesIO()
        self.total_general = 0
        self.ancho_util = 0
        self.content = []
        self.doc = None
    
    def get_pdf_bytes(self):
        """Retorna los bytes del PDF"""
        if hasattr(self, 'buffer'):
            return self.buffer.getvalue()
        return None
    
    def save_to_file(self, filename):
        """Guarda el PDF en un archivo"""
        if self.get_pdf_bytes():
            with open(filename, 'wb') as f:
                f.write(self.get_pdf_bytes())
    
    def get_temp_file(self):
        """Crea un archivo temporal con el PDF"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_file.write(self.get_pdf_bytes())
        temp_file.close()
        return temp_file.name
    
    def generar_pdf(self):
        """Método principal para generar el PDF"""
        if not self.data:
            print("Error: No hay datos para generar el PDF")
            return
        self.buffer = BytesIO()
        
        # DIMENSIONES DE LA HOJA
        ancho_total = A4[0]
        topMargin = 20
        bottomMargin = 60
        leftMargin = 20
        rightMargin = 20
        self.ancho_util = ancho_total - leftMargin - rightMargin
        
        # Configurar el documento en el buffer
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            topMargin=topMargin,
            bottomMargin=bottomMargin,
            leftMargin=leftMargin,
            rightMargin=rightMargin
        )
        
        # Limpiar contenido previo
        self.content = []
        self.total_general = 0
        
        # Generar contenido
        self._generar_encabezado()
        self._generar_tabla_productos()
        
        # Construir el documento con canvas personalizado
        try:
            self.doc.build(self.content, canvasmaker=NumberedCanvas)
            # Mover el cursor al inicio del buffer
            self.buffer.seek(0)
        except Exception as e:
            print(f"Error al generar el PDF: {e}")
            raise
    
    def _generar_encabezado(self):
        """Genera el encabezado del documento"""
        # ESTILOS
        estilo_compacto = ParagraphStyle(
            'Compacto',
            fontSize=8,
            textColor='#2C3E50',
            fontName='Helvetica-Bold',
            leading=10,
        )
        self.estilo_firma_centrado = ParagraphStyle(
            'FirmaCentrado',
            parent=estilo_compacto,
            alignment=TA_CENTER,
            fontSize=9,
            textColor='#000000',
            fontName='Helvetica',
            spaceAfter=3,
            spaceBefore=3
        )
        
        # Logo y título
        self.ancho_logo = self.ancho_util * 0.2
        self.ancho_titulo = self.ancho_util * 0.8
        
        logo_path = str(ruta_recurso("app", "Source", "Icons", "logos", "cuadrado_fondo.png"))
        if not os.path.exists(logo_path):
            logo_path = None
        
        datos_encabezado = [
            [
                Image(logo_path, width=1.5*inch, height=0.9*inch) if logo_path else Paragraph("", estilo_compacto),
                Table([
                    [Paragraph("ORDEN DE COMPRA", 
                              ParagraphStyle('Titulo',
                                           fontSize=18,
                                           alignment=TA_RIGHT,
                                           textColor='#2C3E50',
                                           fontName='Helvetica-Bold'))]
                ], colWidths=[self.ancho_titulo])
            ]
        ]
        
        tabla_encabezado = Table(datos_encabezado, colWidths=[self.ancho_logo, self.ancho_titulo])
        tabla_encabezado.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ]))
        
        self.content.append(tabla_encabezado)
        self.content.append(Spacer(1, 15))
        
        # Información de empresa y orden
        empleado = self.data.empleado
        sucursal = getattr(empleado, "sucursal", None)
        proveedor = self.data.proveedor
        self.nombreEmpresa = texto_pdf(sucursal, "nombre_sucursal")
        self.razonSocialEmpresa = texto_pdf(sucursal, "razon_social")
        self.sucursalRFC = texto_pdf(sucursal, "rfc")
        self.direccionEmpresa = ", ".join(texto_pdf(sucursal, campo) for campo in ("direccion", "codigo_postal", "ciudad", "estado", "pais")) if getattr(sucursal, "direccion", None) else ""
        self.telefonoEmpresa = texto_pdf(sucursal, "num_telefono")
        self.correoEmpresa = texto_pdf(empleado, "correo_electronico")
        self.departamentoRealizo = texto_pdf(getattr(empleado, "departamento", None), "nombre")
        self.usuarioRealizo = " ".join(texto_pdf(empleado, campo) for campo in ("nombre", "apellido_paterno", "apellido_materno"))
        self.fechaOrden = fecha_pdf(self.data.fecha_creacion)
        self.proveedor = texto_pdf(proveedor, "nombre")
        self.plazoPago = texto_pdf(self.data, "plazo_pago")
        self.metodoPago = texto_pdf(self.data.metodos_de_pago, "nombre")
        self.fechaVencimientoCompra = fecha_pdf(self.data.fecha_vencimiento)
        self.direccionProveedor = ", ".join(texto_pdf(proveedor, campo) for campo in ("calles", "avenidas", "colonia", "codigo_postal", "ciudad", "estado", "pais")) if getattr(proveedor, "calles", None) else ""
        self.telefonoProveedor = texto_pdf(proveedor, "telefono")
        self.correoProveedor = texto_pdf(proveedor, "correo")
        self.puestoSolicitante = texto_pdf(getattr(empleado, "puesto", None), "nombre")
        
        datos_tabla_dos_columnas = [
            [Paragraph("<b>INFORMACIÓN DE EMPRESA</b>", estilo_compacto),
             Paragraph("<b>INFORMACIÓN DE ORDEN</b>", estilo_compacto)],
            [
                Table([
                    [Paragraph(f"<b>Negocio:</b> {self.nombreEmpresa}", estilo_compacto)],
                    [Paragraph(f"<b>Razón Social:</b> {self.razonSocialEmpresa}", estilo_compacto)],
                    [Paragraph(f"<b>RFC:</b> {self.sucursalRFC}", estilo_compacto)],
                    [Paragraph(f"<b>Dirección:</b> {self.direccionEmpresa}", estilo_compacto)],
                    [Paragraph(f"<b>Teléfono:</b> {self.telefonoEmpresa}", estilo_compacto)],
                    [Paragraph(f"<b>Correo:</b> {self.correoEmpresa}", estilo_compacto)],
                    [Paragraph(f"<b>Departamento:</b> {self.departamentoRealizo}", estilo_compacto)],
                    [Paragraph(f"<b>Usuario:</b> {self.usuarioRealizo}", estilo_compacto)]
                ]),
                Table([
                    [Paragraph(f"<b>Fecha de Orden:</b> {self.fechaOrden}", estilo_compacto)],
                    [Paragraph(f"<b>Proveedor:</b> {self.proveedor}", estilo_compacto)],
                    [Paragraph(f"<b>Plazo de Pago:</b> {self.plazoPago} meses", estilo_compacto)],
                    [Paragraph(f"<b>Metodo de Pago:</b> {self.metodoPago}", estilo_compacto)],
                    [Paragraph(f"<b>Fecha de Vencimiento:</b> {self.fechaVencimientoCompra}", estilo_compacto)],
                    [Paragraph(f"<b>Dirección:</b> {self.direccionProveedor}", estilo_compacto)],
                    [Paragraph(f"<b>Teléfono:</b> {self.telefonoProveedor}", estilo_compacto)],
                    [Paragraph(f"<b>Correo:</b> {self.correoProveedor}", estilo_compacto)]
                ])
            ]
        ]
        
        tabla_principal = Table(datos_tabla_dos_columnas,
                                colWidths=[self.ancho_util*0.5, self.ancho_util*0.5])
        
        tabla_principal.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (1, 0), 5),
            ('RIGHTPADDING', (0, 0), (1, 0), 5),
            ('LEFTPADDING', (0, 1), (1, 1), 0),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ]))
        
        self.content.append(tabla_principal)
        self.content.append(Spacer(1, 20))
    
    def _generar_tabla_productos(self):
        """Genera la tabla de productos con LongTable para cabeceras repetidas"""
        estilo_compacto = ParagraphStyle(
            'Compacto',
            fontSize=8,
            textColor='#2C3E50',
            fontName='Helvetica-Bold',
            leading=10,
        )
        
        # Estilo para cabecera que se repetirá
        estilo_cabecera = ParagraphStyle(
            'Cabecera',
            parent=estilo_compacto,
            fontSize=9,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor='#FFFFFF',
            spaceAfter=5,
            spaceBefore=5
        )
        
        # Preparar datos para LongTable
        datos_longtable = []
        
        # 1. CABECERA (se repetirá en cada página)
        datos_longtable.append([
            Paragraph("Código", estilo_cabecera),
            Paragraph("Producto", estilo_cabecera),
            Paragraph("Descripción", estilo_cabecera),
            Paragraph("Presentación", estilo_cabecera),
            Paragraph("Unidad", estilo_cabecera),
            Paragraph("Cant.", estilo_cabecera),
            Paragraph("Precio Unit.", estilo_cabecera),
            Paragraph("Subtotal", estilo_cabecera)
        ])
        
        # 2. DATOS DE PRODUCTOS
        for elemento in self.data.detalles:
            try:
                subtotal = float(elemento.subtotal)
                self.total_general += subtotal
                
                # Obtener datos
                codigo = str(elemento.producto.codigo_upc) if elemento.producto.codigo_upc else ""
                nombre = str(elemento.producto.nombre_producto) if elemento.producto.nombre_producto else ""
                descripcion = str(elemento.producto.descripcion_producto) if elemento.producto.descripcion_producto else ""
                presentacion = str(elemento.producto.presentacion_productos.nombre) if elemento.producto.presentacion_productos else ""
                
                # Unidad de medida
                unidad_nombre = ""
                if elemento.producto.unidad_medida_productos and elemento.producto.unidad_medida_productos.nombre:
                    partes = elemento.producto.unidad_medida_productos.nombre.split("-")
                    unidad_nombre = partes[1] if len(partes) > 1 else partes[0]
                
                cantidad = str(elemento.cantidad) if elemento.cantidad else "0"
                precio = f"${float(elemento.precio_unitario):,.2f}" if elemento.precio_unitario else "$0.00"
                subtotal_str = f"${subtotal:,.2f}" if subtotal else "$0.00"
                
                # Agregar fila de datos
                datos_longtable.append([
                    Paragraph(escape(codigo), estilo_compacto),
                    Paragraph(escape(nombre), estilo_compacto),
                    Paragraph(escape(descripcion), estilo_compacto),
                    Paragraph(escape(presentacion), estilo_compacto),
                    Paragraph(escape(unidad_nombre), estilo_compacto),
                    Paragraph(cantidad, estilo_compacto),
                    Paragraph(precio, estilo_compacto),
                    Paragraph(subtotal_str, estilo_compacto)
                ])
                
            except Exception as e:
                raise ValueError("No se pudo generar el PDF: detalle de compra invalido.") from e
        
        # 3. FILA DE TOTAL (se agrega como última fila)
        estilo_total = ParagraphStyle(
            'Total',
            parent=estilo_compacto,
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor='#000000'
        )
        
        datos_longtable.append([
            Paragraph("TOTAL", estilo_total),
            "", "", "", "", "",
            Paragraph("", estilo_total),
            Paragraph(f"${self.total_general:,.2f}", estilo_total)
        ])
        
        # Anchos de columnas
        col_widths = [
            self.ancho_util*0.12,   # Código
            self.ancho_util*0.15,   # Producto
            self.ancho_util*0.20,   # Descripción
            self.ancho_util*0.12,   # Presentación
            self.ancho_util*0.10,   # Unidad
            self.ancho_util*0.08,   # Cantidad
            self.ancho_util*0.12,   # Precio
            self.ancho_util*0.11,   # Subtotal
        ]
        
        # Crear LongTable (se repite cabecera automáticamente)
        longtable = LongTable(datos_longtable, colWidths=col_widths, repeatRows=1)
        
        # Estilo para la LongTable
        estilo_longtable = TableStyle([
            # Estilo para cabecera
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A6572')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Estilo para filas de datos
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (1, 1), (-1, -2), 3),
            ('BOTTOMPADDING', (1, 1), (-1, -2), 3),
            
            # Grid
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#E0E0E0')),
            
            # Estilo para fila de total
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F8F8')),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#333333')),
            ('ALIGN', (0, -1), (0, -1), 'LEFT'),
            ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('SPAN', (0, -1), (6, -1)),
            
            # Alineación específica de columnas
            ('ALIGN', (5, 1), (5, -2), 'RIGHT'),  # Cantidad
            ('ALIGN', (6, 1), (-1, -2), 'RIGHT'),  # Precio y Subtotal
        ])
        
        longtable.setStyle(estilo_longtable)
        
        # Agregar la LongTable al contenido
        self.content.append(longtable)
        self.content.append(Spacer(1, 20))
        
        # Firmas
        self._agregar_firmas()
    
    def _agregar_firmas(self):
        """Agrega la sección de firmas"""
        # Tabla de firmas con líneas
        datos_firmas_lineas = [
            [
                # Solicitado
                Table([
                    [self.crear_linea_firma(150)],
                    [Paragraph("<b>SOLICITANTE</b>", self.estilo_firma_centrado)],
                    [Paragraph(f"{self.usuarioRealizo}", ParagraphStyle(
                        'NombreFirma',
                        parent=self.estilo_firma_centrado,
                        fontSize=10
                    ))],
                    [Paragraph(f"Puesto: {self.puestoSolicitante}", self.estilo_firma_centrado)],
                ], style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')])),
                
                # Autorizado
                Table([
                    [self.crear_linea_firma(150)],
                    [Paragraph("<b>AUTORIZACIÓN</b>", self.estilo_firma_centrado)],
                    [Paragraph("____________________________", ParagraphStyle(
                        'NombreFirma',
                        parent=self.estilo_firma_centrado,
                        fontSize=10
                    ))],
                    [Paragraph("Puesto: ______________________", self.estilo_firma_centrado)],
                ], style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')])),
                
                # Proveedor
                Table([
                    [self.crear_linea_firma(150)],
                    [Paragraph("<b>PROVEEDOR</b>", self.estilo_firma_centrado)],
                    [Paragraph(f"{self.proveedor}", ParagraphStyle(
                        'NombreFirma',
                        parent=self.estilo_firma_centrado,
                        fontSize=10
                    ))],
                    [Paragraph("Fecha recepción: _____/_____/_____", self.estilo_firma_centrado)],
                ], style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
            ]
        ]

        tabla_firmas_lineas = Table(datos_firmas_lineas, 
                                colWidths=[self.ancho_util * 0.33, 
                                           self.ancho_util * 0.33, 
                                           self.ancho_util * 0.33])

        tabla_firmas_lineas.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        self.content.append(Spacer(1, 20))
        self.content.append(tabla_firmas_lineas)
    
    def crear_linea_firma(self, ancho=200):
        """Crea una línea horizontal para firma"""
        from reportlab.platypus.flowables import HRFlowable
        return HRFlowable(
            width=ancho,
            thickness=1,
            color=colors.black,
            spaceBefore=5,
            spaceAfter=5
        )