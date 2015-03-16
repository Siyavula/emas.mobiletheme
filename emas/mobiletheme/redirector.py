from gomobile.mobile.redirector import Redirector as BaseRedirector

class Redirector(BaseRedirector):
    def intercept(self):
        """ We never redirect. """
        return False
