"""Run SQL tests against a disposable loopback PostgreSQL cluster."""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    binaries = root / "installer/third_party/postgresql-portable/bin"
    temporary = Path(tempfile.mkdtemp(prefix="tuleventa-pg-test-"))
    data = temporary / "data"
    started = False
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    def run(name, *arguments):
        subprocess.run([str(binaries / (name + ".exe")), *map(str, arguments)], check=True)

    try:
        run("initdb", "-D", data, "-U", "ephemeral_admin", "-A", "trust", "--encoding=UTF8", "--no-locale")
        run("pg_ctl", "-D", data, "-l", temporary / "postgres.log", "-o",
            f"-h 127.0.0.1 -p {port}", "-w", "start")
        started = True
        run("psql", "-h", "127.0.0.1", "-p", port, "-U", "ephemeral_admin", "-d", "postgres",
            "-v", "ON_ERROR_STOP=1", "-c", "CREATE ROLE tuleventa_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE")
        run("createdb", "-h", "127.0.0.1", "-p", port, "-U", "ephemeral_admin",
            "-O", "tuleventa_test", "tuleventa_test_ephemeral")
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
            TULEVENTA_TEST_DATABASE_URL=f"postgresql+psycopg2://tuleventa_test@127.0.0.1:{port}/tuleventa_test_ephemeral",
            TULEVENTA_TEST_ALLOWED_TARGET=f"127.0.0.1:{port}/tuleventa_test_ephemeral",
            TULEVENTA_TEST_POSTGRES_MAJOR="18")
        arguments = sys.argv[1:] or ["-q", "-m", "db", "--tb=short"]
        return subprocess.run([sys.executable, "-m", "pytest", *arguments], cwd=root, env=environment).returncode
    finally:
        if started or (data / "postmaster.pid").exists():
            run("pg_ctl", "-D", data, "-m", "fast", "-w", "stop")
        shutil.rmtree(temporary)
        print("Ephemeral cluster stopped and removed:", temporary)


if __name__ == "__main__":
    raise SystemExit(main())