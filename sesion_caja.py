from datetime import datetime
from sqlalchemy import select, update
from app.DataBase.conexionBD import Conexion_base_datos
from app.Model.BaseDatosModel import SesionCaja, Ventas

class GestorSesionCaja:
    @staticmethod
    def obtener_sesion_activa(session=None) -> tuple[bool, str, dict | None]:
        """
        Consults if there is a box session currently OPEN ('ABIERTA').
        Can be called with an active SQLAlchemy session or will open and close one.
        Returns:
            tuple[bool, str, dict] -> (exito, mensaje, sesion_dict_o_None)
        """
        def _consultar(s):
            # Check for any active open session
            stmt = select(SesionCaja).where(SesionCaja.estado == "ABIERTA").order_by(SesionCaja.id.desc())
            result = s.execute(stmt).scalars().first()
            if result:
                return True, "Sesión activa encontrada.", {
                    "id": result.id,
                    "usuario_id": result.usuario_id,
                    "fecha_apertura": result.fecha_apertura,
                    "monto_inicial": result.monto_inicial,
                    "ventas_efectivo": result.ventas_efectivo,
                    "ventas_tarjeta": result.ventas_tarjeta,
                    "ventas_transferencia": result.ventas_transferencia,
                    "entradas_efectivo": result.entradas_efectivo,
                    "retiros_efectivo": result.retiros_efectivo,
                    "conteo_usuario": result.conteo_usuario,
                    "efectivo_esperado": result.efectivo_esperado,
                    "diferencia": result.diferencia,
                    "fecha_cierre": result.fecha_cierre,
                    "estado": result.estado
                }
            return False, "No hay ninguna sesión de caja activa abierta.", None

        if session is not None:
            return _consultar(session)
        else:
            try:
                with Conexion_base_datos() as db:
                    s = db.abrir_sesion()
                    return _consultar(s)
            except Exception as e:
                return False, f"Error al obtener sesión de caja abierta: {str(e)}", None

    @staticmethod
    def abrir_sesion_caja(usuario_id: int, monto_inicial: float, session=None) -> tuple[bool, str, dict | None]:
        """
        Registers a new box session with the state 'ABIERTA' and its initial fund.
        """
        def _abrir(s):
            # Verify if there is already an open session
            stmt = select(SesionCaja).where(SesionCaja.estado == "ABIERTA")
            existing = s.execute(stmt).scalars().first()
            if existing:
                return False, f"Ya existe una sesión de caja abierta (ID: {existing.id}) para este o algún otro usuario.", None

            nueva_sesion = SesionCaja(
                usuario_id=usuario_id,
                fecha_apertura=datetime.now(),
                monto_inicial=monto_inicial,
                ventas_efectivo=0.0,
                ventas_tarjeta=0.0,
                ventas_transferencia=0.0,
                entradas_efectivo=0.0,
                retiros_efectivo=0.0,
                efectivo_esperado=monto_inicial,
                diferencia=0.0,
                estado="ABIERTA"
            )
            s.add(nueva_sesion)
            s.commit()
            s.refresh(nueva_sesion)
            return True, "Caja abierta con éxito.", {
                "id": nueva_sesion.id,
                "usuario_id": nueva_sesion.usuario_id,
                "fecha_apertura": nueva_sesion.fecha_apertura,
                "monto_inicial": nueva_sesion.monto_inicial,
                "ventas_efectivo": nueva_sesion.ventas_efectivo,
                "ventas_tarjeta": nueva_sesion.ventas_tarjeta,
                "ventas_transferencia": nueva_sesion.ventas_transferencia,
                "entradas_efectivo": nueva_sesion.entradas_efectivo,
                "retiros_efectivo": nueva_sesion.retiros_efectivo,
                "conteo_usuario": nueva_sesion.conteo_usuario,
                "efectivo_esperado": nueva_sesion.efectivo_esperado,
                "diferencia": nueva_sesion.diferencia,
                "fecha_cierre": nueva_sesion.fecha_cierre,
                "estado": nueva_sesion.estado
            }

        if session is not None:
            return _abrir(session)
        else:
            try:
                with Conexion_base_datos() as db:
                    s = db.abrir_sesion()
                    res = _abrir(s)
                    return res
            except Exception as e:
                return False, f"Error al abrir la sesión de caja: {str(e)}", None

    @staticmethod
    def acumular_venta(sesion_id: int, monto: float, forma_pago: str, session=None) -> tuple[bool, str]:
        """
        Accumulates money from a sale into the open session of the box, filtered by payment method.
        """
        def _acumular(s):
            sesion = s.get(SesionCaja, sesion_id)
            if not sesion:
                return False, f"No se encontró la sesión de caja {sesion_id}."
            if sesion.estado != "ABIERTA":
                return False, f"La sesión de caja {sesion_id} no está abierta."

            forma_pago_upper = forma_pago.upper()
            if "EFECTIVO" in forma_pago_upper or "CONTADO" in forma_pago_upper:
                sesion.ventas_efectivo += monto
            elif "TARJETA" in forma_pago_upper:
                sesion.ventas_tarjeta += monto
            elif "TRANSFERENCIA" in forma_pago_upper or "CHEQUE" in forma_pago_upper:
                sesion.ventas_transferencia += monto
            else:
                # Fallback to efectivo if indeterminate
                sesion.ventas_efectivo += monto

            # Update expected cash
            sesion.efectivo_esperado = sesion.monto_inicial + sesion.ventas_efectivo + sesion.entradas_efectivo - sesion.retiros_efectivo
            s.commit()
            return True, "Acumulación exitosa."

        if session is not None:
            return _acumular(session)
        else:
            try:
                with Conexion_base_datos() as db:
                    s = db.abrir_sesion()
                    res = _acumular(s)
                    return res
            except Exception as e:
                return False, f"Error al acumular venta a la sesión de caja: {str(e)}"

    @staticmethod
    def registrar_entrada_retiro(sesion_id: int, monto: float, es_entrada: bool, session=None) -> tuple[bool, str]:
        """
        Register a custom cash entry or withdrawal during the shift.
        """
        def _registrar(s):
            sesion = s.get(SesionCaja, sesion_id)
            if not sesion or sesion.estado != "ABIERTA":
                return False, "La sesión de caja no coincide o no está abierta."

            if es_entrada:
                sesion.entradas_efectivo += monto
            else:
                sesion.retiros_efectivo += monto

            sesion.efectivo_esperado = sesion.monto_inicial + sesion.ventas_efectivo + sesion.entradas_efectivo - sesion.retiros_efectivo
            s.commit()
            return True, "Registro exitoso."

        if session is not None:
            return _registrar(session)
        else:
            try:
                with Conexion_base_datos() as db:
                    s = db.abrir_sesion()
                    res = _registrar(s)
                    return res
            except Exception as e:
                return False, f"Error al registrar entrada/retiro en caja: {str(e)}"

    @staticmethod
    def cerrar_sesion_caja(sesion_id: int, conteo_usuario: float, session=None) -> tuple[bool, str, dict | None]:
        """
        Closes the active cash session of the box calculating differences and setting state 'CERRADA'.
        """
        def _cerrar(s):
            sesion = s.get(SesionCaja, sesion_id)
            if not sesion:
                return False, f"No se encontró la sesión de caja con ID {sesion_id}.", None
            if sesion.estado != "ABIERTA":
                return False, "La sesión ya se encuentra cerrada.", None

            # Calculate metrics
            efectivo_esperado = sesion.monto_inicial + sesion.ventas_efectivo + sesion.entradas_efectivo - sesion.retiros_efectivo
            diferencia = conteo_usuario - efectivo_esperado

            sesion.conteo_usuario = conteo_usuario
            sesion.efectivo_esperado = efectivo_esperado
            sesion.diferencia = diferencia
            sesion.fecha_cierre = datetime.now()
            sesion.estado = "CERRADA"

            s.commit()
            return True, "Caja cerrada con éxito.", {
                "id": sesion.id,
                "usuario_id": sesion.usuario_id,
                "fecha_apertura": sesion.fecha_apertura,
                "monto_inicial": sesion.monto_inicial,
                "ventas_efectivo": sesion.ventas_efectivo,
                "ventas_tarjeta": sesion.ventas_tarjeta,
                "ventas_transferencia": sesion.ventas_transferencia,
                "entradas_efectivo": sesion.entradas_efectivo,
                "retiros_efectivo": sesion.retiros_efectivo,
                "conteo_usuario": sesion.conteo_usuario,
                "efectivo_esperado": sesion.efectivo_esperado,
                "diferencia": sesion.diferencia,
                "fecha_cierre": sesion.fecha_cierre,
                "estado": sesion.estado
            }

        if session is not None:
            return _cerrar(session)
        else:
            try:
                with Conexion_base_datos() as db:
                    s = db.abrir_sesion()
                    res = _cerrar(s)
                    return res
            except Exception as e:
                return False, f"Error al cerrar la sesión de caja: {str(e)}", None
