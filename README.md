# TuleVenta

Sistema de gestión y ventas **TuleVenta**.

TuleVenta es una aplicación de escritorio orientada a la gestión de ventas, información comercial, estadísticas, reportes y otras funciones administrativas.

---

## 📋 Características

* Gestión de ventas.
* Consulta y administración de información.
* Estadísticas.
* Gráficas.
* Generación de reportes.
* Exportación de información.
* Interfaz de escritorio.
* Ejecución como aplicación independiente mediante `.exe`.
* Sistema de actualización desde GitHub.
* Verificación de nuevas versiones.
* Actualización automática de la aplicación.

> Las funcionalidades disponibles pueden variar según la versión instalada.

---

## 🛠️ Tecnologías

El proyecto utiliza principalmente:

* Python
* PyInstaller
* Plotly
* Pandas, cuando alguna funcionalidad lo requiere
* Bibliotecas adicionales utilizadas por los módulos de reportes, gráficas y exportación.

La aplicación puede distribuirse como un ejecutable de Windows sin necesidad de instalar Python en el equipo del usuario.

---

# 📁 Estructura del proyecto

Una estructura típica del proyecto es:

```text
TuleVenta/
│
├── src/                  # Código fuente de la aplicación
│
├── tools/                # Herramientas auxiliares
│
├── dist/                 # Aplicación compilada
│   └── TuleVenta/
│       └── TuleVenta.exe
│
├── build/                # Archivos temporales de PyInstaller
│
├── TuleVenta.spec        # Configuración de PyInstaller
├── build_app.bat         # Script de compilación
│
├── requirements.txt      # Dependencias de Python
│
└── README.md
```

La estructura exacta puede variar dependiendo de la versión del proyecto.

---

# 🚀 Ejecución en desarrollo

## 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd TuleVenta
```

## 2. Crear entorno virtual

En Windows:

```bash
python -m venv .venv
```

Activar:

```bash
.venv\Scripts\activate
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4. Ejecutar la aplicación

Utiliza el archivo principal de la aplicación.

Por ejemplo:

```bash
python main.py
```

> El archivo de entrada puede variar dependiendo de la estructura actual del proyecto.

---

# 📦 Compilación

TuleVenta utiliza **PyInstaller** para generar la aplicación distribuible.

La compilación puede realizarse mediante:

```text
build_app.bat
```

Ejecuta:

```bat
build_app.bat
```

El resultado normalmente se genera dentro de:

```text
dist\
```

Por ejemplo:

```text
dist\
└── TuleVenta\
    └── TuleVenta.exe
```

---

# ▶️ Ejecutar la versión compilada

Después de compilar:

```bat
dist\TuleVenta\TuleVenta.exe
```

También puede ejecutarse haciendo doble clic sobre:

```text
dist\TuleVenta\TuleVenta.exe
```

---

# 🔧 Configuración de PyInstaller

La configuración de compilación se encuentra en:

```text
TuleVenta.spec
```

Este archivo controla aspectos como:

* módulos incluidos;
* archivos adicionales;
* recursos;
* dependencias;
* imports ocultos;
* archivos binarios;
* nombre del ejecutable;
* configuración del paquete.

Antes de eliminar una dependencia del `.spec`, debe verificarse que ninguna funcionalidad de TuleVenta la utilice.

---

# 📊 Gráficas y estadísticas

TuleVenta puede utilizar componentes destinados a la visualización de información.

Entre ellos pueden encontrarse:

* Plotly
* Pandas
* otras bibliotecas de análisis o visualización.

Estas dependencias deben conservarse si son necesarias para:

* dashboards;
* gráficas;
* estadísticas;
* análisis de ventas;
* reportes;
* tablas dinámicas;
* procesamiento de información.

Antes de excluir una dependencia del ejecutable se debe comprobar qué módulos la utilizan.

---

# 📄 Reportes

La aplicación incluye funcionalidades relacionadas con reportes y generación/exportación de información.

Al compilar una nueva versión se debe comprobar que continúen funcionando:

* generación de reportes;
* visualización de información;
* exportaciones;
* archivos generados;
* gráficas incluidas en reportes.

---

# 🔄 Sistema de actualización

TuleVenta está diseñado para poder comprobar si existe una versión más reciente disponible en el repositorio de GitHub.

El objetivo del sistema de actualización es:

```text
TuleVenta
    │
    ▼
Comprobar versión actual
    │
    ▼
Consultar GitHub
    │
    ▼
¿Existe una versión nueva?
    │
 ┌──┴───┐
 │      │
 NO     SÍ
 │      │
 ▼      ▼
Iniciar Descargar
normal  actualización
            │
            ▼
       Cerrar aplicación
            │
            ▼
       Actualizar archivos
            │
            ▼
       Iniciar nueva versión
```

La actualización debe realizarse antes de que el usuario continúe utilizando normalmente la aplicación.

## Versionado

Las versiones deben utilizar un formato compatible con versionado semántico, por ejemplo:

```text
1.0.0
1.0.1
1.1.0
2.0.0
```

Cuando se publique una nueva versión en GitHub, se recomienda crear una **Release** con su correspondiente versión y archivo de distribución.

---

# 🏷️ Publicación de una nueva versión

El flujo recomendado es:

### 1. Actualizar la versión

Modificar la versión de TuleVenta en la fuente de verdad definida por el proyecto.

Ejemplo:

```text
1.0.0
```

a:

```text
1.0.1
```

### 2. Probar la aplicación

Comprobar:

* inicio;
* ventas;
* estadísticas;
* gráficas;
* reportes;
* exportaciones;
* configuración;
* cierre de la aplicación.

### 3. Generar el ejecutable

Ejecutar:

```bat
build_app.bat
```

### 4. Probar el ejecutable

Ejecutar:

```bat
dist\TuleVenta\TuleVenta.exe
```

### 5. Crear una GitHub Release

Crear una nueva Release utilizando la versión correspondiente.

Por ejemplo:

```text
v1.0.1
```

Agregar el archivo de distribución generado por la compilación.

### 6. Verificar la actualización

Instalar o ejecutar una versión anterior y comprobar que:

```text
versión instalada < versión publicada
```

produzca una actualización correcta.

---

# 🧪 Pruebas antes de publicar

Antes de distribuir una nueva versión se recomienda comprobar:

## Aplicación

* [ ] La aplicación inicia.
* [ ] La aplicación inicia con PostgreSQL detenido y muestra el splash de preparación.
* [ ] La aplicación abre a la primera sin necesidad de finalizar el proceso.
* [ ] La aplicación cierra correctamente y detiene PostgreSQL.
* [ ] Cerrar sesión vuelve a mostrar el login.
* [ ] Cerrar el login termina la aplicación y PostgreSQL.
* [ ] Las ventanas funcionan.
* [ ] La configuración funciona.

## Ventas

* [ ] Crear venta.
* [ ] Consultar venta.
* [ ] Modificar información cuando corresponda.
* [ ] Comprobar cálculos.

## Estadísticas

* [ ] Las estadísticas cargan.
* [ ] Los datos son correctos.
* [ ] Las gráficas funcionan.

## Plotly / gráficas

* [ ] Las gráficas se muestran correctamente.
* [ ] No aparecen errores de JavaScript.
* [ ] Los datos utilizados por las gráficas son correctos.

## Reportes

* [ ] Generar reporte.
* [ ] Abrir reporte.
* [ ] Exportar reporte.
* [ ] Comprobar que los archivos generados son válidos.

## Actualización

* [ ] Detectar nueva versión.
* [ ] Descargar actualización.
* [ ] Cerrar aplicación anterior.
* [ ] Instalar nueva versión.
* [ ] Abrir nueva versión.
* [ ] Confirmar nueva versión.
* [ ] Comprobar que los datos existentes permanecen intactos.

---

# 🐛 Solución de problemas

## El `.exe` no inicia

Ejecutar el programa desde una consola para poder visualizar posibles errores:

```bat
dist\TuleVenta\TuleVenta.exe
```

Revisar también:

* archivos incluidos en `dist`;
* dependencias;
* DLL;
* configuración de PyInstaller;
* archivos de configuración.

## El primer arranque se queda sin ventana

La aplicación inicia PostgreSQL portable antes de abrir la pantalla de acceso. Desde la versión con el ajuste de arranque del 2026-11-18 se muestra un splash de progreso mientras se prepara la base de datos.

Si el splash no avanza:

1. Revisar `%APPDATA%\TuleVenta\postgresql.log`.
2. Comprobar que `%APPDATA%\TuleVenta\PostgreSQL18\bin\pg_ctl.exe` y `pg_isready.exe` existan.
3. Ejecutar:
   ```bat
   "%APPDATA%\TuleVenta\PostgreSQL18\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
   ```
   El puerto debe coincidir con `%PROGRAMDATA%\TuleVenta\configuracion_bd.json`.
4. No es necesario finalizar `TuleVenta.exe` ni abrir la aplicación por segunda vez. El arranque espera hasta 120 segundos a que PostgreSQL termine una recuperación de WAL.

El bloqueo de primer arranque corregido el 2026-11-18 se producía porque `pg_ctl start` se ejecutaba capturando `stdout`/`stderr`; `postgres.exe` heredaba esos pipes y Python quedaba esperando indefinidamente aunque el servidor ya estuviera activo.

## Cerrar sesión y cerrar la aplicación

La barra lateral incluye **Cerrar sesión**. Al confirmarlo:

1. Se cancelan y limpian los workers de base de datos e importación.
2. Se cierra la ventana principal.
3. Se abre de nuevo la pantalla de inicio de sesión.

La sesión no detiene PostgreSQL, porque el siguiente usuario puede iniciar sesión inmediatamente.

Al cerrar la aplicación desde la ventana principal o al cerrar la pantalla de inicio de sesión:

1. Se limpian los workers activos.
2. Se ejecuta `pg_ctl stop -m fast -w` sobre `%APPDATA%\TuleVenta\data`.
3. Se espera a que PostgreSQL termine y se cierran los procesos de la aplicación.

Si hay un ticket en curso, la aplicación pide confirmación antes de descartarlo. Si hay una actualización o importación activa, el cierre se bloquea hasta terminar o cancelar la operación.

---

## Una gráfica no funciona

Comprobar:

1. Que Plotly esté incluido.
2. Que las dependencias necesarias estén incluidas.
3. Que los archivos de recursos estén presentes.
4. Que la función funcione en desarrollo.
5. Que el `.spec` no haya excluido accidentalmente alguna dependencia.

---

## Pandas aparece en el ejecutable

No eliminar `pandas` únicamente porque parezca innecesario.

Primero comprobar:

```text
¿Quién importa pandas?
        ↓
¿Esa función se utiliza?
        ↓
¿Otra biblioteca depende de pandas?
        ↓
¿Puede excluirse sin romper gráficas/reportes?
```

La eliminación debe realizarse solamente después de comprobar las dependencias reales del proyecto.

---

## La actualización no funciona

Comprobar:

* conexión a Internet;
* GitHub Release;
* versión publicada;
* nombre del archivo descargable;
* permisos de escritura;
* proceso del actualizador;
* archivos descargados;
* logs del actualizador.

El ejecutable principal no debe intentar reemplazarse a sí mismo mientras está ejecutándose.

---

# 🔐 Seguridad

Las actualizaciones deben descargarse únicamente desde fuentes controladas.

Cuando sea posible, debe verificarse la integridad del archivo descargado mediante un hash, por ejemplo:

```text
SHA-256
```

No se recomienda ejecutar archivos descargados desde ubicaciones desconocidas.

---

# 💾 Datos del usuario

Las actualizaciones de TuleVenta no deberían eliminar ni sobrescribir los datos de usuario.

Antes de publicar cambios que modifiquen:

* bases de datos;
* archivos de configuración;
* rutas de almacenamiento;
* formatos de datos;

debe comprobarse la compatibilidad con instalaciones anteriores.

---

# 🏗️ Desarrollo

Para trabajar en el proyecto:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Después ejecutar la aplicación utilizando su punto de entrada correspondiente.

---

# 📦 Distribución

La distribución de producción debe realizarse utilizando los archivos generados por PyInstaller.

Ejemplo:

```text
dist\
└── TuleVenta\
    ├── TuleVenta.exe
    ├── archivos necesarios
    ├── DLL necesarias
    └── recursos
```

No se recomienda distribuir solamente el `.exe` si la compilación utiliza el modo `onedir`.

---

# 📝 Registro de versiones

| Versión | Cambios                |
| ------- | ---------------------- |
| 1.0.0   | Versión inicial        |
| 1.0.1   | Correcciones y mejoras |
| 1.1.0   | Nuevas funcionalidades |

Actualizar esta sección al publicar nuevas versiones.

---

# 📌 Notas

Antes de realizar cambios importantes en el sistema:

1. Realizar una copia de seguridad.
2. Probar en desarrollo.
3. Compilar una versión de prueba.
4. Ejecutar todas las pruebas principales.
5. Probar el mecanismo de actualización.
6. Publicar solamente después de verificar la versión compilada.

---

# 👨‍💻 Mantenimiento

Para modificar TuleVenta se recomienda seguir este ciclo:

```text
Modificar código
      ↓
Probar en desarrollo
      ↓
Ejecutar pruebas
      ↓
Actualizar versión
      ↓
Compilar
      ↓
Probar dist/TuleVenta/TuleVenta.exe
      ↓
Crear GitHub Release
      ↓
Probar actualización
      ↓
Publicar
```

---

## Licencia

Especificar aquí la licencia utilizada por el proyecto.

Si el proyecto es propietario:

```text
© TuleVenta. Todos los derechos reservados.
```

No redistribuir ni modificar el software sin autorización del propietario.
