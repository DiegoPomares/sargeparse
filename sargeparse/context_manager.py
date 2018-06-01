
class check_kwargs:  # pylint: disable=invalid-name
    def __init__(self, d):
        self.d = d

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type == KeyError:
            raise KeyError("Key {} not in kwargs".format(exc_value))

        if self.d:
            raise RuntimeError("Unrecognized arguments: '{}'".format(
                "', '".join(map(str, self.d.keys()))
            ))
