import urlparse

from five import grok

from zope.component import getUtility
from zope.interface import Interface
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse

from Products.ATContentTypes.interface import IATDocument
from plone.directives import form
from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView

from rhaptos.xmlfile.xmlfile import IXMLFile
from gomobile.mobile.browser.views import MobileTool as BaseMobileTool
from gomobiletheme.basic.viewlets import getView
from interfaces import IThemeLayer

from upfront.shorturl.browser.views import SHORTURLRE

from emas.app.browser.order import Order as BaseOrder
from emas.theme.browser.toc import TableOfContents as BaseTOC
from emas.mobiletheme.shorturl import IMobileImageShortURLStorage

grok.templatedir('templates')
grok.layer(IThemeLayer)

MXIT_MARKER = 'MXit'
MXIT_AGENT_HEADER = 'HTTP_USER_AGENT'

class XMLFile(form.DisplayForm):
    grok.context(IXMLFile)
    grok.require('zope2.View')
    grok.name('mobilexmlfile')
    grok.template('xmlfile')


class Document(form.DisplayForm):
    grok.context(IATDocument)
    grok.require('zope2.View')
    grok.name('mobiledocumentdefault')
    grok.template('document')

    def update(self):
        self.w['body'] = self.context.getText()


class MobileTool(BaseMobileTool):
    """ Specialise check for low end phones
    """

    def isLowEndPhone(self):
        """ override to check for Mxit """
        if self.isMXit():
            return True
        else:
            return super(MobileTool, self).isLowEndPhone()

    def isMXit(self):
        header = self.request.get(MXIT_AGENT_HEADER, '').lower()
        return MXIT_MARKER.lower() in header


class Order(BaseOrder):
    """ Specialised to accommodate mobile workflow and template and to add
        security constraint.
    """
    grok.require('cmf.SetOwnProperties')
    def update(self):
        return super(Order, self).update()


class TableOfContents(BaseTOC):
    """ Helper methods and a template that renders only the table of contents.
    """
    def getContentItems(self, container=None):
        """ Add the actions specified in the portal_actions category,
            'extra_mobile_links'.
        """
        items = super(TableOfContents, self).getContentItems()
        portal_actions = getToolByName(self.context, 'portal_actions')
        actions = portal_actions.listFilteredActionsFor(self.context)
        mobile_items = []

        # don't add the extra links (which includes practice) on MXit
        if not self.context.restrictedTraverse('@@mobile_tool').isMXit():
            for action in actions.get('extra_mobile_links', []):
                tmp_dict = {
                    'Title': action['title'],
                    'absolute_url': action['url'],
                    'css_class': 'practice-link',
                }
                mobile_items.append(tmp_dict)
        mobile_items.extend(items)
        return mobile_items


class ShortImageURL(BrowserView):
    """ 
    """
    implements(IPublishTraverse)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.traversecode = None

    def lookup(self, code):
        if SHORTURLRE.match(code) is None:
            return None

        storage = getUtility(IMobileImageShortURLStorage)
        return storage.get(code, None)

    def publishTraverse(self, request, name):
        """ This method is called if someone appends the shortcode to the end
            of the url. To prevent the silliness of multiple parts being
            appended, we raise NotFound if we already have one. """
        if self.traversecode is None:
            self.traversecode = name
        else:
            raise NotFound(name)
        return self

    def __call__(self):
        shortcode = self.request.get('shortcode', None) or self.traversecode
        error = None
        if shortcode:
            target = self.lookup(shortcode)
            if target is not None:
                urlparts = urlparse.urlparse(target)
                qdict = urlparse.parse_qs(urlparts.query)
                key = qdict.get('key')[0]
                self.request.set('key', key)
                mobile_image = getView(self.context, self.request,
                                       "mobile_image")
                return mobile_image() 

        raise NotFound()
