import os
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

import sargeparse as package


class CustomTestCommand(TestCommand):
    def run_tests(self):
        print("Error: Use script/test-local or scripy/citest for running tests")
        sys.exit(2)


def get_requirements(path):
    script_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(script_path, path)

    with open(file_path) as f:
        requires = [line.split('#', 2)[0].strip() for line in f]
        requires = [line for line in requires if line]

    return requires


install_reqs = get_requirements("requirements/requirements.txt")
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
    install_requires=install_reqs,
    cmdclass={'test': CustomTestCommand},
    zip_safe=False,
)
