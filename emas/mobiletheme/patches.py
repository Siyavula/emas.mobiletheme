import copy
import traceback

import PIL
import urllib2
import urlparse
import cStringIO

from Acquisition import aq_base
from Acquisition import aq_inner
from ZPublisher import NotFound
from zExceptions import Unauthorized
from zope.app.component.hooks import getSite

from lxml.etree import ParserError 
from lxml.html import fromstring, tostring

from plone.app.layout.navigation.root import getNavigationRootObject
from plone.app.redirector.storage import RedirectionStorage
from mobile.htmlprocessing.transformers.basic import BasicCleaner

from gomobile.mobile.browser.imageprocessor import MobileImageProcessor
from gomobile.mobile.browser.imageprocessor import safe_width
from gomobile.mobile.browser.imageprocessor import safe_height
from gomobile.imageinfo.utilities import ImageInfoUtility
from mobile.sniffer import utilities as snifferutils
from mobile.htmlprocessing.transformers.imageresizer import ImageResizer

from logging import getLogger
LOG = getLogger('MobileTheme: patches')

# increase dimensions that are safe slightly
safe_width = 1024
safe_height = 1024

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


def process_img(self, doc, el):
    """ Process <img> tag in the source docu,ent.
    """
    self.add_alt_tags(el)
    
    src = el.attrib.get("src", None)
    if src:
        # catch exceptions to ensure broken images don't
        # prevent the page from rendering 
        try:
            el.attrib["src"] = self.rewrite(src)
        except:
            # blank alt text
            del el.attrib["alt"]
            el.attrib["src"] = src
            site = getSite()
            error = ['URL: %s' % site.REQUEST.URL,
                     'Referer: %s' % site.REQUEST.HTTP_REFERER,
                     'User Agent: %s' % site.REQUEST.get('HTTP_USER_AGENT', 
                                                         'Unknown'),
                     traceback.format_exc()]
            error = '\n'.join(error)
            LOG.error(error)
        
        # Remove explicit width declarations
        if "width" in el.attrib:            
            del el.attrib["width"]

        if "height" in el.attrib:            
            del el.attrib["height"]
        
    if self.needs_clearing(el):
        self.clear_floats(el)
    
    self.add_processed_class(el)

ImageResizer.process_img = process_img


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
    # check if the image is inside the Plone site
    site = getSite()
    if url.startswith(site.absolute_url()) and not '@@practice' in url:
        image_url_parts = urlparse.urlparse(url)
        # we strip the leading slash since we are traversing from the
        # site root
        path = image_url_parts.path[1:]

        # get the navigation root which might be different to the site
        context = aq_inner(site.REQUEST.PARENTS[0])
        navroot = getNavigationRootObject(context, site)

        # check for ImageScaling view
        if '/@@images/' in path:
            path, name = path.split('/@@images/')
            scalingview = navroot.restrictedTraverse(path + '/@@images/')
            imagescale = scalingview.publishTraverse(site.REQUEST, name)
            io = cStringIO.StringIO(imagescale.data)
        else:
            image = navroot.restrictedTraverse(path)
            io = cStringIO.StringIO(image.getImage().data)
        return PIL.Image.open(io)
    else:
        req = urllib2.Request(url)
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError:
            raise NotFound('The URL:%s could not be found' %url)
        data = response.read()
        io = cStringIO.StringIO(data)
        return PIL.Image.open(io)

ImageInfoUtility.downloadImage = downloadImage
