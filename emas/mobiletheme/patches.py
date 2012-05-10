import copy

import PIL
import urllib2
import cStringIO

from ZPublisher import NotFound
from lxml.etree import ParserError 
from lxml.html import fromstring, tostring
from zope.app.component.hooks import getSite
from plone.app.redirector.storage import RedirectionStorage
from mobile.htmlprocessing.transformers.basic import BasicCleaner
from gomobile.mobile.browser.imageprocessor import MobileImageProcessor
from gomobile.imageinfo.utilities import ImageInfoUtility

from Acquisition import aq_base

def process(self, html):
    """ patched method to not encode result when converting back to
        string since this breaks valid html entities.
    """
    
    # Check whether we got ready parse-tree or string input
    result_type = type(html)

    
    if isinstance(html, basestring):
        try:
            doc = fromstring(html)
        except ParserError:
            # Can't handle malformed doc, empty doc, etc.
            return html
    else:
        doc = copy.deepcopy(html)

    # Run XHTML MP specific cleaning
    self.clean_mobile(doc)

    # Run normal cleaning
    if not self.trusted:
        self(doc)

    return tostring(doc, method="xml")

BasicCleaner.process = process


def mapURL(self, url):
    """ patched to traverse relative urls from folder if content is not
        folderish
    """

    rs = RedirectionStorage()
    if rs.has_path(url):
        url = rs.get(url)


    # Make sure we are traversing the context chain without view object messing up things
    context = self.context.aq_inner

    if url.startswith("http://") or url.startswith("https://"):
        # external URL
        url = url
    elif "++resource" in url:
        # Zope 3 resources are mapped to the site root
        url = url
    else:
        # Map the context path to the site root
        if url.startswith("/"):
            # Pass URL to resizer view relocated to the site root

            url = url[1:]
        else:
            # The URL is relative to the context path
            # Map URL to be relative to the site root

            site = getSite()

            # if isPrincipiaFolderish is False
            folderish = getattr(aq_base(context), 'isPrincipiaFolderish',
                                False)
            try:
                if folderish:
                    imageObject = context.unrestrictedTraverse(url)
                else:
                    imageObject = context.aq_parent.unrestrictedTraverse(url)
            except Unauthorized:
                # The parent folder might be private and the image public,
                # in which case we should be able to view the image after all.
                parent_path = '/'.join(url.split('/')[:-1])
                image_path = url.split('/')[-1]
                parent = site.unrestrictedTraverse(parent_path)
                imageObject = parent.restrictedTraverse(image_path)

            if ("FileResource" in imageObject.__class__.__name__):
                # Five mangling compatible way to detect image urls pointing to the resource directory
                # ...but this should not happen if images are accessed using ++resource syntax
                return url
            elif hasattr(imageObject, "getPhysicalPath"):
                physicalPath = imageObject.getPhysicalPath() # This path is relative to Zope Application server root
#
                virtualPath = self.request.physicalPathToVirtualPath(physicalPath)

                # TODO: Assume Plone site is Zope app top level root object here

                # empty root node, site node
                assert len(physicalPath) > 2

                virtualPath = physicalPath[2:]

                virtualPath = self.removeScale(virtualPath)

                url = "/".join(virtualPath)
            else:
                raise RuntimeError("Unknown traversable image object:" + str(imageObject))
    return url

MobileImageProcessor.mapURL = mapURL

def downloadImage(self, url):
    """ Get remote image data and store.
    """
    req = urllib2.Request(url)
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError:
        raise NotFound('The URL:%s could not be found' %url)
    data = response.read()
    io = cStringIO.StringIO(data)
    return PIL.Image.open(io)

ImageInfoUtility.downloadImage = downloadImage
