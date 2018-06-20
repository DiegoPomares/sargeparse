class ArgumentGroup:
    def __init__(self, title, *, description):
        self.title = title
        self.description = description
        self.arguments = []


class MutualExclussionGroup:
    def __init__(self, *, required):
        self.arguments = []
        self.required = required
