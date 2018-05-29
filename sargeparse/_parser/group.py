class ArgumentGroup:
    def __init__(self, title, *, description):
        self.title = title
        self.description = description
        self.arguments = []


class MutualExclussionGroup:
    def __init__(self):
        self.arguments = []

    def is_required(self):
        for argument in self.arguments:
            if not argument.validate_schema({'required': False}):
                return True

        return False
