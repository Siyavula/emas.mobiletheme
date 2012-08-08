from zope.interface import implements
from zope.interface import Interface

from zope.component import adapts
from plone.app.caching.interfaces import IETagValue

class UserAgent(object):
    """ The ``useragent`` etag component, returning the value of the
        HTTP_USER_AGENT request key.
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        return self.request.get('HTTP_USER_AGENT', '')


class MXit(object):
    """ The ``mxit`` etag component, returning the request is from MXit
        or not.
    """

    implements(IETagValue)
    adapts(Interface, Interface)

    def __init__(self, published, request):
        self.published = published
        self.request = request

    def __call__(self):
        isMXit = "MXit WebBot" in self.request.get('HTTP_USER_AGENT', '')
        return isMXit and 'MXit' or ''
