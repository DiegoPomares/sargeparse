import os
import sys

import multiprocessing
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

import sargeparse as package


class PyTest(TestCommand):
    user_options = [
        ('no-lint', 'L', "Skip file linting"),
        ('no-coverage', 'C', "Skip coverage report"),
        ('test-expression=', 'k', 'Only run tests which match the given substring expression'),
        ('env-file=', 'e', 'Environment file to load')
    ]

    # pylint: disable=attribute-defined-outside-init
    def initialize_options(self):
        super().initialize_options()

        self.pytest_args = [
            '--verbose',
        ]
        self.lint_args = [
            '--flake8',
            '--pylint',
            '--pylint-jobs={}'.format(multiprocessing.cpu_count())
        ]
        self.coverage_args = [
            '--cov={}'.format(package.__name__),
            '--cov-report=term-missing',
            '--cov-report=xml:reports/coverage.xml',
            '--cov-report=html:reports/coverage',
        ]

        self.no_lint = False
        self.no_coverage = False
        self.test_expression = False
        self.env_file = None

    def finalize_options(self):
        super().finalize_options()

        if self.no_lint is False:
            self.pytest_args.extend(self.lint_args)

        if self.no_coverage is False:
            self.pytest_args.extend(self.coverage_args)

        if self.test_expression:
            self.pytest_args.extend(['-k', self.test_expression])

        if self.env_file:
            set_environment(self.env_file)

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


def set_environment(path):
    with open(path) as f:
        for line in f:
            env_vars = [line.lstrip().rstrip('\n') for line in f]
            env_vars = [line for line in env_vars if line and not line.startswith('#')]

    for line in env_vars:
        name, value = line.split('=', 2)
        os.environ[name] = value


def get_requirements(path):
    script_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(script_path, path)

    with open(file_path) as f:
        requires = [line.split('#', 2)[0].strip() for line in f]
        requires = [line for line in requires if line]

    return requires


# install_reqs = get_requirements("requirements/requirements.txt")
test_reqs = get_requirements("requirements/test_requirements.txt")


setup(
    python_requires='>=3.4',
    name=package.__name__,
    description=package.__description__,
    author=package.__author__,
    author_email=package.__author_email__,
    url=package.__url__,
    version=package.__version__,
    packages=find_packages(),
    include_package_data=True,
    # install_requires=install_reqs,
    tests_require=test_reqs,
    cmdclass={'test': PyTest},
    zip_safe=False,
)
