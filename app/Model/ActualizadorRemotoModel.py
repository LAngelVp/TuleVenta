import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from app.version import __version__, es_version_mayor, repositorio_github
from app.runtime_paths import ruta_recurso


def validar_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.hostname not in {'api.github.com', 'github.com', 'objects.githubusercontent.com', 'release-assets.githubusercontent.com', 'github-releases.githubusercontent.com'}:
        raise ValueError('Destino HTTPS no autorizado')
    return url


class _RedirectSeguro(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        validar_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


@dataclass(frozen=True)
class Actualizacion:
    version: str
    nombre: str
    url: str
    size: int
    sha256: str


class ActualizadorRemotoModel:
    TIMEOUT = 10
    MAX_SIZE = 2 * 1024 ** 3
    DEADLINE = 600

    def __init__(self, owner=None, repo=None, opener=None):
        self.owner, self.repo = (owner, repo) if owner and repo else repositorio_github()
        if not all(re.fullmatch(r'[A-Za-z0-9_.-]+', value) for value in (self.owner, self.repo)):
            raise ValueError('Repositorio invalido')
        self.opener = opener or build_opener(_RedirectSeguro()).open

    def _open(self, url):
        return self.opener(Request(validar_url(url), headers={'User-Agent': 'TuleVenta/' + __version__, 'Accept': 'application/vnd.github+json'}), timeout=self.TIMEOUT)

    def _read(self, url, limit):
        with self._open(url) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Respuesta demasiado grande')
        return data

    def comprobar(self):
        data = json.loads(self._read(f'https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest', 1024 ** 2))
        if data.get('draft') or data.get('prerelease'):
            return None
        tag = data.get('tag_name', '')
        if not re.fullmatch(r'v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)', tag, re.ASCII):
            raise ValueError('Tag estable invalido')
        if not es_version_mayor(tag, __version__):
            return None
        name = f'TuleVenta-Update-{tag}-windows-x64.exe'
        def asset(filename):
            matches = [item for item in data.get('assets', []) if item.get('name') == filename]
            if len(matches) != 1:
                raise ValueError('Asset ausente o duplicado: ' + filename)
            return matches[0]
        exe = asset(name)
        checksum = self._read(asset(name + '.sha256')['browser_download_url'], 4096).decode('ascii').strip()
        match = re.fullmatch(r'([a-fA-F0-9]{64})(?:[ \t]+\*?([^\r\n]+))?', checksum)
        if not match or (match[2] and match[2] != name):
            raise ValueError('SHA-256 invalido')
        size = exe.get('size')
        if type(size) is not int or not 0 < size <= self.MAX_SIZE:
            raise ValueError('Tamano invalido')
        return Actualizacion(tag, name, validar_url(exe['browser_download_url']), size, match[1].lower())

    def descargar(self, update, progreso=lambda value: None, cancelado=lambda: False):
        if (not re.fullmatch(r'TuleVenta-Update-v\d+\.\d+\.\d+-windows-x64\.exe', update.nombre, re.ASCII)
                or not re.fullmatch(r'[a-f0-9]{64}', update.sha256)
                or type(update.size) is not int or not 0 < update.size <= self.MAX_SIZE):
            raise ValueError('Metadatos de descarga invalidos')
        if getattr(sys, 'frozen', False) and Path(tempfile.gettempdir()).resolve().is_relative_to(Path(sys.executable).resolve().parent):
            raise ValueError('La carpeta temporal no puede estar dentro de la instalacion')
        directory = Path(tempfile.mkdtemp(prefix='TuleVenta-update-'))
        destination = directory / update.nombre
        partial = destination.with_suffix('.exe.part')
        digest = hashlib.sha256()
        total = 0
        started = time.monotonic()
        try:
            with self._open(update.url) as response, partial.open('xb') as output:
                while True:
                    if cancelado() or time.monotonic() - started > self.DEADLINE:
                        raise TimeoutError('Descarga cancelada o tiempo agotado')
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > update.size or total > self.MAX_SIZE:
                        raise ValueError('Tamano de descarga incorrecto')
                    output.write(chunk)
                    digest.update(chunk)
                    progreso(min(99, total * 100 // update.size))
            if total != update.size or digest.hexdigest() != update.sha256:
                raise ValueError('Tamano o SHA-256 incorrecto')
            partial.replace(destination)
            progreso(100)
            return destination
        except Exception:
            partial.unlink(missing_ok=True)
            directory.rmdir()
            raise


def lanzar_instalador(path, expected_hash):
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        raise ValueError('Actualizar requiere la aplicacion instalada en Windows')
    path = Path(path).resolve()
    with path.open('rb') as binary:
        digest = hashlib.file_digest(binary, 'sha256').hexdigest()
    if digest != expected_hash:
        raise ValueError('SHA-256 cambio antes de ejecutar')
    bridge = ruta_recurso('installer', 'scripts', 'aplicar_actualizacion.ps1')
    if not bridge.is_file():
        raise ValueError('No se encontro el puente de actualizacion')
    temporary_bridge = path.parent / 'aplicar_actualizacion.ps1'
    shutil.copyfile(bridge, temporary_bridge)
    powershell = Path(os.environ.get('SYSTEMROOT', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    return subprocess.Popen([
        str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(temporary_bridge), '-ParentProcessId', str(os.getpid()),
        '-Installer', str(path), '-ExpectedHash', expected_hash,
        '-Application', str(Path(sys.executable).resolve()),
    ], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)