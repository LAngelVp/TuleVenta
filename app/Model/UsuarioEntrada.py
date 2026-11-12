def validar_password_nuevo(password):
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("La clave nueva debe contener al menos 12 caracteres.")
    if password != password.strip():
        raise ValueError("La clave nueva no admite espacios al inicio o al final.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La clave nueva no puede superar 72 bytes UTF-8.")
    return password