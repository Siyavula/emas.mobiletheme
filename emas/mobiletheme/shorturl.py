from zope.interface import Interface
from zope.interface import implements
from upfront.shorturl.storage import ShortURLStorage
from BTrees.OOBTree import OOBTree

class IMobileImageShortURLStorage(Interface):
    """ Marker interface
    """

class MobileImageShortURLStorage(ShortURLStorage):
    """ utility to keep track of shortened urls for mobile images
    """

    implements(IMobileImageShortURLStorage)

    def __init__(self):
        self._map = OOBTree()
        self._reverse_map = OOBTree()

    def add(self, short, target):
        self._map[short] = target
        self._reverse_map[target] = short

    def remove(self, short):
        if self._map.has_key(short):
            target = self.get(short)
            del self._map[short]
            del self._reverse_map[target]

    def get(self, short, default=None):
        return self._map.get(short, default)

    def getkey(self, url, default=None):
        return self._reverse_map.get(url, default)

