import subprocess
import platform
import hashlib
import uuid
import re

def get_hardware_id() -> str:
    """
    Obtains the Motherboard UUID on Windows (using WMIC and PowerShell as fallback).
    If it retrieved a generic, empty, or placeholder UUID, or if the commands fail,
    it falls back to a deterministic SHA256 hash generated via secondary hardware/system details.
    """
    system_name = platform.system().upper()
    raw_uuid = None

    if "WIN" in system_name:
        # Option 1: Try WMIC
        try:
            output = subprocess.check_output(
                "wmic csproduct get uuid",
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if len(lines) > 1:
                # The first line is the header (UUID), the second is the actual value
                raw_uuid = lines[1]
        except Exception:
            raw_uuid = None

        # Option 2: Fallback to PowerShell if WMIC failed or returned empty
        if not raw_uuid:
            try:
                output = subprocess.check_output(
                    'powershell -NoProfile -Command "Get-CimInstance Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"',
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                raw_uuid = output.strip()
            except Exception:
                raw_uuid = None

    # Clean the retrieved UUID if any
    cleaned_uuid = None
    if raw_uuid:
        cleaned_uuid = re.sub(r'[\s\r\n\t]+', '', raw_uuid).upper()

    # Define generic placeholders to reject
    generic_placeholders = {
        "00000000-0000-0000-0000-000000000000",
        "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
        "TOBEFILLEDBYO.E.M.",
        "TOBEFILLEDBYOEM",
        "NONE",
        "DEFAULTSTRING",
        "NOTSPECIFIED",
        "UNKNOWN",
        "NOTAVAILABLE",
        "FILL O.E.M."
    }

    # Check if cleaned_uuid is valid and not generic
    is_valid = cleaned_uuid and cleaned_uuid not in generic_placeholders and len(cleaned_uuid) >= 10

    if is_valid:
        return cleaned_uuid

    # Fallback Mechanism: Generate a SHA256 using secondary system identifiers
    secondary_details = []

    # 1. MAC Address (reliable and built-in)
    try:
        node = uuid.getnode()
        # Ensure it is not a random MAC (getnode returns random if it can't find MAC, but we can't easily prevent that)
        secondary_details.append(f"MAC:{node}")
    except Exception:
        pass

    # 2. Windows C: volume serial number
    if "WIN" in system_name:
        try:
            output = subprocess.check_output(
                "vol C:",
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            for line in output.splitlines():
                if "SERIE" in line.upper() or "SERIAL" in line.upper():
                    secondary_details.append(line.strip())
                    break
        except Exception:
            pass

    # 3. Disk serial numbers using WMIC
    if "WIN" in system_name:
        try:
            output = subprocess.check_output(
                "wmic diskdrive get serialnumber",
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            for line in output.splitlines():
                cleaned_line = line.strip()
                if cleaned_line and "SERIALNUMBER" not in cleaned_line.upper():
                    secondary_details.append(f"DISK:{cleaned_line}")
        except Exception:
            pass

    # 4. System identification properties
    try:
        secondary_details.append(f"NODE:{platform.node()}")
        secondary_details.append(f"PROC:{platform.processor()}")
        secondary_details.append(f"ARCH:{platform.machine()}")
    except Exception:
        pass

    # Form a single deterministic identifier and hash it with SHA-256
    composite_string = "|".join(secondary_details)
    fallback_hash = hashlib.sha256(composite_string.encode("utf-8")).hexdigest().upper()

    return fallback_hash
