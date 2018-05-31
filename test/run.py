import os
import multiprocessing
import argparse

script_path = os.path.dirname(os.path.realpath(__file__))
os.chdir('{}/..'.format(script_path))

PACKAGE = 'sargeparse'

arg_groups = {
    'default': [
        '--verbose',
        '--confcutdir={}'.format(script_path),
    ],
    'lint': [
        '--flake8',
        '--pylint',
        '--pylint-jobs={}'.format(multiprocessing.cpu_count()),
    ],
    'coverage': [
        '--cov={}'.format(PACKAGE),
        '--cov-report=term-missing',
        '--cov-report=xml:reports/coverage.xml',
        '--cov-report=html:reports/coverage',
    ],
}


def set_environment(path):
    with open(path) as f:
        for line in f:
            env_vars = [line.lstrip().rstrip('\n') for line in f]
            env_vars = [line for line in env_vars if line and not line.startswith('#')]

    for line in env_vars:
        name, value = line.split('=', 2)
        os.environ[name] = value


parser = argparse.ArgumentParser()
parser.add_argument('-L', '--no-lint', action='store_false', default=True,
                    dest='lint', help="Skip file linting")
parser.add_argument('-C', '--no-cov', action='store_false', default=True,
                    dest='coverage', help="Skip coverage report")
parser.add_argument('-e', '--env-file', nargs=1,
                    help="File to load environment variables from")

args, rest = parser.parse_known_args()

pylint_args = ['pytest']
pylint_args.extend(arg_groups['default'])

if args.lint:
    pylint_args.extend(arg_groups['lint'])

if args.coverage:
    pylint_args.extend(arg_groups['coverage'])
else:
    pylint_args.append('--no-cov')

pylint_args.extend(rest)

if args.env_file:
    set_environment(args.env_file)

os.execvp(pylint_args[0], pylint_args)
