import argparse
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.DataBase.configuracionConexion import ConfiguracionConexionBD


def _crear_parser():
    parser = argparse.ArgumentParser(
        description="Guarda y prueba la configuracion de PostgreSQL para TuleVenta."
    )
    parser.add_argument("--url", dest="database_url", help="URL completa de SQLAlchemy para PostgreSQL")
    parser.add_argument("--driver", default="postgresql+psycopg2", help="Driver SQLAlchemy a utilizar")
    parser.add_argument("--host", default="127.0.0.1", help="Host del servidor PostgreSQL")
    parser.add_argument("--port", type=int, default=5432, help="Puerto del servidor PostgreSQL")
    parser.add_argument("--database", default="TuleVenta", help="Nombre de la base de datos")
    parser.add_argument("--user", dest="username", default="postgres", help="Usuario de PostgreSQL")
    parser.add_argument("--password", default="", help="Contrasena de PostgreSQL")
    parser.add_argument("--test", action="store_true", help="Probar la conexion inmediatamente despues de guardar")
    return parser


def _construir_configuracion(args):
    return {
        "database_url": args.database_url or "",
        "driver": args.driver,
        "host": args.host,
        "port": args.port,
        "database": args.database,
        "username": args.username,
        "password": args.password,
        "options": {},
    }


def _probar_conexion(url_conexion):
    engine = create_engine(url_conexion, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def main():
    parser = _crear_parser()
    args = parser.parse_args()

    configuracion = _construir_configuracion(args)
    configuracion_guardada = ConfiguracionConexionBD.guardar_configuracion(configuracion)
    ruta = ConfiguracionConexionBD.ruta_configuracion()
    print(f"Configuracion guardada en: {ruta}")

    if args.test:
        try:
            _probar_conexion(ConfiguracionConexionBD.construir_url(configuracion_guardada))
        except SQLAlchemyError as error:
            print(f"No se pudo conectar a PostgreSQL: {error}")
            return 1
        print("Conexion a PostgreSQL validada correctamente.")

    return 0


if __name__ == "__main__":
    sys.exit(main())