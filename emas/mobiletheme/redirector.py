class Redirector(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def intercept(self):
        """ We never redirect. """
        return False
