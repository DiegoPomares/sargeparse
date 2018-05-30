import re
import sys


def python_version(*version_specs):
    pattern = r'(?P<op><|>|<=|>=|==|!=)(?P<maj>\d)\.?(?P<min>\d{0,2})\.?(?P<mic>\d{0,3})'
    interpreter_version = sys.version_info.major * 100000
    interpreter_version += sys.version_info.minor * 1000
    interpreter_version += sys.version_info.micro

    for version_spec in version_specs:
        match = re.match(pattern, version_spec)

        if not match:
            raise TypeError("Invalid version specification {}".format(version_spec))

        operator = match.group('op')
        version = int(match.group('maj')) * 100000
        version += int(match.group('min') or 0) * 1000
        version += int(match.group('mic') or 0)

        # pylint: disable=eval-used
        if not eval("{}{}{}".format(interpreter_version, operator, version)):
            return False

    return True
