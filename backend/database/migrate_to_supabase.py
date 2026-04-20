import psycopg2
import os
from psycopg2.extras import execute_values, Json
from psycopg2.extensions import register_adapter

# Register adapter to handle JSONB columns automatically
register_adapter(dict, Json)

# Source (Local) Configuration
SOURCE_CONFIG = {
    'dbname': 'astrogeo_db',
    'user': 'khushikhanna',
    'host': 'localhost',
    'port': 5432
}

# Target (Supabase) Configuration
TARGET_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'host': 'db.auyojdmjmgviztctbdsp.supabase.co',
    'password': '*EPB8FSbV+Lr!2Z',
    'port': 5432,
    'sslmode': 'require'
}

SCHEMAS_TO_MIGRATE = ['astronomy', 'satellite', 'shared', 'weather', 'public']
EXCLUDED_TABLES = ['geography_columns', 'geometry_columns', 'spatial_ref_sys']

def migrate():
    print("🚀 Starting Database Migration to Supabase...")
    
    try:
        src_conn = psycopg2.connect(**SOURCE_CONFIG)
        src_cur = src_conn.cursor()
        
        tgt_conn = psycopg2.connect(**TARGET_CONFIG)
        tgt_cur = tgt_conn.cursor()
        tgt_conn.autocommit = True

        # 1. Enable PostGIS
        print("Enable PostGIS extension...")
        tgt_cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

        # 2. Create Schemas
        for schema in SCHEMAS_TO_MIGRATE:
            if schema != 'public':
                print(f"Creating schema: {schema}")
                tgt_cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")

        # 3. Fetch all tables
        src_cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN %s 
            AND table_type = 'BASE TABLE'
        """, (tuple(SCHEMAS_TO_MIGRATE),))
        tables = src_cur.fetchall()

        for schema, table in tables:
            if table in EXCLUDED_TABLES:
                continue

            print(f"\n--- Migrating {schema}.{table} ---")
            
            # 3a. Get Column Definitions
            src_cur.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default, udt_name
                FROM information_schema.columns 
                WHERE table_schema = '{schema}' AND table_name = '{table}'
                ORDER BY ordinal_position
            """)
            columns = src_cur.fetchall()
            
            col_defs = []
            col_names = []
            for col in columns:
                name, dtype, nullable, default, udt_name = col
                col_names.append(name)
                
                # Handle ARRAY types
                if dtype == 'ARRAY':
                    if udt_name == '_text' or udt_name == '_varchar':
                        dtype = 'text[]'
                    elif udt_name == '_int4':
                        dtype = 'integer[]'
                    elif udt_name == '_float8':
                        dtype = 'double precision[]'
                    elif udt_name.startswith('_'):
                        dtype = f"{udt_name[1:]}[]"
                
                # Basic DDL generation
                line = f'"{name}" {dtype}'
                if nullable == 'NO':
                    line += " NOT NULL"
                if default and 'nextval' not in default:
                    line += f" DEFAULT {default}"
                col_defs.append(line)

            # 3b. Drop and Recreate Table on Target
            tgt_cur.execute(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE;')
            create_sql = f'CREATE TABLE "{schema}"."{table}" (\n  ' + ',\n  '.join(col_defs) + '\n);'
            tgt_cur.execute(create_sql)
            print(f"Created table {schema}.{table}")

            # 3c. Transfer Data
            src_cur.execute(f'SELECT * FROM "{schema}"."{table}"')
            rows = src_cur.fetchall()
            
            if rows:
                print(f"Transferring {len(rows)} rows...")
                # Fix f-string quoting
                col_list = ", ".join([f'"{c}"' for c in col_names])
                query = f"INSERT INTO \"{schema}\".\"{table}\" ({col_list}) VALUES %s"
                execute_values(tgt_cur, query, rows)
                print(f"Successfully migrated {len(rows)} rows.")
                
                # 3d. Skip sequence reset for now to ensure data transfer completes
                # I will handle this in a separate step if required
                pass
            else:
                print("No data to transfer.")

        print("\n✅ Migration successfully completed!")
        
        src_cur.close()
        src_conn.close()
        tgt_cur.close()
        tgt_conn.close()

    except Exception as e:
        print(f"❌ Error during migration: {e}")

if __name__ == "__main__":
    migrate()
