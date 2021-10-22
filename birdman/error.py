class ParserUpdateRequiredError(Exception):
    def __init__(self, name, msg):
        super(ParserUpdateRequiredError, self).__init__("%s | %s"%(name, msg))


class UnknownError(Exception):
    def __init__(self, name, msg):
        super(UnknownError, self).__init__("%s | %s"%(name, "Unknown error. Generate issues in our Github repository for support."))