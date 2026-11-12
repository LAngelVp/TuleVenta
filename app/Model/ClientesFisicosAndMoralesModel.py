from .BaseDatosModel import Clientes_fisicos, Clientes_morales, Clientes, Representantes_clientes_morales, Categorias_de_clientes, Areas_negocios
from sqlalchemy.orm import aliased
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload
from .AdministracionEntrada import validar_longitudes, snapshot_cliente

class ClientesFisicosAndMorales:
    def __init__(self, session):
        self.session = session


    def insertar_areas_negocio_basicas(self):
        query = select(Areas_negocios).limit(1)
        resultado_consulta = self.session.execute(query).fetchone()
        if resultado_consulta is None:
            areas_basicas = [
                {"nombre": 'Retail y Comercio al por Menor', "descripcion": "Empresas que venden productos directamente a los consumidores, tanto en tiendas físicas como en línea. Ofrecen una amplia gama de productos, desde ropa hasta alimentos y tecnología"},
                {"nombre": 'Tecnología y Software', "descripcion": "Empresas que desarrollan, venden o distribuyen software, hardware y servicios tecnológicos. Su enfoque está en la innovación digital y la mejora de procesos mediante soluciones tecnológicas avanzadas"},
                {"nombre": 'Servicios Financieros', "descripcion": "Instituciones que ofrecen productos financieros como cuentas bancarias, créditos, seguros, inversiones y asesoría financiera. Ayudan a gestionar los ahorros, inversiones y seguros de individuos y empresas"},
                {"nombre": 'Salud y Bienestar', "descripcion": "Negocios dedicados a servicios médicos, hospitales, clínicas, farmacias y bienestar personal. Ofrecen atención en salud física, mental y nutricional para clientes individuales y corporativos"},
                {"nombre": 'Educación y Capacitación', "descripcion": "Instituciones que proveen servicios educativos, desde educación básica hasta programas de capacitación profesional y universidades. Enfocadas en el desarrollo de habilidades y formación académica de estudiantes."},
                {"nombre": 'Alimentos y Bebidas', "descripcion": "Proveedores de productos alimenticios y bebidas, incluyendo distribución a supermercados, restaurantes, bares y tiendas. Su objetivo es satisfacer las necesidades del mercado de consumo masivo y especializado"},
                {"nombre": 'Turismo y Ocio', "descripcion": "Empresas dedicadas a ofrecer servicios turísticos como agencias de viajes, hoteles, transportes, actividades recreativas y entretenimiento. Ayudan a planificar viajes tanto nacionales como internacionales"},
                {"nombre": 'Construcción e Inmobiliaria', "descripcion": "Empresas que se dedican a la construcción, venta, alquiler o gestión de propiedades residenciales, comerciales e industriales. También abarcan servicios de remodelación y urbanización en distintas localidades"},
                {"nombre": 'Industria Automotriz', "descripcion": "Empresas que fabrican, distribuyen o venden vehículos y repuestos automotrices. Además de proveer servicios de mantenimiento, reparación y accesorios para vehículos particulares y comerciales"},
                {"nombre": 'Entretenimiento y Medios', "descripcion": "Negocios dedicados a la producción de contenido digital, cine, música, deportes, y medios de comunicación. Ofrecen una variedad de servicios, desde distribución hasta creación de contenido en diferentes plataformas"},
                {"nombre": 'Energía y Recursos Naturales', "descripcion": "Empresas dedicadas a la generación, distribución y comercialización de energía, como electricidad, gas y energías renovables. También manejan recursos naturales para industrias como la minería y petróleo"},
                {"nombre": 'Moda y Textiles', "descripcion": "Proveedores y fabricantes de ropa, calzado y accesorios. Ofrecen productos para clientes individuales o para la venta al por mayor en tiendas y boutiques, con un enfoque en tendencias de moda"},
                {"nombre": 'Logística y Transporte', "descripcion": "Empresas que se encargan del transporte de mercancías y distribución a nivel local e internacional. Ofrecen soluciones para la gestión de cadenas de suministro, incluyendo almacenamiento y distribución"},
                {"nombre": 'Servicios de Consultoría', "descripcion": "Firmas que ofrecen asesoramiento en áreas como finanzas, recursos humanos, tecnología, estrategia empresarial, y más. Ayudan a empresas a mejorar sus procesos y tomar decisiones informadas"},
                {"nombre": 'Seguros y Protección', "descripcion": "Compañías que ofrecen productos de seguros para la protección de bienes, salud, vida y otros riesgos. Ayudan a individuos y empresas a mitigar riesgos financieros y pérdidas inesperadas"}
            ]

            self.session.execute(Areas_negocios.__table__.insert(), areas_basicas)
            return True

    def insertar_categorias_negocio_basicas(self):
        query = select(Categorias_de_clientes).limit(1)
        resultado_consulta = self.session.execute(query).fetchone()
        if resultado_consulta is None:
            categorias_basicas = [
                {"nombre": 'Supermercados', "descripcion": "Venta de alimentos, productos de uso doméstico y productos de consumo diario."},
                {"nombre": 'Ropa y Accesorios', "descripcion": "Venta de ropa, calzado y accesorios de moda para hombres, mujeres y niños."},
                {"nombre": 'Electrónica y Tecnología', "descripcion": "Venta de dispositivos electrónicos, computadoras, teléfonos móviles y accesorios tecnológicos."},
                {"nombre": 'Jugueterías', "descripcion": "Venta de juguetes y productos recreativos para niños y adolescentes."},
                {"nombre": 'Muebles y Decoración', "descripcion": "Venta de muebles para el hogar, decoración y artículos para mejorar el ambiente doméstico."},
                {"nombre": 'Software Empresarial', "descripcion": "Soluciones informáticas para la gestión de empresas, como ERP y CRM."},
                {"nombre": 'Hardware', "descripcion": "Venta de componentes electrónicos, computadoras y dispositivos tecnológicos."},
                {"nombre": 'Desarrollo de Aplicaciones', "descripcion": "Servicios de creación y personalización de aplicaciones móviles y de escritorio."},
                {"nombre": 'Servicios de Cloud Computing', "descripcion": "Soluciones basadas en la nube para almacenamiento, computación y respaldo de datos."},
                {"nombre": 'Ciberseguridad', "descripcion": "Servicios enfocados en proteger sistemas informáticos y redes contra amenazas y ataques digitales."},
                {"nombre": 'Banca y Créditos', "descripcion": "Servicios bancarios como cuentas, préstamos, tarjetas de crédito y débito."},
                {"nombre": 'Seguros', "descripcion": "Productos de seguros para vida, salud, auto, hogar y empresas."},
                {"nombre": 'Inversiones', "descripcion": "Servicios de asesoría y productos de inversión para maximizar los rendimientos financieros."},
                {"nombre": 'Consultoría Financiera', "descripcion": "Servicios especializados en la gestión de finanzas personales y corporativas."},
                {"nombre": 'Tecnología Financiera', "descripcion": "Soluciones tecnológicas para la industria financiera, como pagos digitales y fintech."},
                {"nombre": 'Servicios Médicos', "descripcion": "Consultas médicas, diagnósticos y tratamientos médicos en diversas especialidades."},
                {"nombre": 'Farmacias y Medicamentos', "descripcion": "Venta de medicamentos recetados y de venta libre, productos de cuidado personal."},
                {"nombre": 'Nutrición y Suplementos', "descripcion": "Productos para mejorar la salud física, como suplementos alimenticios y dietas."},
                {"nombre": 'Bienestar Mental', "descripcion": "Servicios de terapia psicológica, psicoterapia y bienestar emocional."},
                {"nombre": 'Cuidado de la Salud Preventiva', "descripcion": "Programas y productos enfocados en la prevención de enfermedades y promoción de la salud."},
                {"nombre": 'Escuelas y Universidades', "descripcion": "Instituciones educativas de nivel básico, medio superior y superior."},
                {"nombre": 'Capacitación Profesional', "descripcion": "Cursos y talleres especializados para mejorar las habilidades y competencias laborales."},
                {"nombre": 'Educación en Línea', "descripcion": "Plataformas y programas educativos disponibles en línea para aprendizaje a distancia."},
                {"nombre": 'Consultoría Educativa', "descripcion": "Servicios que ayudan a instituciones educativas y estudiantes a tomar decisiones informadas."},
                {"nombre": 'Material Educativo', "descripcion": "Libros, herramientas, recursos digitales y materiales de apoyo para estudiantes y docentes."},
                {"nombre": 'Distribuidores de Alimentos', "descripcion": "Proveedores mayoristas de alimentos frescos, congelados y procesados."},
                {"nombre": 'Bebidas y Licores', "descripcion": "Distribuidores de bebidas alcohólicas y no alcohólicas para consumo masivo."},
                {"nombre": 'Productos Gourmet', "descripcion": "Venta de alimentos premium, especializados y de alta calidad para consumidores exigentes."},
                {"nombre": 'Comida Rápida y Restaurantes', "descripcion": "Proveedores de productos para restaurantes, food trucks y servicios de comida rápida."},
                {"nombre": 'Catering y Banquetes', "descripcion": "Servicios de catering para eventos, ofreciendo comida y bebida a gran escala."},
                {"nombre": 'Agencias de Viajes', "descripcion": "Agencias que venden paquetes turísticos, boletos de avión y servicios de planificación de viajes."},
                {"nombre": 'Hoteles y Alojamiento', "descripcion": "Servicios de hospedaje, tanto en cadenas hoteleras como en hospedajes independientes."},
                {"nombre": 'Transportes y Renta de Vehículos', "descripcion": "Servicios de transporte turístico y renta de vehículos para turistas."},
                {"nombre": 'Actividades Recreativas', "descripcion": "Empresas que organizan tours, excursiones y actividades recreativas para grupos o individuos."},
                {"nombre": 'Contratistas y Obras', "descripcion": "Empresas que realizan obras de construcción civil, desde edificios hasta infraestructuras públicas."},
                {"nombre": 'Bienes Raíces', "descripcion": "Servicios de compra, venta y alquiler de propiedades residenciales, comerciales e industriales."},
                {"nombre": 'Materiales de Construcción', "descripcion": "Distribuidores de materiales como cemento, acero, madera y otros insumos para construcción."},
                {"nombre": 'Remodelación y Diseño', "descripcion": "Empresas que ofrecen servicios de remodelación, decoración y diseño de interiores."},
                {"nombre": 'Fabricación de Vehículos', "descripcion": "Empresas que fabrican vehículos, tanto para uso personal como comercial."},
                {"nombre": 'Repuestos y Accesorios', "descripcion": "Proveedores de partes y piezas de repuesto para mantenimiento y reparación de vehículos."},
                {"nombre": 'Mantenimiento y Reparación', "descripcion": "Servicios especializados en la reparación, mantenimiento y mejora de vehículos."},
                {"nombre": 'Venta de Automóviles', "descripcion": "Concesionarios y distribuidores de vehículos nuevos y usados."},
                {"nombre": 'Servicios de Flotas', "descripcion": "Gestión y mantenimiento de flotas de vehículos para empresas y particulares."},
                {"nombre": 'Cine y Producción Audiovisual', "descripcion": "Empresas dedicadas a la producción y distribución de películas, series y contenido audiovisual."},
                {"nombre": 'Medios de Comunicación', "descripcion": "Televisión, radio, periódicos y plataformas digitales de noticias y entretenimiento."},
                {"nombre": 'Música y Eventos', "descripcion": "Promotoras de conciertos, festivales y eventos musicales."},
                {"nombre": 'Plataformas de Streaming', "descripcion": "Empresas que ofrecen servicios de transmisión de contenido audiovisual en línea."},
                {"nombre": 'Publicidad y Marketing', "descripcion": "Agencias y consultoras que crean campañas publicitarias para diversos sectores."},
                {"nombre": 'Energía Eléctrica', "descripcion": "Proveedores de servicios de electricidad tanto para usuarios domésticos como comerciales."},
                {"nombre": 'Gas y Petróleo', "descripcion": "Distribuidores de gas natural, petróleo y derivados para consumo industrial y doméstico."},
                {"nombre": 'Energías Renovables', "descripcion": "Proyectos y soluciones basadas en energías limpias como solar, eólica y geotérmica."},
                {"nombre": 'Minería y Extracción', "descripcion": "Empresas dedicadas a la extracción de recursos minerales y naturales para su procesamiento y comercialización."},
                {"nombre": 'Reciclaje y Gestión de Residuos', "descripcion": "Servicios dedicados al reciclaje y gestión adecuada de residuos industriales y urbanos."}
            ]

            self.session.execute(Categorias_de_clientes.__table__.insert(), categorias_basicas)
            # self.session.commit()
            return True

    def agregar_cliente_fisico(self, nombre, correo, rfc, telefono, pais, estado, ciudad, avenidas, calles, codigo_postal, direccion_adicional, entidad_legalizada, categoria_cliente_id, credito, estado_credito, limite_credito, porcentaje_interes, fecha_ultimo_reporte, credito_disponible, credito_utilizado, tipo_cliente, aplica_descuento, porcentaje_descuento, comentarios, areas_de_negocios_id, apellido_paterno, apellido_materno, curp, fecha_nacimiento, num_identificacion, ocupacion, ingresos, estado_civil, foto):
        validar_longitudes(Clientes_fisicos, locals())
        try:
            foto = str(foto).strip() if foto else ""
            cliente_existente = (
                self.session.query(Clientes_fisicos)
                .filter(
                    Clientes.nombre == nombre,
                    Clientes_fisicos.apellido_paterno == apellido_paterno,
                    Clientes_fisicos.curp == curp
                )
                .first()
            )
            if cliente_existente:
                return cliente_existente, None
            else:
                cliente = Clientes_fisicos(
                    nombre = nombre,
                    correo = correo,
                    rfc = rfc,
                    telefono = telefono,
                    pais = pais,
                    estado = estado,
                    ciudad = ciudad,
                    avenidas = avenidas,
                    calles = calles,
                    codigo_postal = codigo_postal,
                    direccion_adicional = direccion_adicional,
                    entidad_legalizada = entidad_legalizada,
                    categoria_cliente_id = categoria_cliente_id,
                    credito = credito,
                    estado_credito = estado_credito,
                    limite_credito = limite_credito,
                    porcentaje_interes = porcentaje_interes,
                    fecha_ultimo_reporte = fecha_ultimo_reporte,
                    credito_disponible = credito_disponible,
                    credito_utilizado = credito_utilizado,
                    tipo_cliente = tipo_cliente,
                    aplica_descuento = aplica_descuento,
                    porcentaje_descuento = porcentaje_descuento,
                    comentarios = comentarios,
                    areas_de_negocios_id = areas_de_negocios_id,
                    apellido_paterno = apellido_paterno,
                    apellido_materno = apellido_materno,
                    curp = curp,
                    fecha_nacimiento = fecha_nacimiento,
                    num_identificacion = num_identificacion,
                    ocupacion = ocupacion,
                    ingresos = ingresos,
                    estado_civil = estado_civil,
                    foto = foto
                    )
                self.session.add(cliente)
                self.session.flush()
                return cliente, True
        except Exception as e:
            raise

    def agregar_cliente_moral(self,nombre, correo, rfc, telefono, pais, estado, ciudad, avenidas, calles, codigo_postal, direccion_adicional, entidad_legalizada, categoria_cliente_id, credito, estado_credito, limite_credito, porcentaje_interes, fecha_ultimo_reporte, credito_disponible, credito_utilizado, tipo_cliente, aplica_descuento, porcentaje_descuento, comentarios, areas_de_negocios_id, razon_social, fecha_constitucion, web, sector, nif, representante_id=None):
        validar_longitudes(Clientes_morales, dict(locals(), NIF=nif))
        try:
            cliente_existente = (self.session.query(Clientes_morales).filter(Clientes.nombre == nombre).filter(Clientes_morales.razon_social == razon_social).first())
            if cliente_existente:
                return cliente_existente, None
            else:
                cliente = Clientes_morales(
                    nombre=nombre, correo = correo , rfc = rfc, telefono = telefono, pais = pais, estado = estado, ciudad = ciudad, avenidas = avenidas, calles = calles, codigo_postal = codigo_postal, direccion_adicional = direccion_adicional, entidad_legalizada = entidad_legalizada, categoria_cliente_id = categoria_cliente_id, credito = credito, estado_credito = estado_credito, limite_credito = limite_credito, porcentaje_interes = porcentaje_interes, fecha_ultimo_reporte = fecha_ultimo_reporte, credito_disponible = credito_disponible, credito_utilizado = credito_utilizado, tipo_cliente = tipo_cliente, aplica_descuento = aplica_descuento,porcentaje_descuento = porcentaje_descuento, comentarios = comentarios, areas_de_negocios_id = areas_de_negocios_id, razon_social = razon_social, fecha_constitucion = fecha_constitucion,  web = web, sector = sector, NIF = nif, representante_id=representante_id
                )
                self.session.add(cliente)
                self.session.flush()
                return cliente, True
        except Exception as e:
            raise

    def agregar_representante_cliente_moral(self, nombre, telefono, correo, puesto):
        validar_longitudes(Representantes_clientes_morales, locals())

        try:
            representante_existente = (self.session.query(Representantes_clientes_morales).filter(Representantes_clientes_morales.nombre == nombre, Representantes_clientes_morales.telefono == telefono).first())
            if representante_existente:
                return representante_existente
            else:
                representante = Representantes_clientes_morales(nombre = nombre, telefono = telefono, correo = correo, puesto = puesto)
                self.session.add(representante)
                self.session.flush()
                return representante
        except Exception as e:
            raise

    def mostrar_clientes_fisicos(self, cantidad_inicial=0, cantidad_final = 100, snapshots=False):
        try:
            clientes = (
                self.session.query(Clientes_fisicos)
                .options(joinedload(Clientes_fisicos.areas_de_negocios), joinedload(Clientes_fisicos.categoria))
                .order_by(Clientes_fisicos.nombre.asc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            return [snapshot_cliente(cliente) for cliente in clientes] if snapshots else clientes, True
        except Exception as e:
            raise

    def mostrar_clientes_morales(self, cantidad_inicial=0, cantidad_final = 100, snapshots=False):
        try:
            clientes = (
                self.session.query(Clientes_morales)
                .options(joinedload(Clientes_morales.areas_de_negocios), joinedload(Clientes_morales.categoria), joinedload(Clientes_morales.representante))
                .order_by(Clientes_morales.nombre.asc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )

            return [snapshot_cliente(cliente) for cliente in clientes] if snapshots else clientes, True
        except Exception as e:
            raise

    def obtener_cliente_fisico_por_id(self, id):
        try:
            clientes_fisicos_alias = aliased(Clientes_fisicos)
            cliente = (self.session.query(Clientes, clientes_fisicos_alias)
                        .join(clientes_fisicos_alias, Clientes.id == clientes_fisicos_alias.id)
                        .filter(Clientes.id == id)
                        .first())
            if cliente:
                return cliente
            else:
                return None
        except Exception as e:
            raise

    def obtener_cliente_moral_por_id(self, id):
        try:
            clientes_morales_alias = aliased(Clientes_morales)
            cliente = (self.session.query(Clientes, clientes_morales_alias)
                        .join(clientes_morales_alias, Clientes.id == clientes_morales_alias.id)
                        .filter(Clientes.id == id)
                        .first())
            if cliente:
                return cliente
            else:
                return None
        except Exception as e:
            raise

    def filtrar_clientes_fisicos_por_nombre(self, texto, cantidad_inicial = 0, cantidad_final = 100, snapshots=False):
        try:
            clientes = (
                self.session.query(Clientes_fisicos)
                .options(
                    joinedload(Clientes_fisicos.areas_de_negocios),
                    joinedload(Clientes_fisicos.categoria)
                )
                .filter(
                    or_(
                        Clientes_fisicos.nombre.ilike(f'%{texto}%'),
                        Clientes_fisicos.apellido_paterno.ilike(f'%{texto}%'),
                        Clientes_fisicos.apellido_materno.ilike(f'%{texto}%'),
                        Clientes_fisicos.curp.ilike(f'%{texto}%')
                    )
                )
                .order_by(Clientes_fisicos.nombre.asc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )
        except Exception as e:
            raise

        return [snapshot_cliente(cliente) for cliente in clientes] if snapshots else clientes, True

    def filtrar_clientes_morales_por_nombre(self, texto, cantidad_inicial = 0, cantidad_final = 100, snapshots=False):
        try:
            clientes = (
                self.session.query(Clientes_morales)
                .options(
                    joinedload(Clientes_morales.areas_de_negocios),
                    joinedload(Clientes_morales.categoria),
                    joinedload(Clientes_morales.representante)
                )
                .filter(
                    or_(
                        Clientes_morales.nombre.ilike(f'%{texto}%'),
                        Clientes_morales.razon_social.ilike(f'%{texto}%'),
                        Clientes_morales.rfc.ilike(f'%{texto}%'),
                        Clientes_morales.NIF.ilike(f'%{texto}%')
                    )
                )
                .order_by(Clientes_morales.nombre.asc())
                .offset(cantidad_inicial)
                .limit(cantidad_final)
                .all()
            )
        except Exception as e:
            raise

        return [snapshot_cliente(cliente) for cliente in clientes] if snapshots else clientes, True

    def actualizar_cliente_fisico(self, id, nombre, correo, rfc, telefono, pais, estado, ciudad, avenidas, calles, codigo_postal, direccion_adicional, entidad_legalizada, categoria_cliente_id, credito, estado_credito, limite_credito, porcentaje_interes, fecha_ultimo_reporte, credito_disponible, credito_utilizado, aplica_descuento, porcentaje_descuento, comentarios, areas_de_negocios_id, apellido_paterno, apellido_materno, curp, fecha_nacimiento, num_identificacion, ocupacion, ingresos, estado_civil, foto):
        validar_longitudes(Clientes_fisicos, locals())
        try:
            foto = str(foto).strip() if foto else ""
            if id:
                # Consultar el cliente base y cliente físico
                resultado = self.session.query(Clientes_fisicos).filter(Clientes_fisicos.id == id).first()
                if resultado is None:
                    return False
                cliente_base = cliente_fisico = resultado

                if cliente_base and cliente_fisico:
                    # Actualizar los campos del cliente base
                    cliente_base.nombre = nombre
                    cliente_base.correo  = correo
                    cliente_base.rfc = rfc
                    cliente_base.telefono = telefono
                    cliente_base.pais = pais
                    cliente_base.estado = estado
                    cliente_base.ciudad = ciudad
                    cliente_base.avenidas = avenidas
                    cliente_base.calles = calles
                    cliente_base.codigo_postal = codigo_postal
                    cliente_base.direccion_adicional = direccion_adicional
                    cliente_base.entidad_legalizada = entidad_legalizada
                    cliente_base.credito = credito
                    cliente_base.estado_credito = estado_credito
                    cliente_base.limite_credito = limite_credito
                    cliente_base.porcentaje_interes = porcentaje_interes
                    cliente_base.fecha_ultimo_reporte = fecha_ultimo_reporte
                    cliente_base.credito_disponible = credito_disponible
                    cliente_base.credito_utilizado = credito_utilizado
                    cliente_base.aplica_descuento = aplica_descuento
                    cliente_base.porcentaje_descuento = porcentaje_descuento
                    cliente_base.comentarios = comentarios

                    # Actualizar los campos del cliente físico
                    cliente_fisico.apellido_paterno = apellido_paterno
                    cliente_fisico.apellido_materno = apellido_materno
                    cliente_fisico.curp = curp
                    cliente_fisico.fecha_nacimiento = fecha_nacimiento
                    cliente_fisico.num_identificacion = num_identificacion
                    cliente_fisico.ocupacion = ocupacion
                    cliente_fisico.ingresos = ingresos
                    cliente_fisico.estado_civil = estado_civil
                    cliente_fisico.foto = foto

                    # Actualizar categoría y área de negocios
                    if categoria_cliente_id:
                        categoria = self.session.query(Categorias_de_clientes).get(categoria_cliente_id)
                        if categoria:
                            cliente_base.categoria = categoria
                        else:
                            raise ValueError("No se encontro la categoria del cliente.")

                    if areas_de_negocios_id:
                        area = self.session.query(Areas_negocios).get(areas_de_negocios_id)
                        if area:
                            cliente_base.areas_de_negocios = area
                        else:
                            raise ValueError("No se encontro el area de negocio del cliente.")

                    return True
                else:
                    return False
        except Exception as e:
            raise

    def actualizar_cliente_moral(self, id, nombre, correo, rfc, telefono, pais, estado, ciudad, avenidas, calles, codigo_postal, direccion_adicional, entidad_legalizada, categoria_cliente_id, credito, estado_credito, limite_credito, porcentaje_interes, fecha_ultimo_reporte, credito_disponible, credito_utilizado, aplica_descuento, porcentaje_descuento, comentarios, areas_de_negocios_id, razon_social, fecha_constitucion, web, sector, nif, nombre_representante, telefono_representante, correo_representante, puesto_representante):
        validar_longitudes(Clientes_morales, dict(locals(), NIF=nif))
        validar_longitudes(Representantes_clientes_morales, {
            "nombre": nombre_representante, "telefono": telefono_representante,
            "correo": correo_representante, "puesto": puesto_representante,
        })
        try:
            if id:
                # Consultar el cliente base y cliente físico
                resultado = self.session.query(Clientes_morales).filter(Clientes_morales.id == id).first()
                if resultado is None:
                    return False
                cliente_base = cliente_moral = resultado

                if cliente_base and cliente_moral:
                    # Actualizar los campos del cliente base
                    cliente_base.nombre = nombre
                    cliente_base.correo  = correo
                    cliente_base.rfc = rfc
                    cliente_base.telefono = telefono
                    cliente_base.pais = pais
                    cliente_base.estado = estado
                    cliente_base.ciudad = ciudad
                    cliente_base.avenidas = avenidas
                    cliente_base.calles = calles
                    cliente_base.codigo_postal = codigo_postal
                    cliente_base.direccion_adicional = direccion_adicional
                    cliente_base.entidad_legalizada = entidad_legalizada
                    cliente_base.credito = credito
                    cliente_base.estado_credito = estado_credito
                    cliente_base.limite_credito = limite_credito
                    cliente_base.porcentaje_interes = porcentaje_interes
                    cliente_base.fecha_ultimo_reporte = fecha_ultimo_reporte
                    cliente_base.credito_disponible = credito_disponible
                    cliente_base.credito_utilizado = credito_utilizado
                    cliente_base.aplica_descuento = aplica_descuento
                    cliente_base.porcentaje_descuento = porcentaje_descuento
                    cliente_base.comentarios = comentarios

                    # Actualizar el cliente moral
                    cliente_moral.razon_social = razon_social
                    cliente_moral.fecha_constitucion = fecha_constitucion
                    cliente_moral.NIF = nif
                    cliente_moral.web = web
                    cliente_moral.sector = sector

                    # Actualizar categoría y área de negocios
                    if categoria_cliente_id:
                        categoria = self.session.query(Categorias_de_clientes).get(categoria_cliente_id)
                        if categoria:
                            cliente_base.categoria = categoria
                        else:
                            raise ValueError("No se encontro la categoria del cliente.")

                    if areas_de_negocios_id:
                        area = self.session.query(Areas_negocios).get(areas_de_negocios_id)
                        if area:
                            cliente_base.areas_de_negocios = area
                        else:
                            raise ValueError("No se encontro el area de negocio del cliente.")
                    # Actualizar o agregar representante
                    if cliente_moral.representante:
                        # Actualizar el primer representante si existe
                        representante = cliente_moral.representante  # O usa un índice adecuado
                        if not (nombre_representante and telefono_representante and correo_representante and puesto_representante):
                            cliente_moral.representante = None
                        else:
                            representante.nombre = nombre_representante
                            representante.telefono = telefono_representante
                            representante.correo = correo_representante
                            representante.puesto = puesto_representante
                    else:
                        # Si no hay representante, crear uno nuevo
                        if nombre_representante and  telefono_representante and correo_representante and puesto_representante:
                            nuevo_representante = self.agregar_representante_cliente_moral(
                                nombre=nombre_representante,
                                telefono=telefono_representante,
                                correo=correo_representante,
                                puesto=puesto_representante
                            )
                            self.session.add(nuevo_representante)
                            cliente_moral.representante = nuevo_representante
                    return True
                else:
                    return False
        except Exception as e:
            raise

    def eliminar_cliente(self, id, modelo):
        try:
            cliente = self.session.query(modelo).filter(modelo.id == id).one_or_none()
            if cliente:
                self.session.delete(cliente)
                return True
            return False
        except Exception as e:
            raise


