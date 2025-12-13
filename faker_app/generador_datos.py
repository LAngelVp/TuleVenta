from sqlalchemy import create_engine
import pandas as pd
import csv
import random
from faker import Faker
from datetime import datetime, timedelta
from openpyxl import Workbook

fake = Faker('es_MX')
random.seed(42)

class Generador_tablas:
    def __init__(self):
        self.cantidad_registros = 10000
        self.conexion = 'postgresql+psycopg2://Dev_Rous:Dev_Rous73@localhost:5432/Dev_Rous'
        self.engine = create_engine(self.conexion)
        
    def creacion_de_productos(self):
        columnas_esperadas = [
            "Proveedor", "Código de Barras", "Nombre", "Categoría", "Marca", "Modelo", "Color",
            "Material", "Unidad de Medida", "Presentación", "Costo Inicial", "Costo Final",
            "Margen Porcentaje", "Precio Venta", "Existencia", "Existencia Min", "Existencia Max", "Peso",
            "Largo Dimensiones", "Alto Dimensiones", "Ancho Dimensiones",
            "Descripción", "Notas", "Fecha Vencimiento", "Fecha Fabricación", "Imagen"
        ]

        def generar_dimensiones():
            largo = round(random.uniform(10.0, 100.0), 2)
            alto = round(random.uniform(10.0, 100.0), 2)
            ancho = round(random.uniform(10.0, 100.0), 2)
            return largo, alto, ancho

        data = []
        for _ in range(self.cantidad_registros):
            largo, alto, ancho = generar_dimensiones()
            costo_inicial = round(random.uniform(10, 100), 2)
            margen = round(random.uniform(5, 50), 2)
            costo_final = round(costo_inicial * (1 + margen / 100), 2)
            precio_venta = round(costo_final * 1.2, 2)

            producto = {
                "Proveedor": fake.company(),
                "Código de Barras": fake.unique.ean(length=13),
                "Nombre": fake.word().capitalize() + " " + fake.word().capitalize(),
                "Categoría": fake.word().capitalize(),
                "Marca": fake.company(),
                "Modelo": fake.bothify(text='??-####'),
                "Color": fake.color_name(),
                "Material": fake.word().capitalize(),
                "Unidad de Medida": random.choice(["Unidad", "Caja", "Litro", "Metro"]),
                "Presentación": random.choice(["Botella", "Caja", "Bolsa", "Paquete"]),
                "Costo Inicial": costo_inicial,
                "Costo Final": costo_final,
                "Margen Porcentaje": f"{margen}%",
                "Precio Venta": precio_venta,
                "Existencia": round(random.uniform(0, 500), 2),
                "Existencia Min": round(random.uniform(0, 50), 2),
                "Existencia Max": round(random.uniform(100, 1000), 2),
                "Peso": round(random.uniform(0.1, 10.0), 2),
                "Largo Dimensiones": largo,
                "Alto Dimensiones": alto,
                "Ancho Dimensiones": ancho,
                "Descripción": fake.text(max_nb_chars=100),
                "Notas": fake.sentence(nb_words=6),
                "Fecha Vencimiento": fake.date_between(start_date='today', end_date='+2y'),
                "Fecha Fabricación": fake.date_between(start_date='-2y', end_date='today'),
                "Imagen": fake.image_url()
            }
            data.append(producto)

        df = pd.DataFrame(data)
        df.to_excel("documento_datos.xlsx", index=False)
        print(f"✅ Se generó documento_datos.xlsx con {self.cantidad_registros} productos.")

    def creacion_empleados(self):
        def generar_empleado():
            genero = random.choice(['Masculino', 'Femenino'])
            fecha_despido = None
            if random.random() < 0.2:
                fecha_despido = fake.date_between(start_date='-5y', end_date='today')

            return {
                "nombre": fake.first_name_male() if genero == "Masculino" else fake.first_name_female(),
                "apellido_paterno": fake.last_name(),
                "apellido_materno": fake.last_name(),
                "genero": genero,
                "fecha_nacimiento": fake.date_of_birth(minimum_age=18, maximum_age=60).strftime("%Y-%m-%d"),
                "estado_civil": random.choice(['Soltero', 'Casado', 'Divorciado', 'Viudo']),
                "curp": fake.unique.bothify(text='????######??????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                "rfc": fake.unique.bothify(text='????######???', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                "nivel_academico": random.choice(['Licenciatura', 'Maestría', 'Doctorado', 'Técnico', 'Bachillerato']),
                "carrera": fake.job(),
                "correo_electronico": fake.unique.email(),
                "numero_seguro_social": fake.unique.numerify(text='###########'),
                "fecha_contratacion": fake.date_between(start_date='-10y', end_date='today').strftime("%Y-%m-%d"),
                "fecha_despido": fecha_despido.strftime("%Y-%m-%d") if fecha_despido else None,
                "ciudad": fake.city(),
                "codigo_postal": fake.postcode()[:5],
                "estado": fake.state(),
                "pais": "México",
                "numero_telefonico": fake.numerify(text='##########'),
                "nombre_contacto": fake.name(),
                "contacto_emergencia": fake.numerify(text='##########'),
                "parentesco_contacto": random.choice(['Padre', 'Madre', 'Hermano', 'Esposo', 'Amigo']),
                "calles": fake.street_name(),
                "avenidas": fake.street_name(),
                "colonia": fake.city_suffix(),
                "num_interior": fake.building_number() if random.random() > 0.3 else None,
                "num_exterior": fake.building_number(),
                "direccion_adicional": fake.address(),
                "activo": random.choice([True, False]),
                "foto": None,
                "puesto_id": None,
                "usuario_id": None,
                "departamento_id": None,
                "sucursal_id": None,
            }

        empleados = [generar_empleado() for _ in range(self.cantidad_registros)]
        df_empleados = pd.DataFrame(empleados)
        columnas_bol=df_empleados.select_dtypes(include=bool).columns.tolist()
        df_empleados[columnas_bol] = df_empleados[columnas_bol].astype(str)
        # df_empleados.to_csv("empleados_fake.csv",sep=';', index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
        df_empleados.to_sql('Empleados', con=self.engine, if_exists='append', index=False)
        print(f"✅ Se generó empleados_fake.xlsx con {self.cantidad_registros} empleados.")

    def creacion_de_clientes(self):
        # Primero, obtener los IDs existentes de las tablas relacionadas
        try:
            # Obtener categorías existentes
            query_categorias = "SELECT id FROM Categorias_de_clientes"
            categorias_df = pd.read_sql(query_categorias, self.engine)
            categorias_ids = categorias_df['id'].tolist()
            
            if not categorias_ids:
                raise ValueError("No hay categorías en la tabla Categorias_de_clientes")
            
            # Obtener áreas de negocio existentes
            query_areas = "SELECT id FROM Areas_negocios"
            areas_df = pd.read_sql(query_areas, self.engine)
            areas_ids = areas_df['id'].tolist()
            
            if not areas_ids:
                raise ValueError("No hay áreas en la tabla Areas_negocios")
            
            # Obtener representantes existentes
            query_representantes = "SELECT id FROM Representantes_clientes_morales"
            representantes_df = pd.read_sql(query_representantes, self.engine)
            representantes_ids = representantes_df['id'].tolist()
            
        except Exception as e:
            print(f"❌ Error al leer tablas existentes: {e}")
            print("Asegúrate de que las tablas relacionadas ya existen y tienen datos")
            return
        
        # Generar clientes
        clientes_fisicos = []
        clientes_morales = []
        clientes_generales = []
        
        print(f"🔧 Generando {self.cantidad_registros} clientes...")
        
        # Obtener el último ID de cliente para continuar desde ahí
        try:
            query_max_id = "SELECT MAX(id) as max_id FROM Clientes"
            max_id_df = pd.read_sql(query_max_id, self.engine)
            start_id = max_id_df['max_id'].iloc[0]
            if pd.isna(start_id):
                start_id = 1
            else:
                start_id = int(start_id) + 1
        except:
            start_id = 1
        
        for i in range(self.cantidad_registros):
            cliente_id = start_id + i
            es_moral = random.random() < 0.3  # 30% clientes morales, 70% físicos
            
            # Datos comunes para todos los clientes
            tiene_credito = random.random() < 0.7  # 70% tienen crédito
            limite_credito = round(random.uniform(1000, 100000), 2) if tiene_credito else 0
            credito_utilizado = round(random.uniform(0, limite_credito * 0.8), 2) if tiene_credito else 0
            
            # Fechas aleatorias
            fecha_reporte = fake.date_time_between(start_date='-1y', end_date='now')
            
            # Nombre según tipo de cliente
            if es_moral:
                nombre = fake.company()
            else:
                nombre = fake.first_name()
            
            cliente_general = {
                "id": cliente_id,
                "nombre": nombre,
                "correo": fake.unique.email(),
                "rfc": self._generar_rfc_valido(),
                "telefono": fake.numerify(text='##########'),
                "pais": "México",
                "estado": fake.state(),
                "ciudad": fake.city(),
                "avenidas": fake.street_name(),
                "calles": fake.street_name(),
                "codigo_postal": fake.postcode()[:5],
                "direccion_adicional": fake.address(),
                "entidad_legalizada": random.choice([True, False]),
                "categoria_cliente_id": random.choice(categorias_ids),
                "credito": tiene_credito,
                "estado_credito": random.choice(["Activo", "Suspendido", "Cancelado", "En revisión"]) if tiene_credito else "Sin crédito",
                "limite_credito": limite_credito,
                "porcentaje_interes": round(random.uniform(5, 30), 2) if tiene_credito else 0,
                "fecha_ultimo_reporte": fecha_reporte,
                "credito_disponible": limite_credito - credito_utilizado,
                "credito_utilizado": credito_utilizado,
                "tipo_cliente": "MORAL" if es_moral else "FISICO",
                "aplica_descuento": random.choice([True, False]),
                "porcentaje_descuento": round(random.uniform(0, 20), 2),
                "comentarios": fake.sentence(nb_words=10),
                "areas_de_negocios_id": random.choice(areas_ids)
            }
            
            if es_moral:
                # Datos específicos para cliente moral
                cliente_moral = {
                    "id": cliente_id,
                    "razon_social": fake.company(),
                    "fecha_constitucion": fake.date_between(start_date='-30y', end_date='-1y'),
                    "web": fake.url(),
                    "sector": random.choice(["Tecnología", "Manufactura", "Retail", "Servicios", 
                                            "Alimentos", "Construcción", "Salud", "Educación", 
                                            "Finanzas", "Transporte"]),
                    "NIF": fake.unique.bothify(text='NIF##########'),
                    "representante_id": random.choice(representantes_ids) if representantes_ids else None
                }
                clientes_morales.append(cliente_moral)
            else:
                # Datos específicos para cliente físico
                genero = random.choice(['Masculino', 'Femenino'])
                apellido_paterno = fake.last_name()
                apellido_materno = fake.last_name()
                nombre_completo = f"{nombre} {apellido_paterno} {apellido_materno}"
                
                # Actualizar nombre en cliente general para que incluya apellidos
                cliente_general["nombre"] = nombre_completo
                
                # Generar CURP (formato básico)
                curp_base = f"{apellido_paterno[:2]}{apellido_materno[:1]}{nombre[:1]}"
                curp_sufijo = fake.bothify(text='######??????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                
                cliente_fisico = {
                    "id": cliente_id,
                    "apellido_paterno": apellido_paterno,
                    "apellido_materno": apellido_materno,
                    "curp": f"{curp_base}{curp_sufijo}".upper()[:18],
                    "fecha_nacimiento": fake.date_of_birth(minimum_age=18, maximum_age=80),
                    "num_identificacion": fake.unique.bothify(text='INE##########'),
                    "ocupacion": fake.job(),
                    "ingresos": round(random.uniform(5000, 50000), 2),
                    "estado_civil": random.choice(['Soltero', 'Casado', 'Divorciado', 'Viudo', 'Unión libre']),
                    "foto": None
                }
                clientes_fisicos.append(cliente_fisico)
            
            clientes_generales.append(cliente_general)
            
            # Mostrar progreso cada 1000 registros
            if (i + 1) % 1000 == 0:
                print(f"   ✅ Generados {i + 1} clientes...")
        
        # Convertir a DataFrames
        df_clientes_generales = pd.DataFrame(clientes_generales)
        df_clientes_fisicos = pd.DataFrame(clientes_fisicos)
        df_clientes_morales = pd.DataFrame(clientes_morales)
        
        # Convertir columnas booleanas para PostgreSQL
        columnas_bool = df_clientes_generales.select_dtypes(include=bool).columns.tolist()
        if columnas_bool:
            df_clientes_generales[columnas_bool] = df_clientes_generales[columnas_bool].astype(str)
        
        # Insertar en la base de datos (append, no replace)
        print("\n💾 Insertando datos en la base de datos...")
        
        try:
            # Insertar clientes generales
            df_clientes_generales.to_sql('Clientes', con=self.engine, if_exists='append', index=False)
            print(f"✅ Insertados {len(clientes_generales)} registros en 'Clientes'")
            
            # Insertar clientes físicos si hay
            if not df_clientes_fisicos.empty:
                df_clientes_fisicos.to_sql('Clientes_fisicos', con=self.engine, if_exists='append', index=False)
                print(f"✅ Insertados {len(clientes_fisicos)} registros en 'Clientes_fisicos'")
            
            # Insertar clientes morales si hay
            if not df_clientes_morales.empty:
                df_clientes_morales.to_sql('Clientes_morales', con=self.engine, if_exists='append', index=False)
                print(f"✅ Insertados {len(clientes_morales)} registros en 'Clientes_morales'")
            
            # Guardar también en archivos CSV por si acaso
            df_clientes_generales.to_csv("clientes_generales.csv", sep=';', index=False, 
                                       encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
            
            if not df_clientes_fisicos.empty:
                df_clientes_fisicos.to_csv("clientes_fisicos.csv", sep=';', index=False, 
                                         encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
            
            if not df_clientes_morales.empty:
                df_clientes_morales.to_csv("clientes_morales.csv", sep=';', index=False, 
                                         encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
            
            print("\n🎯 Resumen final:")
            print(f"   - Total clientes insertados: {self.cantidad_registros}")
            print(f"   - Clientes físicos: {len(clientes_fisicos)}")
            print(f"   - Clientes morales: {len(clientes_morales)}")
            print(f"   - Archivos CSV generados: clientes_generales.csv, clientes_fisicos.csv, clientes_morales.csv")
            print("\n✅ ¡Proceso completado exitosamente!")
            
        except Exception as e:
            print(f"❌ Error al insertar en la base de datos: {e}")
            # Guardar en CSV aunque falle la inserción
            print("Guardando datos en archivos CSV como respaldo...")
            df_clientes_generales.to_csv("clientes_generales_backup.csv", sep=';', index=False, 
                                       encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    
    def _generar_rfc_valido(self):
        """Genera un RFC válido para México"""
        # Para persona física
        if random.random() < 0.7:
            apellido1 = fake.last_name()[:2].upper()
            apellido2 = fake.last_name()[:1].upper()
            nombre = fake.first_name()[:1].upper()
            fecha = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%y%m%d')
            homoclave = fake.bothify(text='???', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            return f"{apellido1}{apellido2}{nombre}{fecha}{homoclave}"[:13]
        else:
            # Para persona moral
            palabras = fake.company().split()
            iniciales = ''.join([p[:1] for p in palabras[:3]]).upper()
            fecha = fake.date_between(start_date='-30y', end_date='-1y').strftime('%y%m%d')
            homoclave = fake.bothify(text='???', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            return f"{iniciales}{fecha}{homoclave}"[:12]

# Para usar con tu clase existente
# if __name__ == "__main__":
#     from sqlalchemy import create_engine
    
#     # Asegúrate de que las tablas relacionadas ya existen con datos:
#     # - Categorias_de_clientes (con algunos registros)
#     # - Areas_negocios (con algunos registros)
#     # - Representantes_clientes_morales (opcional, para clientes morales)
    
generador = Generador_tablas()
generador.creacion_de_clientes()

# Generador_tablas().creacion_empleados()