from datetime import datetime
import math
import unicodedata
from sqlalchemy import select, update
from app.DataBase.conexionBD import Conexion_base_datos
from app.Model.BaseDatosModel import SesionCaja, Ventas


def clasificar_forma_pago(nombre):
    etiqueta = " ".join("".join(caracter for caracter in unicodedata.normalize("NFKD", nombre or "")
                               if not unicodedata.combining(caracter)).upper().split())
    categorias = {
        "CONTADO": "efectivo", "EFECTIVO": "efectivo",
        "TARJETA DE CREDITO": "tarjeta", "TARJETA DE DEBITO": "tarjeta", "TARJETA": "tarjeta",
        "TRANSFERENCIA": "transferencia", "CHEQUE": "transferencia",
        "CREDITO": "credito", "CREDITO AL CLIENTE": "credito",
    }
    if etiqueta not in categorias:
        raise ValueError("Metodo de pago sin clasificacion aprobada.")
    return categorias[etiqueta]


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
    def abrir_sesion_caja(usuario_id: int, monto_inicial: float, session=None, confirmar=True) -> tuple[bool, str, dict | None]:
        """
        Registers a new box session with the state 'ABIERTA' and its initial fund.
        """
        def _abrir(s):
            if not math.isfinite(float(monto_inicial)) or monto_inicial < 0:
                return False, "Fondo inicial invalido.", None
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
            if confirmar:
                s.commit()
                s.refresh(nueva_sesion)
            else:
                s.flush()
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

        if not confirmar and session is None:
            return False, "Se requiere session para confirmar=False.", None
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
    def acumular_venta(sesion_id: int, monto: float, forma_pago: str, session=None, confirmar=True) -> tuple[bool, str]:
        """
        Accumulates money from a sale into the open session of the box, filtered by payment method.
        """
        def _acumular(s):
            if not math.isfinite(float(monto)) or monto < 0:
                return False, "Monto de venta invalido."
            exito, mensaje = GestorSesionCaja.ajustar_venta(sesion_id, monto, forma_pago, s)
            if exito and confirmar:
                s.commit()
            return exito, mensaje

        if not confirmar and session is None:
            return False, "Se requiere session para confirmar=False."
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
    def ajustar_venta(sesion_id, monto, forma_pago, session):
        try:
            categoria = clasificar_forma_pago(forma_pago)
        except ValueError as error:
            return False, str(error)
        if not math.isfinite(float(monto)):
            return False, "Delta de caja invalido."
        sesion = session.get(SesionCaja, sesion_id)
        if sesion is None or sesion.estado != "ABIERTA":
            return False, "La caja origen no esta ABIERTA; requiere conciliacion."
        if categoria != "credito":
            campo = f"ventas_{categoria}"
            saldo = round(getattr(sesion, campo) + monto, 2)
            if saldo < 0:
                return False, "Acumulado insuficiente; requiere conciliacion."
            setattr(sesion, campo, saldo)
        sesion.efectivo_esperado = sesion.monto_inicial + sesion.ventas_efectivo + sesion.entradas_efectivo - sesion.retiros_efectivo
        return True, "Acumulacion ajustada."

    @staticmethod
    def registrar_entrada_retiro(sesion_id: int, monto: float, es_entrada: bool, session=None, confirmar=True) -> tuple[bool, str]:
        """
        Register a custom cash entry or withdrawal during the shift.
        """
        def _registrar(s):
            if not math.isfinite(float(monto)) or monto < 0:
                return False, "Monto de entrada/retiro invalido."
            sesion = s.get(SesionCaja, sesion_id)
            if not sesion or sesion.estado != "ABIERTA":
                return False, "La sesión de caja no coincide o no está abierta."

            if es_entrada:
                sesion.entradas_efectivo += monto
            else:
                sesion.retiros_efectivo += monto

            sesion.efectivo_esperado = sesion.monto_inicial + sesion.ventas_efectivo + sesion.entradas_efectivo - sesion.retiros_efectivo
            if confirmar:
                s.commit()
            return True, "Registro exitoso."

        if not confirmar and session is None:
            return False, "Se requiere session para confirmar=False."
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
    def cerrar_sesion_caja(sesion_id: int, conteo_usuario: float, session=None, confirmar=True) -> tuple[bool, str, dict | None]:
        """
        Closes the active cash session of the box calculating differences and setting state 'CERRADA'.
        """
        def _cerrar(s):
            if not math.isfinite(float(conteo_usuario)) or conteo_usuario < 0:
                return False, "Conteo invalido.", None
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

            if confirmar:
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

        if not confirmar and session is None:
            return False, "Se requiere session para confirmar=False.", None
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
