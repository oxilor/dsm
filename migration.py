from migra import Migration
from sqlbag import S
from psycopg2 import connect
from os import getcwd
from os.path import isdir, isfile, join
from glob import glob
from contextlib import closing

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
    sql_files = glob(join(full_path, '**/*.sql'), recursive=True)
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

def get_migration(args):
  """Generate DDL statements that should be executed to reach the desired schema."""
  # Apply the desired schema against the temporary database
  desired_schema = ''
  for to in args.to:
    desired_schema += read_schema(to) + '\n'
  if desired_schema:
    execute_sql(args.temp_uri, desired_schema)

  # Generate DDL statements
  statements = ''
  with S(args.uri) as x_from, S(args.temp_uri) as x_target:
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

  return statements.strip()
