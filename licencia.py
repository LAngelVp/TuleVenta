import base64
import json
from datetime import datetime, date
from pathlib import Path
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from PySide6.QtCore import QSettings

from hardware import get_hardware_id

def get_public_key_path() -> Path:
    """
    Resolves the path to 'licencia_publica.pem'.
    Handles standard development runs, current working directory,
    and PyInstaller frozen executable environments.
    """
    # 1. Dev run or bundled in _MEIPASS
    path_file_dir = Path(__file__).parent / "licencia_publica.pem"
    if path_file_dir.exists():
        return path_file_dir

    # 2. Curren working directory
    path_cwd = Path.cwd() / "licencia_publica.pem"
    if path_cwd.exists():
        return path_cwd

    # 3. Next to the compiled executable
    if getattr(sys, 'frozen', False):
        path_exe = Path(sys.executable).parent / "licencia_publica.pem"
        if path_exe.exists():
            return path_exe

    # Default fallback
    return path_file_dir

def load_public_key():
    """
    Loads the RSA public key from the pem file.
    """
    pem_path = get_public_key_path()
    if not pem_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de clave pública: '{pem_path}'")

    with open(pem_path, "rb") as key_file:
        public_key = load_pem_public_key(key_file.read())
    return public_key

def validar_licencia(licencia_str: str) -> tuple[bool, str, dict]:
    """
    Validates the signature, Hardware ID, and expiration date of the given license key.

    The license has the format: payloadBase64.firmaBase64

    Returns:
        tuple[bool, str, dict]: (is_valid, validation_message, decoded_payload_dict)
    """
    if not licencia_str or not isinstance(licencia_str, str):
        return False, "La clave de la licencia está vacía o es inválida.", {}

    licencia_str = licencia_str.strip()
    parts = licencia_str.split(".")
    if len(parts) != 2:
        return False, "Formato de clave de licencia inválido. Debe estructurarse como 'payloadBase64.firmaBase64'.", {}

    payload_b64, signature_b64 = parts

    # 1. Decodificar la firma digest
    try:
        # Pad signature b64 standardly
        sig_padding = len(signature_b64) % 4
        if sig_padding:
            signature_b64 += "=" * (4 - sig_padding)
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        return False, f"La firma Base64 de la licencia no se pudo decodificar: {str(e)}", {}

    # 2. Cargar clave pública y verificar criptográficamente
    try:
        pub_key = load_public_key()
    except Exception as e:
        return False, f"Error al cargar la clave pública de validación: {str(e)}", {}

    try:
        pub_key.verify(
            signature_bytes,
            payload_b64.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except InvalidSignature:
        return False, "Firma digital de licencia inválida. La clave ha sido alterada o es incorrecta.", {}
    except Exception as e:
        return False, f"Error inesperado al validar la firma de la licencia: {str(e)}", {}

    # 3. Decodificar Payload Base64
    try:
        payload_padding = len(payload_b64) % 4
        if payload_padding:
            payload_b64 += "=" * (4 - payload_padding)
        payload_bytes = base64.b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
    except Exception as e:
        return False, f"No se pudo decodificar el payload JSON de la licencia: {str(e)}", {}

    # 4. Validar estructura del payload
    cliente = payload.get("cliente")
    lic_hardware_id = payload.get("hardware_id")
    vencimiento_str = payload.get("vencimiento")

    if not cliente or not lic_hardware_id or not vencimiento_str:
        return False, "La estructura del payload de la licencia es incompleta (faltan campos obligatorios).", payload

    # 5. Comprobar que el Hardware ID coincida
    current_hw_id = get_hardware_id()
    if lic_hardware_id.strip().upper() != current_hw_id:
        return False, f"Hardware ID no coincide.\nLicencia emitida para: {lic_hardware_id}\nEste equipo es: {current_hw_id}", payload

    # 6. Comprobar la fecha de vencimiento
    try:
        exp_date = datetime.strptime(vencimiento_str, "%Y-%m-%d").date()
    except Exception:
        return False, f"El formato de la fecha de vencimiento '{vencimiento_str}' es inválido (debe ser YYYY-MM-DD).", payload

    if exp_date < date.today():
        return False, f"La licencia de {cliente} expiró el: {vencimiento_str}", payload

    return True, "Licencia válida de forma exitosa.", payload

def guardar_licencia(licencia_str: str) -> None:
    """
    Saves the license key to the platform native persistent storage (using QSettings).
    """
    settings = QSettings("TuleVenta", "Licencia")
    settings.setValue("licencia_key", licencia_str.strip())

def leer_licencia() -> str:
    """
    Loads the persistent license key from QSettings.
    """
    settings = QSettings("TuleVenta", "Licencia")
    val = settings.value("licencia_key", "")
    if isinstance(val, str):
        return val.strip()
    return ""

def obtener_info_licencia() -> dict:
    """
    Reads the stored license key via QSettings, decodes the JSON payload,
    calculates remaining days and validity, returning a metadata dict.

    Returns:
        dict: {
            "cliente": str,
            "vencimiento": str,
            "dias_restantes": int,
            "estado_valido": bool,
            "mensaje": str
        }
    """
    lic_str = leer_licencia()
    valido, mensaje, payload = validar_licencia(lic_str)

    cliente = payload.get("cliente", "Sin activar / Desconocido")
    vencimiento_str = payload.get("vencimiento", "N/D")

    dias_restantes = 0
    if vencimiento_str != "N/D":
        try:
            exp_date = datetime.strptime(vencimiento_str, "%Y-%m-%d").date()
            dias_restantes = (exp_date - date.today()).days
        except Exception:
            pass

    return {
        "cliente": cliente,
        "vencimiento": vencimiento_str,
        "dias_restantes": dias_restantes,
        "estado_valido": valido,
        "mensaje": mensaje
    }
