

class CheckKwargs:
    def __init__(self, d):
        self.d = d

    def __enter__(self):  # pylint: disable=invalid-name
        pass

    def __exit__(self, exc_type, exc_value, traceback):  # pylint: disable=invalid-name
        if exc_type == KeyError:
            raise KeyError("Key '{}' not in kwargs".format(exc_value))

        if self.d:
            raise RuntimeError("Unrecognized arguments: '{}'".format(
                "', '".join(map(str, self.d.keys()))
            ))
