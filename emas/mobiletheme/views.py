import urlparse
import logging
import traceback

from five import grok

from zope.component import getUtility
from zope.interface import Interface
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse

from Products.ATContentTypes.interface import IATDocument
from plone.directives import form
from Products.CMFCore.utils import getToolByName

from plone.app.layout.navigation.interfaces import INavigationRoot
from Products.Five import BrowserView
from zExceptions import NotFound

from rhaptos.xmlfile.xmlfile import IXMLFile
from gomobile.mobile.browser.views import MobileTool as BaseMobileTool
from gomobiletheme.basic.viewlets import getView
from interfaces import IThemeLayer

from upfront.shorturl.browser.views import SHORTURLRE

from emas.app.browser.order import Order as BaseOrder
from emas.theme.browser.toc import TableOfContents as BaseTOC
from emas.mobiletheme.shorturl import IMobileImageShortURLStorage
from emas.mobiletheme.tracking.views import log_page_view

LOG = logging.getLogger('mobile.views')

grok.templatedir('templates')
grok.layer(IThemeLayer)

WELCOME_MSG = \
    """
    Read textbooks for free or <a href="@@register">sign up</a>
    and <a href="login">login</a> to Intelligent Practice, for
    unlimited homework practice.
    """

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
        mobile_items = []

        portal_actions = getToolByName(self.context, 'portal_actions')
        actions = portal_actions.listFilteredActionsFor(self.context)

        # don't add the extra links (which includes practice) on MXit
        if not self.context.restrictedTraverse('@@mobile_tool').isMXit():
            if self.has_practise_content(self.context):
                mobile_items.append(self._practice_url())
            for action in actions.get('extra_mobile_links', []):
                tmp_dict = {
                    'Title': action['title'],
                    'absolute_url': action['url'],
                    'css_class': 'toc-link',
                }
                mobile_items.append(tmp_dict)

        if INavigationRoot.providedBy(self.context):
            category = '%s_mobile_links' % self.context.getId()
            for action in actions.get(category, []):
                tmp_dict = {
                    'Title': action['title'],
                    'absolute_url': action['url'],
                    'css_class': 'toc-link',
                }
                mobile_items.append(tmp_dict)
        else:
            mobile_items.extend(self._items(container))
            
        return mobile_items
    
    def welcome_message(self):
        pps = self.context.restrictedTraverse('@@plone_portal_state')
        pmt = getToolByName(self.context, 'portal_membership')
        navroot = pps.navigation_root()
        message = ''
        if pmt.isAnonymousUser() and self.context == navroot:
            message = WELCOME_MSG
        return message
    
    def has_practise_content(self, context):
        retVal = True
        paths_without_practise_content = [
            '/emas/maths/grade-10-mathematical-literacy',
            '/emas/maths/grade-11-mathematical-literacy',
            '/emas/maths/grade-12-mathematical-literacy',
            '/emas/science/lifesciences',
        ]
        path = self.context.getPhysicalPath()
        if path:
            path = '/'.join(path[:4])
            if path in paths_without_practise_content:
                retVal = False

        return retVal
    
    def _practice_url(self):
        title = self.context.Title().lower()
        absolute_url = self.context.absolute_url()
        if INavigationRoot.providedBy(self.context):
            title = 'Practise %s' % self.context.getId().capitalize()
        elif 'grade' in title:
            title = 'Practise this grade'
        elif 'grade' in self.context.aq_parent():
            title = 'Practise this chapter'
        elif absolute_url.endswith('.cnxmlplus'):
            title = 'Practise this section'
        else:
            title = 'Practise'
        
        parts = urlparse.urlparse(self.context.absolute_url())
        newparts = urlparse.ParseResult(parts.scheme,
                                        parts.netloc,
                                        '/@@practice' + parts.path,
                                        parts.params,
                                        parts.query,
                                        parts.fragment)
        url = urlparse.urlunparse(newparts)
        tmp_dict = {
            'Title': title,
            'absolute_url': url,
            'css_class': 'practice-link',
        }
        return tmp_dict

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


class MobileTrackingView(grok.View):
    grok.name('track')
    grok.context(Interface)
    
    def render(self):
        # we don't want to blow up in the face of the user if we restart
        # redis. we log as ERROR so we'll still get a flood ERROR emails
        try:
            log_page_view(self.request, self.context)
        except ConnectionError:
            if not Globals.DevelopmentMode:
                # Zope is in debug mode
                LOG.error(traceback.format_exc())
        return ''
