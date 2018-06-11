from collections import Counter


class ArgumentGroup:
    def __init__(self, title, *, description):
        self.title = title
        self.description = description
        self.arguments = []


class MutualExclussionGroup:
    def __init__(self):
        self.arguments = []

    def is_required(self):
        required = Counter((arg.validate_schema({'required': True}) for arg in self.arguments))

        if len(required) > 1:
            msg = "'required' property in all mutex group arguments' must have the same value (True or False)"
            raise ValueError(msg)

        return required.most_common(1)[0][0]
