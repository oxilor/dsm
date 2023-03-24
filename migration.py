from migra import Migration
from sqlbag import S
from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from os import getcwd
from os.path import isdir, isfile, join
from glob import glob
from contextlib import closing
import re

class SchemaNotFound(Exception):
  "Raised when the schema is neither a file nor a directory."
  pass

def read_schema(path: str):
  """Read a database schema.
  The path can be either a file or a directory with SQL files.
  """
  cwd = getcwd()
  full_path = join(cwd, path)

  if isdir(full_path):
    statements = ''
    sql_files = glob(join(full_path, '*.sql'))
    for file_name in sorted(sql_files):
      file_path = join(cwd, file_name)
      if (isfile(file_path)):
        with open(file_path, 'r') as f:
          statements += f.read() + '\n'
    return statements

  elif isfile(full_path):
    with open(full_path, 'r') as f:
      return f.read()

  else:
    raise SchemaNotFound

def execute_sql(uri: str, sql: str):
  """Execute SQL statements in the specified database."""
  with closing(connect(uri)) as conn:
    with conn.cursor() as cursor:
      cursor.execute(sql)
      conn.commit()

def create_database(uri: str, dbName: str):
  """Create a new database."""
  with closing(connect(uri)) as conn:
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT);
    with conn.cursor() as cursor:
      cursor.execute('CREATE DATABASE "%s";' % dbName)
      conn.commit()

def drop_database(uri: str, dbName: str):
  """Drop the existing database."""
  with closing(connect(uri)) as conn:
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT);
    with conn.cursor() as cursor:
      # Prevent future connections
      cursor.execute('REVOKE CONNECT ON DATABASE "%s" FROM public;' % dbName)
      conn.commit()

      # Terminate all connections
      cursor.execute("SELECT pid, pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '%s';" % dbName)
      conn.commit()

      # Drop the database
      cursor.execute('DROP DATABASE "%s";' % dbName)
      conn.commit()

def replace_db_name_in_dsn(dsn: str, dbName: str):
  """Replace the database name in DSN."""
  return re.sub('(?<=//)(.*/)\w+', r'\1%s' % dbName, dsn)

def get_migration(args):
  """Generate DDL statements that should be executed to reach the desired schema."""
  # Create a temporary database
  create_database(args.uri, args.temp_db_name)
  try:
    # Apply the desired schema against the temporary database
    temp_db_uri = replace_db_name_in_dsn(args.uri, args.temp_db_name)
    desired_schema = read_schema(args.to).strip()
    if desired_schema:
      execute_sql(temp_db_uri, desired_schema)

    # Generate DDL statements
    statements = ''
    with S(args.uri) as x_from, S(temp_db_uri) as x_target:
      migration = Migration(
        x_from,
        x_target,
        schema=args.schema,
        exclude_schema=args.exclude_schema,
        ignore_extension_versions=args.ignore_extension_versions,
      )
      if args.unsafe:
        migration.set_safety(False)
      migration.add_all_changes(privileges=args.with_privileges)
      statements = migration.sql
  finally:
    # Drop the temporary database
    drop_database(args.uri, args.temp_db_name)

  return statements.strip()
