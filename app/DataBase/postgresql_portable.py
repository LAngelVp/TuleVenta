from .postgres_manager import (
    PostgresConnectionSettings as PostgreSqlConnectionSettings,
    PostgresServiceManager,
    PostgresStartupError as PostgreSqlPortableStartupError,
    asegurar_servicio_postgres,
)


class PostgreSqlPortableBootstrap:
    """Wrapper de compatibilidad para el gestor centralizado de PostgreSQL."""

    def __init__(self, logger=None):
        self._manager = PostgresServiceManager(logger=logger)

    def asegurar_servidor_disponible(self):
        return self._manager.asegurar_servicio_postgres()