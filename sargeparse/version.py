import re
import sys


def python_version(*version_specs):
    pattern = r'(?P<op><|>|<=|>=|==|!=)(?P<maj>\d)((?P<min>\.\d{1,2})(?P<mic>\.\d{1,3})?)?$'
    interpreter_version = sys.version_info.major * 100000
    interpreter_version += sys.version_info.minor * 1000
    interpreter_version += sys.version_info.micro

    for version_spec in version_specs:
        match = re.match(pattern, version_spec)

        if not match:
            raise TypeError("Invalid version specification {}".format(version_spec))

        matches = match.groupdict('.0')

        operator = match.group('op')
        version = int(matches['maj']) * 100000
        version += int(matches['min'][1:]) * 1000
        version += int(matches['mic'][1:])

        # pylint: disable=eval-used
        if not eval("{}{}{}".format(interpreter_version, operator, version)):
            return False

    return True
