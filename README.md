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
  --uri 'postgresql://user:password@localhost:5432/db_name' \
  --temp-uri 'postgresql://user:password@localhost:5432/temp_db_name' \
  --to /schema/main.sql
```

Arguments:
- `--uri` [required] – The [connection URI](https://www.postgresql.org/docs/current/libpq-connect.html#id-1.7.3.8.3.6) to the target database.
- `--temp-uri` [required] – The connection URI to the temporary database (must be empty). All SQL files with your schema will be executed in it (see `--to` argument). After that the difference between the target and temporary databases will be determined.
- `--to` [required] – The path to a file or directory with multiple files with your schema (e.g. one file is one table). This argument can be specified multiple times.
- `--unsafe` [optional] – Don't throw an exception if DROP statements are generated.
- `--schema` [optional] – Generate DDL statements only for the specified schema.
- `--exclude-schema` [optional] – Generate DDL statements for all schemas except the specified one.
- `--ignore-extension-versions` [optional] – Ignore versions when comparing extensions.
- `--with-privileges` [optional] – Include permission-related change statements (GRANT, REVOKE).

Example output:
```
alter table "public"."tasks" add column "name" text not null;
```

If there are no changes, then there is no output data. This is useful for CI jobs. For example:
```sh
diff=$(docker run oxilor/dsm diff) # The arguments are omitted for simplicity

if [ -z $diff ]; then
  echo "No changes"
else
  echo $diff
fi
```

### apply

Generates DDL statements and executes them after confirmation.

```sh
docker run --rm --net=host -it -v "${PWD}/src/schema":/schema oxilor/dsm apply \
  --uri 'postgresql://user:password@localhost:5432/db_name' \
  --temp-uri 'postgresql://user:password@localhost:5432/temp_db_name' \
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
  --uri 'postgresql://user:password@localhost:5432/db_name' \
  --temp-uri 'postgresql://user:password@localhost:5432/temp_db_name' \
  --to /schema/main.sql
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
  --uri 'postgresql://user:password@localhost:5432/db_name' \
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

## Usage examples

### Example 1. Docker compose

docker-compose.yml:
```yaml
version: '3.2'

services:
  dsm:
    image: oxilor/dsm
    # Check the connection URI to the target database (--uri)
    command: >
      apply
      --uri "postgresql://postgres:postgres@localhost:5432/db_name"
      --temp-uri "postgresql://postgres:postgres@localhost:5431/temp"
      --to /schema
      --unsafe
      --ignore-extension-versions
    network_mode: host
    volumes:
      - '../schema:/schema' # Check the path to a directory with your schema files (../schema)
    depends_on:
      temp-postgres:
        condition: service_healthy

  temp-postgres:
    image: postgres:15-alpine
    ports:
      - "5431:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: temp
    healthcheck:
      test: pg_isready -U postgres
      interval: 3s
```

How to run:
```sh
docker compose run dsm
```

### Example 2. Docker

sync-schema.sh:
```sh
#!/bin/sh

# Start the temporary database
docker run -d \
  -e "POSTGRES_USER=postgres" \
  -e "POSTGRES_PASSWORD=postgres" \
  -e "POSTGRES_DB=temp" \
  -p "5431:5432" \
  --health-cmd="pg_isready -U postgres" \
  --health-interval=3s \
  --name temp-postgres \
  postgres:15-alpine

# Wait until the database is ready
until docker inspect --format='{{.State.Health.Status}}' temp-postgres | grep -q 'healthy';
do
  sleep 3;
done

on_exit() {
  # Delete the temporary database
  {
    docker stop temp-postgres
    docker rm temp-postgres
  } &> /dev/null
}
trap on_exit EXIT

# Sync the database schema
# Check the path to a directory with your schema files (../schema)
# Check the connection URI to the target database (--uri)
docker run --rm --network=host -it \
  -v "../schema:/schema" \
  oxilor/dsm apply \
    --uri "postgresql://postgres:postgres@localhost:5432/db_name" \
    --temp-uri "postgresql://postgres:postgres@localhost:5431/temp" \
    --to /schema \
    --unsafe \
    --ignore-extension-versions
```

How to run:
```sh
sh sync-schema.sh
```
