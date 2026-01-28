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
# VARIABLES GLOBALES
        total_general = 0
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
            # alignment=TA_LEFT,
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
            [Paragraph("<b>INFORMACIÓN DE EMPRESA</b>", estilo_compacto),
            Paragraph("<b>INFORMACIÓN DE ORDEN</b>", estilo_compacto)],
            [
                Table([
                    [Paragraph("<b>Negocio:</b> " + nombreEmpresa, estilo_compacto)],
                    [Paragraph("<b>Dirección:</b> " + direccionEmpresa, estilo_compacto)],
                    [Paragraph("<b>Teléfono:</b> " + telefonoEmpresa, estilo_compacto)],
                    [Paragraph("<b>Correo:</b> " + correoEmpresa, estilo_compacto)]
                ]),
                Table([
                    [Paragraph("<b>Fecha de Orden:</b> " + fechaOrden, estilo_compacto)],
                    [Paragraph("<b>Proveedor:</b> " + proveedor, estilo_compacto)],
                    [Paragraph("<b>Dirección:</b> " + direccionProveedor, estilo_compacto)],
                    [Paragraph("<b>Teléfono:</b> " + telefonoProveedor, estilo_compacto)],
                    [Paragraph("<b>Correo:</b> " + correoProveedor, estilo_compacto)]
                ])
            ]
        ]
        tabla_principal = Table(datos_tabla_dos_columnas,
         colWidths=[ancho_util*0.5, ancho_util*0.5]
         )
        tabla_principal.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Padding SOLO para la primera fila (los títulos)
            ('LEFTPADDING', (0, 0), (1, 0), 5),  # Solo fila 0, columnas 0 y 1
            ('RIGHTPADDING', (0, 0), (1, 0), 5),
            
            # Para las tablas internas (fila 1), NO aplicar padding
            ('LEFTPADDING', (0, 1), (1, 1), 0),
            
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ]))
        content.append(tabla_principal)
        content.append(Spacer(1, 20))
# TERMINA EL ENCABEZADO --------------------------
# TABLA DE PRODUCTOS ---------------------------
        datos_tabla_productos = [
            [Paragraph("Producto", estilo_compacto),
            Paragraph("Cantidad", estilo_compacto),
            Paragraph("Precio", estilo_compacto),
            Paragraph("Subtotal", estilo_compacto)]
        ]
        tabla_productos = Table(datos_tabla_productos, colWidths=[ancho_util*0.25, ancho_util*0.25, ancho_util*0.25, ancho_util*0.25])
        tabla_productos.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ]))
        content.append(tabla_productos)
        productos_lista =[
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
            {
                "producto": "Producto 1",
                "cantidad": 1,
                "precio": 10.00,
                "subtotal": 10.00
            },
            {
                "producto": "Producto 2",
                "cantidad": 2,
                "precio": 20.00,
                "subtotal": 20.00
            },
        ]
        tablas_productos = []
        total_general = 0

        for producto in productos_lista:
            subtotal = producto["subtotal"]
            total_general += subtotal
            
            tabla_producto = Table([
                [Paragraph(producto["producto"], estilo_compacto),
                Paragraph(str(producto["cantidad"]), estilo_compacto),
                Paragraph(f"${float(producto['precio']):,.2f}", estilo_compacto),
                Paragraph(f"${float(subtotal):,.2f}", estilo_compacto)]
            ], colWidths=[ancho_util*0.25, ancho_util*0.25, ancho_util*0.25, ancho_util*0.25])
            
            tabla_producto.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ]))
            
            tablas_productos.append(tabla_producto)
            content.append(tabla_producto)

        # Ahora agregamos la fila de TOTAL
        espacio_vacio = Spacer(1, 5)  # Espacio de 10 puntos antes del total
        content.append(espacio_vacio)

        # Crear fila de TOTAL
        fila_total = Table([
            [Paragraph("<b>TOTAL</b>", estilo_compacto),
            "",  # Celda vacía para cantidad
            "",  # Celda vacía para precio
            Paragraph(f"<b>${total_general:,.2f}</b>", estilo_compacto)]
        ], colWidths=[ancho_util*0.25, ancho_util*0.25, ancho_util*0.25, ancho_util*0.25])

        fila_total.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (3, 0), (3, 0), 10),  # Más padding a la derecha del monto
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F8F8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
            ('SPAN', (0, 0), (2, 0)),  # Une las primeras 3 celdas para "TOTAL"
        ]))

        content.append(fila_total)
# TERMINA TABLA DE PRODUCTOS -------------------
# CARGA DE DATOS -------------------------------
        self.doc.build(content)

PurchaseOrderPDF()