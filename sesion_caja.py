from datetime import datetime
import math
from sqlalchemy import select, update
from app.DataBase.conexionBD import Conexion_base_datos
from app.Model.BaseDatosModel import SesionCaja, Ventas
from app.Model.FormaPago import clasificar_forma_pago


class GestorSesionCaja:
    @staticmethod
    def analizar_arqueo(sesion: dict, conteo_usuario: float) -> dict:
        valores = {}
        for campo in ("monto_inicial", "ventas_efectivo", "entradas_efectivo", "retiros_efectivo"):
            try:
                valor = float(sesion[campo])
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise ValueError(f"{campo}: importe invalido.") from error
            if not math.isfinite(valor) or valor < 0:
                raise ValueError(f"{campo}: importe invalido.")
            valores[campo] = valor
        try:
            conteo = float(conteo_usuario)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Conteo invalido.") from error
        if not math.isfinite(conteo) or conteo < 0:
            raise ValueError("Conteo invalido.")
        esperado = valores["monto_inicial"] + valores["ventas_efectivo"] + valores["entradas_efectivo"] - valores["retiros_efectivo"]
        diferencia = conteo - esperado
        if not math.isfinite(esperado) or not math.isfinite(diferencia):
            raise ValueError("Balance no finito.")
        visible = round(diferencia, 2)
        estado = "CUADRADA" if visible == 0 else ("SOBRANTE" if visible > 0 else "FALTANTE")
        return {"efectivo_esperado": esperado, "conteo_usuario": conteo,
                "diferencia": diferencia, "estado": estado}

    @staticmethod
    def obtener_resumen_turno(sesion_id: int, session=None) -> tuple[bool, str, dict | None]:
        if not isinstance(sesion_id, int) or isinstance(sesion_id, bool) or sesion_id <= 0:
            return False, "Identificador de caja invalido.", None

        def _consultar(session_actual):
            caja = session_actual.get(SesionCaja, sesion_id)
            if caja is None or caja.estado != "ABIERTA":
                return False, "La caja indicada no esta abierta.", None
            campos = ("id", "usuario_id", "fecha_apertura", "estado", "monto_inicial",
                      "ventas_efectivo", "ventas_tarjeta", "ventas_transferencia",
                      "entradas_efectivo", "retiros_efectivo")
            resumen = {campo: getattr(caja, campo) for campo in campos}
            ventas = session_actual.execute(
                select(Ventas).where(Ventas.sesion_caja_id == sesion_id).order_by(Ventas.fecha, Ventas.id)
            ).scalars().all()
            campos_venta = ("id", "folio", "fecha", "empleado_id", "forma_pago", "estado",
                            "activo", "total", "cancelada_por_usuario_id", "fecha_cancelacion")
            resumen["movimientos_ventas"] = [
                {campo: getattr(venta, campo) for campo in campos_venta} for venta in ventas
            ]
            return True, "Resumen del turno cargado.", resumen

        if session is not None:
            return _consultar(session)
        try:
            with Conexion_base_datos() as database:
                return _consultar(database.abrir_sesion())
        except Exception:
            return False, "No se pudo consultar el turno de caja.", None

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
    def procesar_movimiento_efectivo(sesion_id: int, monto: float, es_entrada: bool) -> tuple[bool, str, bool]:
        if not isinstance(sesion_id, int) or isinstance(sesion_id, bool) or sesion_id <= 0:
            return False, "Identificador de caja invalido.", False
        try:
            importe = float(monto)
        except (TypeError, ValueError, OverflowError):
            return False, "Importe invalido.", False
        if isinstance(monto, bool) or not math.isfinite(importe) or importe <= 0 or not isinstance(es_entrada, bool):
            return False, "El importe debe ser positivo y el tipo de movimiento valido.", False
        en_commit = False
        try:
            with Conexion_base_datos() as database:
                session = database.abrir_sesion()
                try:
                    caja = session.execute(
                        select(SesionCaja).where(SesionCaja.id == sesion_id).with_for_update()
                    ).scalar_one_or_none()
                    if caja is None or caja.estado != "ABIERTA":
                        session.rollback()
                        return False, "La caja seleccionada ya no esta abierta.", False
                    exito, mensaje = GestorSesionCaja.registrar_entrada_retiro(
                        sesion_id, importe, es_entrada, session=session, confirmar=False
                    )
                    if not exito:
                        session.rollback()
                        return False, mensaje, False
                    GestorSesionCaja.analizar_arqueo({
                        campo: getattr(caja, campo) for campo in
                        ("monto_inicial", "ventas_efectivo", "entradas_efectivo", "retiros_efectivo")
                    }, 0)
                    session.flush()
                    en_commit = True
                    session.commit()
                    return True, "Movimiento de efectivo registrado.", False
                except Exception:
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    raise
        except Exception:
            mensaje = ("Confirmacion incierta: verifica el balance antes de volver a registrar."
                       if en_commit else "No se pudo registrar el movimiento de efectivo.")
            return False, mensaje, en_commit

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
