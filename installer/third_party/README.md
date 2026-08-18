Coloca aqui una carpeta portable completa de PostgreSQL con este nombre:

`postgresql-portable`

La estructura minima esperada es esta:

`postgresql-portable\bin\initdb.exe`

`postgresql-portable\bin\pg_ctl.exe`

`postgresql-portable\bin\psql.exe`

`postgresql-portable\bin\createdb.exe`

La carpeta debe incluir tambien las librerias y recursos de PostgreSQL (`lib`, `share`, etc.), porque `initdb` no funciona con solo los ejecutables.

Si cambias de major version, ajusta `PostgreSqlVersionMajor` y, si quieres, el nombre del servicio en `installer/TuleVentaSetup.iss`.