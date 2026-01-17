from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from datetime import datetime

class PurchaseOrderPDF:
    def __init__(self):
# DIMENCIONES DE LA HOJA
        ancho_total = A4[0]
        topMargin = 20
        bottomMargin = 25
        leftMargin = 20
        rightMargin = 20
        ancho_util = ancho_total - leftMargin - rightMargin
# ARRAY DE CONTENIDO
        content = []
# CREACION DEL DOCUMENTO
        self.doc = SimpleDocTemplate(
            "OrdenCompra.pdf", 
            pagesize=A4, 
            topMargin=topMargin, 
            bottomMargin=bottomMargin, 
            leftMargin=leftMargin, 
            rightMargin=rightMargin
        )
# ESTILOS:
        estilo_compacto = ParagraphStyle(
            'Compacto',
            fontSize=8,
            alignment=TA_LEFT,
            textColor='#2C3E50',
            fontName='Helvetica-Bold',
            leading=10,
        )
# DATOS DE LA TABLA DEL ENCABEZADO
# DIMENCIONES DE LAS COLUMNAS
        ancho_logo = ancho_util * 0.2
        ancho_titulo = ancho_util * 0.8
        datos = [
            [
                Image("C:/Users/Angel Rodriguez/Microsoft/software-punto-de-venta/app/Source/Icons/logos/cuadrado_fondo.png", 
                     width=1.5*inch, height=0.9*inch),
                Table([
                    [Paragraph("ORDEN DE COMPRA", 
                              ParagraphStyle('Titulo',
                                           fontSize=18,
                                           alignment=TA_RIGHT,
                                           textColor='#2C3E50',
                                           fontName='Helvetica-Bold'))]
                ], colWidths=[ancho_titulo])
            ]
        ]
        tabla = Table(datos, colWidths=[ancho_logo, ancho_titulo])
        tabla.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ]))
        content.append(tabla)
        content.append(Spacer(1, 15))
# FINAL DEL ENCABEZADO
        nombreEmpresa = "Empresa ficticia"
        direccionEmpresa = "Calle Sanchez Loyo, entre JOSE ARRIETA SANCHEZ y MIGUEL HIDALGO, Numero 123, Paso del Macho, Veracruz, CP:94970"
        telefonoEmpresa = "1352-1234-5678"
        correoEmpresa = "[EMAIL_ADDRESS]"
        claveOrden = "123456789"
        fechaOrden = "2022-01-01"
        fechaEntrega = "2022-01-01"
        proveedor = "Proveedor ficticio"
        direccionProveedor = "Calle Sanchez Loyo, entre JOSE ARRIETA SANCHEZ y MIGUEL HIDALGO, Numero 123, Paso del Macho, Veracruz, CP:94970"
        telefonoProveedor = "1352-1234-5678"
        correoProveedor = "[EMAIL_ADDRESS]"
        
        datos_tabla_dos_columnas = [
            # Fila 1: Encabezados (opcional)
            [Paragraph("<b>INFORMACIÓN DE EMPRESA</b>", estilo_compacto),
            Paragraph("<b>INFORMACIÓN DE ORDEN</b>", estilo_compacto)],
            
            # Fila 2: Datos empresa (columna 0) y Datos orden (columna 1)
            [
                # COLUMNA 0: Datos de empresa (como tabla anidada)
                Table([
                    [Paragraph("<b>Negocio:</b> " + nombreEmpresa, estilo_compacto)],
                    [Paragraph("<b>Dirección:</b> " + direccionEmpresa, estilo_compacto)],
                    [Paragraph("<b>Teléfono:</b> " + telefonoEmpresa, estilo_compacto)],
                    [Paragraph("<b>Correo:</b> " + correoEmpresa, estilo_compacto)]
                ]),
                
                # COLUMNA 1: Datos de orden (sin Clave duplicada)
                Table([
                    [Paragraph("<b>Fecha de Orden:</b> " + fechaOrden, estilo_compacto)],
                    [Paragraph("<b>Proveedor:</b> " + proveedor, estilo_compacto)],
                    [Paragraph("<b>Dirección:</b> " + direccionProveedor, estilo_compacto)],
                    [Paragraph("<b>Teléfono:</b> " + telefonoProveedor, estilo_compacto)],
                    [Paragraph("<b>Correo:</b> " + correoProveedor, estilo_compacto)]
                ])
            ]
        ]

        # Crear tabla principal de 2 columnas
        tabla_principal = Table(datos_tabla_dos_columnas, colWidths=[ancho_util*0.5, ancho_util*0.5])

        # Estilo para tabla principal
        tabla_principal.setStyle(TableStyle([
            # Alineación diferente por columna
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),      # Columna 0 (Empresa): IZQUIERDA
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),      # Columna 1 (Orden): IZQUIERDA
            
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Padding entre columnas
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 0),   # Espacio entre columnas
            ('LEFTPADDING', (1, 0), (1, -1), 0),
            
            # Encabezados (si los usas)
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Bordes (opcional)
            # ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ]))
        content.append(tabla_principal)
        content.append(Spacer(1, 20))
        self.doc.build(content)

PurchaseOrderPDF()