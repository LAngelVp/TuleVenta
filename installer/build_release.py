import hashlib
import re
import subprocess
import sys
from pathlib import Path


def generar_instalador(root, compiler, version, runner=subprocess.run):
    root = Path(root).resolve()
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('El instalador requiere una version estable X.Y.Z')
    majors = set()
    for name in ('pg_ctl', 'initdb', 'psql'):
        binary = root / 'installer/third_party/postgresql-portable/bin' / (name + '.exe')
        result = runner([str(binary), '--version'], check=True, capture_output=True,
                        text=True, timeout=10, cwd=root)
        match = re.search(r'PostgreSQL\) ([0-9]+)', result.stdout)
        if not match or int(match[1]) < 10:
            raise ValueError('Version PostgreSQL invalida: ' + name)
        majors.add(match[1])
    if len(majors) != 1:
        raise ValueError('Motores PostgreSQL incompatibles')
    major = majors.pop()
    output = root / 'installer/output'
    executable = output / f'TuleVenta-Update-v{version}-windows-x64.exe'
    previous = executable.stat().st_mtime_ns if executable.exists() else None
    print(f'Compilando TuleVenta {version}, PostgreSQL {major}', flush=True)
    runner([str(compiler), f'/DAppVersion={version}', f'/DPostgreSqlVersionMajor={major}',
            str(root / 'installer/TuleVentaSetup.iss')], check=True, cwd=root, timeout=3600)
    if not executable.is_file() or executable.stat().st_mtime_ns == previous:
        raise ValueError('Inno no genero un instalador nuevo en: ' + str(executable))
    with executable.open('rb') as binary:
        if binary.read(2) != b'MZ':
            raise ValueError('El artefacto generado no es un ejecutable Windows')
        binary.seek(0)
        digest = hashlib.file_digest(binary, 'sha256').hexdigest()
    checksum = executable.with_suffix('.exe.sha256')
    partial = checksum.with_suffix('.sha256.part')
    try:
        partial.write_text(digest + '  ' + executable.name + '\n', encoding='ascii')
        partial.replace(checksum)
    finally:
        partial.unlink(missing_ok=True)
    print(f'EXE: {executable}\nSHA-256: {checksum}', flush=True)
    return executable, checksum


def main():
    if len(sys.argv) != 2:
        print('Uso: build_release.py <ruta ISCC.exe>', file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from app.version import __version__
    try:
        generar_instalador(root, Path(sys.argv[1]), __version__)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('No se genero un release completo: ' + str(error), file=sys.stderr)
        return error.returncode if isinstance(error, subprocess.CalledProcessError) and 0 < error.returncode < 256 else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())