import uuid
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    Float,
    ForeignKey,
    Table,
    Index,
    BigInteger,
    LargeBinary,
    Boolean,
    CHAR,
    DateTime,
    Time
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, configure_mappers, Mapped, mapped_column

# configure_mappers()
Base = declarative_base()

# Tabla M:M entre Roles y Permisos
rol_permiso = Table(
    "rol_permisos",
    Base.metadata,
    Column("rol_id", BigInteger, ForeignKey("Roles.id",ondelete='CASCADE'), primary_key=True),
    Column("permiso_id", BigInteger, ForeignKey("Permisos.id"), primary_key=True),
)

usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", BigInteger, ForeignKey("Usuarios.id"), primary_key=True),
    Column("rol_id", BigInteger, ForeignKey("Roles.id"), primary_key=True),
)

sucursal_producto = Table(
    "sucursal_producto",
    Base.metadata,
    Column("sucursal_id", BigInteger, ForeignKey("Sucursales.id"), primary_key=True),
    Column("producto_id", BigInteger, ForeignKey("Productos.id"), primary_key=True),
)

proveedor_categoria = Table(
    "proveedor_categoria",
    Base.metadata,
    Column("proveedor_id", BigInteger, ForeignKey("Proveedores.id"), primary_key=True),
    Column(
        "categoria_id",
        BigInteger,
        ForeignKey("Categorias_proveedores.id"),
        primary_key=True,
    ),
)

departamento_sucursal = Table(
    "departamento_sucursal",
    Base.metadata,
    Column(
        "departamento_id", BigInteger, ForeignKey("Departamentos.id"), primary_key=True
    ),
    Column("sucursal_id", BigInteger, ForeignKey("Sucursales.id"), primary_key=True),
)

# Apartado de Permisos
class Permisos(Base):
    __tablename__ = "Permisos"
    id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre:Mapped[str] = mapped_column(String(50), unique=True)
    roles = relationship(
        "Roles", secondary=rol_permiso, back_populates="permisos", 
        )

# Apartado de Roles
class Roles(Base):
    __tablename__ = "Roles"
    id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre:Mapped[str] = mapped_column(String(100), unique=True)
    descripcion:Mapped[str] = mapped_column(Text)
    permisos = relationship(
        "Permisos", secondary=rol_permiso, back_populates="roles"
        )
    usuarios = relationship("Usuarios", back_populates="rol")

# Apartado de Usuarios
class Usuarios(Base):
    __tablename__ = "Usuarios"
    id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario:Mapped[str] = mapped_column(String(60), unique=True, nullable=True)
    contraseña:Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    fecha_creacion:Mapped[datetime] = mapped_column(Date, nullable=False)
    fecha_actualizacion:Mapped[datetime] = mapped_column(Date, nullable=True)
    rol_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Roles.id", ondelete='SET NULL'),
        nullable=True
    )
    rol = relationship("Roles", back_populates="usuarios")
    empleado = relationship("Empleados", uselist=False, back_populates="usuario")
    movimientos_inventario = relationship("Movimientos_Inventario", back_populates="usuario")

# Apartado de Puestos
class Puestos(Base):
    __tablename__ = "Puestos"
    id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre:Mapped[str] = mapped_column(String(100))
    salario:Mapped[float] = mapped_column(Float)
    horas_laborales:Mapped[float] = mapped_column(Float)
    dias_laborales:Mapped[str] = mapped_column(Text)
    descripcion_puesto:Mapped[str] = mapped_column(Text)
    hora_entrada:Mapped[datetime] = mapped_column(Time)
    hora_salida:Mapped[datetime] = mapped_column(Time)
    empleados = relationship("Empleados", back_populates="puesto")
    departamento_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Departamentos.id", ondelete='SET NULL'),
        nullable=True
        )
    departamento = relationship(
        "Departamentos", back_populates="puestos", lazy="joined"
    )
    hora_salida:Mapped[datetime] = mapped_column(Time)
    empleados = relationship("Empleados", back_populates="puesto")
    departamento_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Departamentos.id", ondelete='SET NULL'),
        nullable=True
    )
    departamento = relationship(
        "Departamentos", back_populates="puestos", lazy="joined"
    )

# Apartado de Empleados
class Empleados(Base):
    __tablename__ = "Empleados"
    id:Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre:Mapped[str] = mapped_column(String(100))
    apellido_paterno:Mapped[str] = mapped_column(String(100))
    apellido_materno:Mapped[str] = mapped_column(String(100))
    genero:Mapped[str] = mapped_column(String(20))
    fecha_nacimiento:Mapped[datetime] = mapped_column(Date)
    estado_civil:Mapped[str] = mapped_column(String(20))
    curp:Mapped[str] = mapped_column(String(18), unique=True)
    rfc:Mapped[str] = mapped_column(String(13), unique=True)
    nivel_academico:Mapped[str] = mapped_column(String(100))
    carrera:Mapped[str] = mapped_column(String(150))
    correo_electronico:Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    numero_seguro_social:Mapped[str] = mapped_column(String(13), unique=True)
    fecha_contratacion:Mapped[datetime] = mapped_column(Date)
    fecha_despido:Mapped[datetime] = mapped_column(Date, nullable=True)
    ciudad:Mapped[str] = mapped_column(String(100), nullable=True)
    codigo_postal:Mapped[str] = mapped_column(String(5), nullable=True)
    estado:Mapped[str] = mapped_column(String(100), nullable=True)
    pais:Mapped[str] = mapped_column(String(100), nullable=True)
    numero_telefonico:Mapped[str] = mapped_column(String(10), nullable=True)
    nombre_contacto:Mapped[str] = mapped_column(String(100), nullable=True)
    contacto_emergencia:Mapped[str] = mapped_column(String(10))
    parentesco_contacto:Mapped[str] = mapped_column(String(20))
    calles:Mapped[str] = mapped_column(String(100), nullable=True)
    avenidas:Mapped[str] = mapped_column(String(100), nullable=True)
    colonia:Mapped[str] = mapped_column(String(100))
    num_interior:Mapped[str] = mapped_column(String(10), nullable=True)
    num_exterior:Mapped[str] = mapped_column(String(10), nullable=True)
    direccion_adicional:Mapped[str] = mapped_column(Text, nullable=True)
    puesto_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Puestos.id", ondelete='SET NULL'),
        nullable=True
    )
    puesto = relationship("Puestos", back_populates="empleados")
    departamento_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Departamentos.id", ondelete='SET NULL'),
        nullable=True
    )
    departamento = relationship(
        "Departamentos", back_populates="empleados", lazy="joined"
    )
    fecha_contratacion:Mapped[datetime] = mapped_column(Date)
    fecha_despido:Mapped[datetime] = mapped_column(Date, nullable=True)
    ciudad:Mapped[str] = mapped_column(String(100), nullable=True)
    codigo_postal:Mapped[str] = mapped_column(String(5), nullable=True)
    estado:Mapped[str] = mapped_column(String(100), nullable=True)
    pais:Mapped[str] = mapped_column(String(100), nullable=True)
    numero_telefonico:Mapped[str] = mapped_column(String(10), nullable=True)
    nombre_contacto:Mapped[str] = mapped_column(String(100), nullable=True)
    contacto_emergencia:Mapped[str] = mapped_column(String(10))
    parentesco_contacto:Mapped[str] = mapped_column(String(20))
    calles:Mapped[str] = mapped_column(String(100), nullable=True)
    avenidas:Mapped[str] = mapped_column(String(100), nullable=True)
    colonia:Mapped[str] = mapped_column(String(100))
    num_interior:Mapped[str] = mapped_column(String(10), nullable=True)
    num_exterior:Mapped[str] = mapped_column(String(10), nullable=True)
    direccion_adicional:Mapped[str] = mapped_column(Text, nullable=True)
    puesto_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Puestos.id", ondelete='SET NULL'),
        nullable=True
    )
    puesto = relationship("Puestos", back_populates="empleados")
    departamento_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Departamentos.id", ondelete='SET NULL'),
        nullable=True
    )
    departamento = relationship(
        "Departamentos", back_populates="empleados", lazy="joined"
    )
    fecha_contratacion:Mapped[datetime] = mapped_column(Date)
    fecha_despido:Mapped[datetime] = mapped_column(Date, nullable=True)
    ciudad:Mapped[str] = mapped_column(String(100), nullable=True)
    codigo_postal:Mapped[str] = mapped_column(String(5), nullable=True)
    estado:Mapped[str] = mapped_column(String(100), nullable=True)
    pais:Mapped[str] = mapped_column(String(100), nullable=True)
    numero_telefonico:Mapped[str] = mapped_column(String(10), nullable=True)
    nombre_contacto:Mapped[str] = mapped_column(String(100), nullable=True)
    contacto_emergencia:Mapped[str] = mapped_column(String(10))
    parentesco_contacto:Mapped[str] = mapped_column(String(20))
    calles:Mapped[str] = mapped_column(String(100), nullable=True)
    avenidas:Mapped[str] = mapped_column(String(100), nullable=True)
    colonia:Mapped[str] = mapped_column(String(100))
    num_interior:Mapped[str] = mapped_column(String(10), nullable=True)
    num_exterior:Mapped[str] = mapped_column(String(10), nullable=True)
    direccion_adicional:Mapped[str] = mapped_column(Text, nullable=True)
    puesto_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Puestos.id", ondelete='SET NULL'),
        nullable=True
    )
    puesto = relationship("Puestos", back_populates="empleados")
    departamento_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Departamentos.id", ondelete='SET NULL'),
        nullable=True
    )
    departamento = relationship(
        "Departamentos", back_populates="empleados", lazy="joined"
    )
    fecha_contratacion:Mapped[datetime] = mapped_column(Date)
    fecha_despido:Mapped[datetime] = mapped_column(Date, nullable=True)
    ciudad:Mapped[str] = mapped_column(String(100), nullable=True)
    codigo_postal:Mapped[str] = mapped_column(String(5), nullable=True)
    estado:Mapped[str] = mapped_column(String(100), nullable=True)
    pais:Mapped[str] = mapped_column(String(100), nullable=True)
    numero_telefonico:Mapped[str] = mapped_column(String(10), nullable=True)
    nombre_contacto:Mapped[str] = mapped_column(String(100), nullable=True)
    estado_civil:Mapped[str] = mapped_column(String(20))
    curp:Mapped[str] = mapped_column(String(18), unique=True)
    rfc:Mapped[str] = mapped_column(String(13), unique=True)
    nivel_academico:Mapped[str] = mapped_column(String(100))
    carrera:Mapped[str] = mapped_column(String(150))
    correo_electronico:Mapped[str] = mapped_column(String(100), nullable=True, unique=True)
    numero_seguro_social:Mapped[str] = mapped_column(String(13), unique=True)
    fecha_contratacion:Mapped[datetime] = mapped_column(Date)
    fecha_despido:Mapped[datetime] = mapped_column(Date, nullable=True)
    contacto_emergencia:Mapped[str] = mapped_column(String(10))
    parentesco_contacto:Mapped[str] = mapped_column(String(20))
    calles:Mapped[str] = mapped_column(String(100), nullable=True)
    avenidas:Mapped[str] = mapped_column(String(100), nullable=True)
    colonia:Mapped[str] = mapped_column(String(100))
    num_interior:Mapped[str] = mapped_column(String(10), nullable=True)
    num_exterior:Mapped[str] = mapped_column(String(10), nullable=True)
    direccion_adicional:Mapped[str] = mapped_column(Text, nullable=True)
    activo:Mapped[bool] = mapped_column(Boolean, default=True)
    foto:Mapped[str] = mapped_column(Text, nullable=True)
    puesto_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Puestos.id", ondelete='SET NULL'),
        nullable=True
    )
    puesto = relationship("Puestos", back_populates="empleados", lazy="joined")
    usuario_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Usuarios.id", ondelete='SET NULL'),
        nullable=True
    )
    usuario = relationship("Usuarios", back_populates="empleado")
    ventas = relationship("Ventas", back_populates="empleado")
    turnos = relationship("Turnos", back_populates="empleado")
    departamento_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Departamentos.id", ondelete='RESTRICT'),
        nullable=True
    )
    departamento = relationship("Departamentos", back_populates="empleados", lazy="joined")
    sucursal_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Sucursales.id", ondelete='RESTRICT'),
        nullable=True
    )
    sucursal = relationship("Sucursales", back_populates="empleados", lazy="joined")
    compras = relationship("Compras", back_populates="empleado")

class Sucursales(Base):
    __tablename__ = "Sucursales"
    id:Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
        )
    nombre_sucursal:Mapped[str] = mapped_column(String(50))
    codigo_postal:Mapped[str] = mapped_column(String(5))
    ciudad:Mapped[str] = mapped_column(String(50))
    estado:Mapped[str] = mapped_column(String(50))
    pais:Mapped[str] = mapped_column(String(50))
    num_telefono:Mapped[str] = mapped_column(String(10))
    razon_social:Mapped[str] = mapped_column(String(300))
    rfc:Mapped[str] = mapped_column(String(13))
    direccion:Mapped[str] = mapped_column(Text)
    productos = relationship(
        "Productos", secondary=sucursal_producto, back_populates="sucursales"
    )
    departamentos = relationship(
        "Departamentos", secondary=departamento_sucursal, back_populates="sucursales"
    )
    empleados = relationship("Empleados", back_populates="sucursal")

class Departamentos(Base):
    __tablename__ = "Departamentos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(70))
    descripcion:Mapped[str] = mapped_column(Text)
    empleados = relationship(
        "Empleados", back_populates="departamento"
    )  # Relación con la tabla de empleados
    puestos = relationship(
        "Puestos", back_populates="departamento"
    )  # Relación uno a muchos con Puestos
    sucursales = relationship(
        "Sucursales", secondary=departamento_sucursal, back_populates="departamentos",  lazy="select", cascade="save-update, merge", passive_deletes=True
    )

class Presentacion_productos(Base):
    __tablename__ = "Presentacion_productos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100), nullable=False)
    productos = relationship("Productos", back_populates="presentacion_productos")
    
class Unidad_medida_productos(Base):
    __tablename__ = "Unidad_medida_productos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    productos = relationship("Productos", back_populates="unidad_medida_productos")
    
class Productos(Base):
    __tablename__ = "Productos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
    )
    codigo_upc:Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre_producto:Mapped[str] = mapped_column(String(60))
    descripcion_producto:Mapped[str] = mapped_column(Text)
    costo_inicial:Mapped[float] = mapped_column(Float)
    costo_final:Mapped[float] = mapped_column(Float)
    margen_porcentaje:Mapped[float] = mapped_column(Float)
    precio:Mapped[float] = mapped_column(Float)
    existencia:Mapped[float] = mapped_column(Float)
    existencia_minima:Mapped[float] = mapped_column(Float)
    existencia_maxima:Mapped[float] = mapped_column(Float)
    marca:Mapped[str] = mapped_column(String(100))
    modelo:Mapped[str] = mapped_column(String(100))
    peso:Mapped[float] = mapped_column(Float)
    alto_cm:Mapped[float] = mapped_column(Float)
    largo_cm:Mapped[float] = mapped_column(Float)
    ancho_cm:Mapped[float] = mapped_column(Float)
    color:Mapped[str] = mapped_column(String(255))
    material:Mapped[str] = mapped_column(String(255))
    fecha_fabricacion:Mapped[datetime] = mapped_column(Date)
    fecha_vencimiento:Mapped[datetime] = mapped_column(Date, nullable=True)
    imagen:Mapped[str] = mapped_column(Text)
    notas:Mapped[str] = mapped_column(Text)
    presentacion_producto_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Presentacion_productos.id", ondelete='SET NULL'), nullable=True)
    presentacion_productos = relationship("Presentacion_productos", back_populates="productos")
    unidad_medida_productos_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Unidad_medida_productos.id", ondelete='SET NULL'), nullable=True)
    unidad_medida_productos = relationship("Unidad_medida_productos", back_populates="productos")
    categoria_id:Mapped[int] = mapped_column(BigInteger, ForeignKey('Categorias_productos.id', ondelete='SET NULL'), nullable=True)
    categoria = relationship("Categorias_productos", back_populates="productos")
    sucursales = relationship(
        "Sucursales", secondary=sucursal_producto, back_populates="productos", 
    )
    producto_proveedor_asociaciones = relationship("ProductoProveedor", back_populates="producto", cascade="all, delete-orphan", collection_class=set)
    
    proveedores = relationship(
        "Proveedores",
        secondary="producto_proveedor",
        viewonly=True
    )
    
    detalles_compras = relationship("Detalles_compras", back_populates="producto")
    
    detalles_ventas = relationship("Detalles_ventas", back_populates="producto")
    
    movimientos_inventario = relationship("Movimientos_Inventario", back_populates="producto", cascade="all, delete-orphan")

class Movimientos_Inventario(Base):
    __tablename__ = "Movimientos_inventario"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    producto_id:Mapped[int] = mapped_column(Integer, ForeignKey("Productos.id", ondelete="CASCADE"), nullable=True)
    cantidad_cambio:Mapped[float] = mapped_column(Float)  #  Indica la cantidad de productos que entran o salen del inventario.
    tipo_movimiento:Mapped[str] = mapped_column(String(20))  # Tipo de movimiento: "entrada" o "salida"
    fecha_movimiento:Mapped[datetime] = mapped_column(Date)
    notas:Mapped[str] = mapped_column(Text)
    usuario_id:Mapped[int] = mapped_column(Integer, ForeignKey("Usuarios.id", ondelete='SET NULL'), nullable=True)
    
    # Relación con Productos
    producto = relationship("Productos", back_populates="movimientos_inventario")
    
    usuario = relationship("Usuarios", back_populates="movimientos_inventario")

class Categorias_productos(Base):
    __tablename__ = "Categorias_productos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    descripcion:Mapped[str] = mapped_column(Text)
    # Relación con Productos (una categoría tiene muchos productos)
    productos = relationship("Productos", back_populates="categoria")

class Proveedores(Base):
    __tablename__ = "Proveedores"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(150))
    pais:Mapped[str] = mapped_column(String(30))
    estado:Mapped[str] = mapped_column(String(30))
    ciudad:Mapped[str] = mapped_column(String(30))
    codigo_postal:Mapped[str] = mapped_column(String(5))
    calles:Mapped[str] = mapped_column(String(60))
    avenidas:Mapped[str] = mapped_column(String(60))
    colonia:Mapped[str] = mapped_column(String(50))
    direccion_adicional:Mapped[str] = mapped_column(Text)
    rfc:Mapped[str] = mapped_column(String(13))
    pagina_web:Mapped[str] = mapped_column(Text)
    correo:Mapped[str] = mapped_column(String(100))
    telefono:Mapped[str] = mapped_column(String(10))
    clave_moneda:Mapped[str] = mapped_column(String(5))
    tipo_moneda:Mapped[str] = mapped_column(String(50))
    representante_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Representantes_proveedores.id"), nullable=True)
    categoria_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Categorias_proveedores.id"), nullable=True)
    categoria = relationship("Categorias_proveedores", back_populates="proveedores")
    representante = relationship("Representantes_proveedores", back_populates="proveedores")
    producto_proveedor_asociaciones = relationship("ProductoProveedor", back_populates="proveedor", cascade="all, delete-orphan", collection_class=set)
    productos = relationship(
        "Productos",
        secondary="producto_proveedor",
        viewonly=True
    )
    compras = relationship("Compras", back_populates="proveedor")
    
class ProductoProveedor(Base):
    __tablename__ = "producto_proveedor"
    producto_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Productos.id", ondelete='SET NULL'), primary_key=True)
    proveedor_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Proveedores.id", ondelete='SET NULL'), primary_key=True)
    precio_venta:Mapped[float] = mapped_column(Float)
    producto = relationship("Productos", back_populates="producto_proveedor_asociaciones")
    proveedor = relationship("Proveedores", back_populates="producto_proveedor_asociaciones")

class Representantes_proveedores(Base):
    __tablename__ = "Representantes_proveedores"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    apellido_paterno:Mapped[str] = mapped_column(String(60))
    apellido_materno:Mapped[str] = mapped_column(String(60))
    telefono:Mapped[str] = mapped_column(String(10))
    correo:Mapped[str] = mapped_column(String(100))
    puesto:Mapped[str] = mapped_column(String(100))
    proveedores = relationship("Proveedores", back_populates="representante")  # Relación inversa

class Categorias_proveedores(Base):
    __tablename__ = "Categorias_proveedores"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(150))
    descripcion:Mapped[str] = mapped_column(Text)
    proveedores = relationship(
        "Proveedores", back_populates="categoria", 
    )

class Clientes(Base):
    __tablename__ = "Clientes"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(255))
    correo:Mapped[str] = mapped_column(String(255))
    rfc:Mapped[str] = mapped_column(String(20))
    telefono:Mapped[str] = mapped_column(String(15))
    pais:Mapped[str] = mapped_column(String(100))
    estado:Mapped[str] = mapped_column(String(100))
    ciudad:Mapped[str] = mapped_column(String(255))
    avenidas:Mapped[str] = mapped_column(String(255))
    calles:Mapped[str] = mapped_column(String(255))
    codigo_postal:Mapped[str] = mapped_column(String(20))
    direccion_adicional:Mapped[str] = mapped_column(Text)
    entidad_legalizada:Mapped[bool] = mapped_column(Boolean)
    categoria_cliente_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Categorias_de_clientes.id"))
    credito:Mapped[bool] = mapped_column(Boolean)
    estado_credito:Mapped[str] = mapped_column(String(25))
    limite_credito:Mapped[float] = mapped_column(Float)
    porcentaje_interes:Mapped[float] = mapped_column(Float)
    fecha_ultimo_reporte:Mapped[datetime] = mapped_column(DateTime)
    credito_disponible:Mapped[float] = mapped_column(Float)
    credito_utilizado:Mapped[float] = mapped_column(Float)
    tipo_cliente:Mapped[str] = mapped_column(String(50))
    aplica_descuento:Mapped[bool] = mapped_column(Boolean)
    porcentaje_descuento:Mapped[float] = mapped_column(Float)
    comentarios:Mapped[str] = mapped_column(Text)

    ventas = relationship("Ventas", back_populates="cliente")
    areas_de_negocios_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Areas_negocios.id"), nullable=False)
    areas_de_negocios = relationship("Areas_negocios", back_populates="clientes")
    categoria = relationship("Categorias_de_clientes", back_populates="clientes")

    __mapper_args__ = {"polymorphic_on": tipo_cliente, "polymorphic_identity": "clientes"}

class Categorias_de_clientes(Base):
    __tablename__ = "Categorias_de_clientes"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    descripcion:Mapped[str] = mapped_column(String(255))
    clientes = relationship("Clientes", back_populates="categoria")

class Compras(Base):
    __tablename__ = "Compras"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    proveedor_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Proveedores.id"), nullable=False)
    empleado_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Empleados.id"), nullable=False)
    fecha_compra:Mapped[datetime] = mapped_column(DateTime)
    fecha_creacion:Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    total_compra:Mapped[float] = mapped_column(Float)
    estado:Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    metodos_pago_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Metodos_pagos.id"), nullable=False)
    detalles = relationship("Detalles_compras", 
    back_populates="compra",
    cascade="all, delete-orphan",
    passive_deletes=True
    )
    proveedor = relationship("Proveedores", back_populates="compras")
    metodos_de_pago = relationship("Metodos_pagos", back_populates="compras")
    empleado = relationship("Empleados", back_populates="compras")

class Detalles_compras(Base):
    __tablename__ = "Detalles_compras"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    compra_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Compras.id", ondelete='SET NULL'), nullable=False)
    producto_id:Mapped[str] = mapped_column(Text, ForeignKey("Productos.codigo_upc"), nullable=False)
    cantidad:Mapped[float] = mapped_column(Float)
    precio_unitario:Mapped[float] = mapped_column(Float)
    subtotal:Mapped[float] = mapped_column(Float)
    compra = relationship("Compras", back_populates="detalles")
    producto = relationship("Productos", back_populates="detalles_compras")

class Turnos(Base):
    __tablename__ = "Turnos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    empleado_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Empleados.id"), nullable=False)
    fecha_turno:Mapped[datetime] = mapped_column(DateTime)
    hora_inicio:Mapped[datetime] = mapped_column(DateTime)
    hora_fin:Mapped[datetime] = mapped_column(DateTime)
    empleado = relationship("Empleados", back_populates="turnos")
    transacciones = relationship("Transacciones", back_populates="turno")

class Transacciones(Base):
    __tablename__ = "Transacciones"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    tipo:Mapped[str] = mapped_column(String(100))
    monto:Mapped[float] = mapped_column(Float)
    fecha:Mapped[datetime] = mapped_column(DateTime)
    turno_id:Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Turnos.id"), nullable=False
    )  # Relación con Turnos

    # Relación con Turnos
    turno = relationship("Turnos", back_populates="transacciones")

class Areas_negocios(Base):
    __tablename__ = "Areas_negocios"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    descripcion:Mapped[str] = mapped_column(Text)
    clientes = relationship("Clientes", back_populates="areas_de_negocios")

class Clientes_fisicos(Clientes):
    __tablename__ = "Clientes_fisicos"
    id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Clientes.id", ondelete='CASCADE'), primary_key=True)
    apellido_paterno:Mapped[str] = mapped_column(String(255))
    apellido_materno:Mapped[str] = mapped_column(String(255))
    curp:Mapped[str] = mapped_column(String(18))
    fecha_nacimiento:Mapped[datetime] = mapped_column(Date)
    num_identificacion:Mapped[str] = mapped_column(String(20))
    ocupacion:Mapped[str] = mapped_column(String(150))
    ingresos:Mapped[float] = mapped_column(Float)
    estado_civil:Mapped[str] = mapped_column(String(15))
    foto:Mapped[str] = mapped_column(Text)

    __mapper_args__ = {
        "polymorphic_identity": "FISICO",
    }

class Clientes_morales(Clientes):
    __tablename__ = "Clientes_morales"
    id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Clientes.id", ondelete="CASCADE"), primary_key=True)
    razon_social:Mapped[str] = mapped_column(String(255))
    fecha_constitucion:Mapped[datetime] = mapped_column(Date)
    web:Mapped[str] = mapped_column(String(255))
    sector:Mapped[str] = mapped_column(String(255))
    NIF:Mapped[str] = mapped_column(String(20))
    representante_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Representantes_clientes_morales.id"))
    representante = relationship(
        "Representantes_clientes_morales", back_populates="clientes_morales"
    )

    __mapper_args__ = {
        "polymorphic_identity": "MORAL",
    }

class Metodos_pagos(Base):
    __tablename__ = "Metodos_pagos"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    compras = relationship("Compras", back_populates="metodos_de_pago")
    ventas = relationship("Ventas", back_populates="metodos_de_pago")

class Representantes_clientes_morales(Base):
    __tablename__ = "Representantes_clientes_morales"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    nombre:Mapped[str] = mapped_column(String(100))
    telefono:Mapped[str] = mapped_column(String(20))
    correo:Mapped[str] = mapped_column(String(100))
    puesto:Mapped[str] = mapped_column(String(100))
    clientes_morales = relationship("Clientes_morales", back_populates="representante")
    
class Detalles_ventas(Base):
    __tablename__ = "Detalles_ventas"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    venta_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Ventas.id", ondelete="RESTRICT"), nullable=False)  # Relación con la venta
    producto_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Productos.id", ondelete="RESTRICT"), nullable=False)  # Relación con el producto vendido
    cantidad:Mapped[float] = mapped_column(Float, nullable=False)  # Cantidad del producto vendido
    precio_unitario:Mapped[float] = mapped_column(Float, nullable=False)  # Precio unitario del producto en el momento de la venta
    subtotal:Mapped[float] = mapped_column(Float, nullable=False)  # Subtotal: cantidad * precio_unitario
    descuento:Mapped[float] = mapped_column(Float, default=0.0)  # Descuento aplicado
    iva:Mapped[float] = mapped_column(Float, nullable=False)  # IVA del detalle
    total_con_iva:Mapped[float] = mapped_column(Float, nullable=False)  # Precio con IVA
    nombre_producto:Mapped[str] = mapped_column(String(200), nullable=False)
    clave_producto:Mapped[str] = mapped_column(String(200), nullable=False)
    activo:Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relación con la venta
    venta = relationship("Ventas", back_populates="detalles_ventas")

    # Relación con el producto
    producto = relationship("Productos", back_populates="detalles_ventas")

class Ventas(Base):
    __tablename__ = "Ventas"
    id:Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True
        )
    folio:Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    fecha:Mapped[datetime] = mapped_column(DateTime)
    fecha_creacion:Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    fecha_actualizacion:Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now())
    subtotal:Mapped[float] = mapped_column(Float, nullable=False)
    iva:Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total:Mapped[float] = mapped_column(Float)
    estado:Mapped[str] = mapped_column(String(100), nullable=False, default='PENDIENTE')
    comentarios:Mapped[str] = mapped_column(Text)
    activo:Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    motivo_cancelacion:Mapped[str] = mapped_column(String(200), nullable=True)
    cancelada_por_usuario_id:Mapped[int] = mapped_column(BigInteger, ForeignKey("Usuarios.id"), nullable=True)
    fecha_cancelacion:Mapped[datetime] = mapped_column(DateTime, nullable=True)
    forma_pago:Mapped[str] = mapped_column(String(50), nullable=True)

    cliente_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Clientes.id", ondelete='RESTRICT'),
        nullable=False
    )
    empleado_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Empleados.id", ondelete='RESTRICT'),
        nullable=False
    )
    metodos_pagos_id:Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("Metodos_pagos.id", ondelete='RESTRICT'),
        nullable=False
    )

    cliente = relationship("Clientes", back_populates="ventas")
    empleado = relationship("Empleados", back_populates="ventas")
    metodos_de_pago = relationship("Metodos_pagos", back_populates="ventas")
    
    detalles_ventas = relationship(
        "Detalles_ventas", 
        back_populates="venta",
        cascade="save-update, merge",
        passive_deletes=False
    )
    cancelada_por_usuario = relationship(
        "Usuarios", 
        foreign_keys=[cancelada_por_usuario_id]
    )
    
# Índices para mejorar el rendimiento en búsquedas
Index("idx_usuario", Usuarios.usuario)
Index("idx_curp", Empleados.curp)
Index("idx_rfc", Empleados.rfc)
Index("idx_idProducto", Productos.id)
Index("idx_nombreProducto", Productos.nombre_producto)
Index("idx_CODIGOupcpRODUCTO", Productos.codigo_upc)
Index("idx_categoriaProducto", Categorias_productos.id)
Index("idx_unidadMedidaProducto", Unidad_medida_productos.id)
Index("idx_presentacionProducto", Presentacion_productos.id)
Index("idx_proveedorId", Proveedores.id)
