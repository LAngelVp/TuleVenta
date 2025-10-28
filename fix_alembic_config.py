# fix_alembic_config.py
import os
import re

def fix_alembic_ini():
    """Corrige alembic.ini"""
    ini_path = 'alembic.ini'
    
    with open(ini_path, 'r') as f:
        content = f.read()
    
    # Verificar si ya tiene las configuraciones
    if 'version_table = alembic_version' not in content:
        # Agregar después de sqlalchemy.url
        new_content = re.sub(
            r'(sqlalchemy\.url\s*=\s*[^\n]+)',
            r'\1\nversion_table = alembic_version\nversion_table_schema = public',
            content
        )
        
        with open(ini_path, 'w') as f:
            f.write(new_content)
        print("✅ alembic.ini actualizado")
    else:
        print("✅ alembic.ini ya está correcto")

def fix_env_py():
    """Corrige alembic/env.py"""
    env_path = 'alembic/env.py'
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    changes_made = False
    
    # 1. Agregar import text si no existe
    if 'from sqlalchemy import text' not in content:
        content = content.replace(
            'from sqlalchemy import engine_from_config',
            'from sqlalchemy import engine_from_config\nfrom sqlalchemy import text'
        )
        changes_made = True
    
    # 2. Agregar version_table_schema a run_migrations_offline
    if 'version_table_schema="public"' not in content:
        offline_config = '''context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},'''
        
        new_offline_config = '''context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="public",
        version_table="alembic_version"'''
        
        content = content.replace(offline_config, new_offline_config)
        changes_made = True
    
    # 3. Agregar SET search_path y config a run_migrations_online
    if 'connection.execute(text("SET search_path TO public"))' not in content:
        # Buscar el with connectable.connect() y agregar después
        online_pattern = r'(with connectable\.connect\(\) as connection:)'
        replacement = r'''\1
        # ⭐ ESTABLECER SCHEMA POR DEFECTO
        connection.execute(text("SET search_path TO public"))'''
        
        content = re.sub(online_pattern, replacement, content)
        changes_made = True
    
    # 4. Agregar configuraciones al context.configure online
    if 'include_schemas=True' not in content:
        online_config_pattern = r'context\.configure\(\s*connection=connection,\s*target_metadata=target_metadata\s*\)'
        new_online_config = '''context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="public",
            version_table="alembic_version",
            include_schemas=True
        )'''
        
        content = re.sub(online_config_pattern, new_online_config, content)
        changes_made = True
    
    if changes_made:
        with open(env_path, 'w') as f:
            f.write(content)
        print("✅ alembic/env.py actualizado")
    else:
        print("✅ alembic/env.py ya está correcto")

if __name__ == "__main__":
    print("🔧 Corrigiendo configuración de Alembic...")
    fix_alembic_ini()
    fix_env_py()
    print("🎉 Configuración corregida. Ahora Alembic debería crear la tabla automáticamente.")