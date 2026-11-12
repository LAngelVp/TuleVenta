import unicodedata


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