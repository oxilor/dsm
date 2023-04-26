from os import getcwd
from os.path import join
from sys import argv
from argparse import ArgumentParser, Namespace
from migration import execute_sql, get_migration

commandHelpMap={
  'diff': 'Print DDL statements that should be executed to reach the desired schema.',
  'apply': 'Generate DDL statements and execute them after confirmation.',
  'save': 'Save DDL statements into a file.',
  'execute': 'Execute SQL statements from a file.',
}

class color:
  BLUE = '\033[94m'
  GREEN = '\033[92m'
  RED = '\033[91m'
  END = '\033[0m'

class DsmToolCli:
  def __init__(self) -> None:
    usage='dsm <command> [<args>]\n\nAvailable commands:\n'
    for command in commandHelpMap:
      usage += '  %-10s' '%s\n' % (command, commandHelpMap[command])

    parser = ArgumentParser(
      description='Declarative schema management tool.',
      usage=usage,
    )
    parser.add_argument('command', help='Subcommand to run.')

    args = parser.parse_args(argv[1:2])
    if args.command not in commandHelpMap or not hasattr(self, args.command):
      print('Incorrect command.')
      parser.print_help()
      exit(1)

    getattr(self, args.command)()

  def diff(self) -> None:
    parser = ArgumentParser(description=commandHelpMap['diff'])
    args = self.parse_diff_arguments(parser)
    statements = get_migration(args)
    if statements:
      print(statements)

  def apply(self) -> None:
    parser = ArgumentParser(description=commandHelpMap['apply'])
    parser.add_argument(
      '--no-confirmation',
      dest='confirmation',
      action='store_false',
      help='Execute the generated DDL statements without confirmation.',
    )

    args = self.parse_diff_arguments(parser)
    statements = get_migration(args)

    if statements:
      if args.confirmation:
        print('%sPending changes:%s' % (color.BLUE, color.END), end='\n\n')
        print(statements, end='\n\n')
        valid = {'y': True, 'n': False}
        while True:
          print('%sDo you want to execute them? [y/n] %s' % (color.BLUE, color.END), end='')
          choice = input().lower()
          if choice in valid:
            if valid[choice]:
              execute_sql(args.uri, statements)
              print('%sDone.%s' % (color.GREEN, color.END))
              exit(0)
            else:
              print('%sNot confirmed.%s' % (color.RED, color.END))
              exit(1)
          else:
            print('Please respond with "y" or "n".')
      else:
        execute_sql(args.uri, statements)
        print('%sDone.%s' % (color.GREEN, color.END))
    else:
      self.print_no_changes()

  def save(self) -> None:
    parser = ArgumentParser(description=commandHelpMap['save'])
    parser.add_argument(
      '--file',
      dest='file',
      default='/schema/pending.sql',
      help='The path to the file where the generated DDL statements will be stored.',
    )

    args = self.parse_diff_arguments(parser)
    statements = get_migration(args)

    if statements:
      file_path = join(getcwd(), args.file)
      with open(file_path, 'w') as f:
        f.write(statements)
        print('%sSaved the file "%s" with the following changes:%s' % (color.GREEN, file_path, color.END), end='\n\n')
        print(statements)
    else:
      self.print_no_changes()

  def execute(self) -> None:
    parser = ArgumentParser(description=commandHelpMap['execute'])
    parser.add_argument(
      '--uri',
      dest='uri',
      default=None,
      required=True,
      help='The connection URI to the target database.',
    )
    parser.add_argument(
      '--file',
      dest='file',
      default='/schema/pending.sql',
      help='The path to the file with SQL statements that should be executed to reach the desired schema.',
    )

    args = parser.parse_args(argv[2:])
    file_path = join(getcwd(), args.file)

    with open(file_path, 'r') as f:
      statements = f.read().strip()
      execute_sql(args.uri, statements)
      print('%sThe following changes were made:%s' % (color.GREEN, color.END), end='\n\n')
      print(statements)

  def parse_diff_arguments(self, parser: ArgumentParser) -> Namespace:
    parser.add_argument(
      '--uri',
      dest='uri',
      default=None,
      required=True,
      help='The connection URI to the target database.',
    )
    parser.add_argument(
      '--temp-uri',
      dest='temp_uri',
      default=None,
      required=True,
      help='The connection URI to the temporary database (must be empty).',
    )
    parser.add_argument(
      '--to',
      dest='to',
      default=None,
      required=True,
      action='append',
      help='The path to a file or directory with multiple files with your schema (e.g. one file is one table).',
    )
    parser.add_argument(
      '--unsafe',
      dest='unsafe',
      action='store_true',
      help="Don't throw an exception if DROP statements are generated.",
    )
    parser.add_argument(
      '--schema',
      dest='schema',
      default=None,
      help='Generate DDL statements only for the specified schema.',
    )
    parser.add_argument(
      '--exclude-schema',
      dest='exclude_schema',
      default=None,
      help='Generate DDL statements for all schemas except the specified one.',
    )
    parser.add_argument(
      '--ignore-extension-versions',
      dest='ignore_extension_versions',
      action='store_true',
      help='Ignore versions when comparing extensions.',
    )
    parser.add_argument(
      '--with-privileges',
      dest='with_privileges',
      action='store_true',
      help='Include permission-related change statements (GRANT, REVOKE).',
    )
    return parser.parse_args(argv[2:])

  def print_no_changes(self) -> None:
    print('%sNo changes.%s' % (color.GREEN, color.END))


if __name__ == '__main__':
  DsmToolCli()
