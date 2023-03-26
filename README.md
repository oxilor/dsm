# Declarative schema management tool

CLI for managing a PostgreSQL database schema in a declarative way.

Workflow:
1. Modify a file with your database schema (e.g. add a new column). You can store the schema in a single file (e.g. `schema.sql`) or in multiple files (e.g. one file for each table for convenience).
1. Run this tool, which will generate DLL statements allowing your database to reach the desired schema (e.g. `ALTER TABLE ... ADD COLUMN ...`).
1. Make sure everything is in order and confirm the changes.
1. The tool will execute these DDL statements and your database schema will have the desired state.

This tool uses [migra](https://github.com/djrobstep/migra) under the hood.

## Commands

### diff

Prints DDL statements that should be executed to reach the desired schema.

```sh
docker run --rm --net=host -it -v "${PWD}/src/schema":/schema oxilor/dsm diff \
  --uri 'postgresql://user:password@localhost:5432/my_database' \
  --to /schema/main.sql
```

Arguments:
- `--uri` [required] – The [connection URI](https://www.postgresql.org/docs/current/libpq-connect.html#id-1.7.3.8.3.6) to the target database.
- `--to` [required] – The path to a schema file or directory with multiple SQL files (e.g. one file is one table). This argument can be specified multiple times.
- `--temp-db-name` [optional, default='temp'] – The name of the temporary database used to detect the desired schema.
- `--unsafe` [optional] – Don't throw an exception if DROP statements are generated.
- `--schema` [optional] – Generate DDL statements only for the specified schema.
- `--exclude-schema` [optional] – Generate DDL statements for all schemas except the specified one.
- `--ignore-extension-versions` [optional] – Ignore versions when comparing extensions.
- `--with-privileges` [optional] – Include permission-related change statements (GRANT, REVOKE).

Example output:
```
alter table "public"."tasks" add column "name" text not null;
```

### apply

Generates DDL statements and executes them after confirmation.

```sh
docker run --rm --net=host -it -v "${PWD}/src/schema":/schema oxilor/dsm apply \
  --uri 'postgresql://user:password@localhost:5432/my_database' \
  --to /schema/main.sql
```

The arguments are the same as for `diff` and additionally:
- `--no-confirmation` [optional] – Execute the generated DDL statements without confirmation.

Example output:
```
Pending changes:

alter table "public"."tasks" add column "name" text not null;

Do you want to execute them? [y/n] y
Done.
```

### save

Saves DDL statements into a file.

```sh
docker run --rm --net=host -it -v "${PWD}/src/schema":/schema oxilor/dsm save \
  --uri 'postgresql://user:password@localhost:5432/my_database' \
  --to /schema/main.sql \
  --file /schema/pending.sql
```

The arguments are the same as for `diff` and additionally:
- `--file` [optional, default='/schema/pending.sql'] – The path to the file where the generated DDL statements will be stored.

Example output:
```
Saved the file "/schema/pending.sql" with the following changes:

alter table "public"."tasks" add column "name" text not null;
```

### execute

Executes SQL statements from a file.

```sh
docker run --rm --net=host -it -v "${PWD}/src/schema":/schema oxilor/dsm execute \
  --uri 'postgresql://user:password@localhost:5432/my_database' \
  --file /schema/pending.sql
```

Arguments:
- `--uri` [required] – The connection URI to the target database.
- `--file` [optional, default='/schema/pending.sql'] – The path to the file with SQL statements that should be executed to reach the desired schema.

Example output:
```
The following changes were made:

alter table "public"."tasks" add column "name" text not null;
```
