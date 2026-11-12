import json
import os
import re
from app.runtime_paths import ruta_configuracion_mutable

__version__ = "1.0.0"
GITHUB_OWNER = "LAngelVp"
GITHUB_REPO = "TuleVentaInstaller"


def _semver(value):
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?', value, re.ASCII) if isinstance(value, str) else None
    if not match:
        raise ValueError('Version SemVer invalida')
    parts = match[4].split('.') if match[4] else []
    if any(part.isdigit() and len(part) > 1 and part.startswith('0') for part in parts):
        raise ValueError('Version SemVer invalida')
    return tuple(int(match[index]) for index in (1, 2, 3)), parts


def es_version_mayor(remota, local):
    remote, newer = _semver(remota)
    current, older = _semver(local)
    if remote != current:
        return remote > current
    if not newer or not older:
        return bool(older) and not newer
    for first, second in zip(newer, older):
        if first == second:
            continue
        if first.isdigit() and second.isdigit():
            return int(first) > int(second)
        if first.isdigit() != second.isdigit():
            return not first.isdigit()
        return first > second
    return len(newer) > len(older)


def repositorio_github():
    path = ruta_configuracion_mutable('actualizador.json', 'TULEVENTA_UPDATER_CONFIG_PATH')
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    owner = os.environ.get('TULEVENTA_GITHUB_OWNER', config.get('github_owner', GITHUB_OWNER))
    repo = os.environ.get('TULEVENTA_GITHUB_REPO', config.get('github_repo', GITHUB_REPO))
    if not all(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]+', value) and value not in ('.', '..') for value in (owner, repo)):
        raise ValueError('Configura el repositorio publico de actualizaciones')
    return owner, repo