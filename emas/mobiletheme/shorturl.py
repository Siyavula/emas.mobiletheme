from zope.interface import Interface
from upfront.shorturl.storage import ShortURLStorage

class IMobileImageShortURLStorage(Interface):
    """ Marker interface
    """

class MobileImageShortURLStorage(ShortURLStorage)
    """ utility to keep track of shortened urls for mobile images
    """

    implements(IMobileImageShortURLStorage)
