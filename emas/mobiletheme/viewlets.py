import logging
import Globals
from redis.connection import ConnectionError
from Acquisition import aq_inner, aq_parent

from zope.component import getMultiAdapter

from zope.interface import Interface

from five import grok
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from gomobiletheme.basic import viewlets as base

from plone.app.layout.nextprevious import view as navbase

from emas.theme.browser.viewlets import PracticeServiceMessagesViewlet as \
    PracticeServiceMessagesViewletBase

from emas.mobiletheme import MessageFactory as _

# Layer for which against all our viewlets are registered
from interfaces import IThemeLayer

logger = logging.getLogger('emas.mobiletheme')

# Viewlets are on all content by default.
grok.context(Interface)

# Use templates directory to search for templates.
grok.templatedir('templates')

# Viewlets are active only when gomobiletheme.basic theme layer is activated
grok.layer(IThemeLayer)

# All viewlets are registered against this dummy viewlet manager
grok.viewletmanager(base.MainViewletManager)

class Logo(base.Logo):
    """ Render site logo with link back to the site root.

    Logo will be automatically resized in the case of
    the mobile screen is very small.
    """

    def getLogoPath(self):
        """ Use Zope 3 resource directory mechanism to pick up the logo file from the static media folder registered by Grok """
        return "++resource++emas.mobiletheme/logo.png"

    def update(self):
        portal_state = base.getView(self.context, self.request,
                                    "plone_portal_state")
        self.nav_root_url = portal_state.navigation_root_url()
        self.portal_url = self.nav_root_url
        self.logo_url = self.nav_root_url + "/" + self.getLogoPath()


class AdditionalHead(base.AdditionalHead):
    """ Include our custom CSS and JS in the theme.
    
    If you want to override the base versions, please consider customizing base.Head instead.
    """
    
    def update(self):
        
        base.AdditionalHead.update(self)
        
        context = self.context.aq_inner
        
        portal_state = getMultiAdapter((context, self.request), name=u"plone_portal_state")
        self.portal_url = portal_state.portal_url()
        
        # Absolute URL refering to the static media folder
        self.resource_url = self.portal_url + "/" + "++resource++emas.mobiletheme"


class Header(base.Header):
    """ Render items at the top of the page.

    This includes

    * Log in, Register links

    * Logo

    * Language switcher
    """

    def update(self):
        portal_state = base.getView(self.context, self.request, 
                                    "plone_portal_state")
        self.anonymous = portal_state.anonymous()

        # Get personal path bar actions
        context_state = base.getView(self.context, self.request,
                                     u'plone_context_state')
        try:
            self.user_actions = context_state.actions("mobile_user")
        except:
            self.user_actions = []
        self.isMxit = self.context.restrictedTraverse('@@mobile_tool').isMXit()


class ActionsHeader(grok.Viewlet):
    """ Override and hook in our own template
    """

    def render(self):
        return

class Back(base.Back):
    """ Make a custom Back button that does not use the canonical object
    """

    def update(self):
        context= self.context.aq_inner
        
        portal_helper = getMultiAdapter((context, self.request), name="plone_portal_state")
        
        parent = aq_parent(context)

        breadcrumbs_view = base.getView(self.context, self.request, 'breadcrumbs_view')
        breadcrumbs = breadcrumbs_view.breadcrumbs()
        
        if (len(breadcrumbs)==1):
            self.backTitle = _(u"Home")
        else:
            if hasattr(parent, "Title"):
                self.backTitle = parent.Title()
            else:
                self.backTitle = _(u"Back")
        
        if hasattr(parent, "absolute_url"):
            self.backUrl = parent.absolute_url()
        else:
            self.backUrl = portal_helper.portal_url()
            
        self.isHome = len(breadcrumbs)==0

class FooterText(base.FooterText):
    """ Override to put our own template into play """

    def update(self):
        super(grok.Viewlet, self).update()
        self.portal_state = base.getView(self.context, self.request,
            "plone_portal_state")
        self.site_url = self.portal_state.navigation_root_url()

class MobileFolderListing(base.MobileFolderListing):
    """ Disable mobile folder listing """

    def update(self):
        """ """
        self.items = []

class SearchBoxTop(base.SearchBoxTop):
    """ Search box top
    """
    
class SearchBoxBottom(base.SearchBoxBottom):
    """ Search box bottom
    """

class NextPreviousViewlet(navbase.NextPreviousViewlet):
    """ Next / Previous links template override
    """
    index = ZopeTwoPageTemplateFile('./templates/nextprevious.pt')

class Head(base.Head):
    """ Override base to customise template
    """

    def apple_icon_url(self):
        """ Get url for apple-touch-icon used on Apple devices.
        """
        return "/".join([self.resource_url(), "apple-touch-icon.png"])
     

class Sections(base.Sections):
    """ Override to customise template
    """

class MobileTracker(grok.Viewlet):
    """ Site visitors tracking code for mobile analytics 
        Redeclared to override template.
    """

    def update(self):
        context = aq_inner(self.context)

        self.portal_state = base.getView(context, self.request,
                                         "plone_portal_state")
        self.site_url = self.portal_state.navigation_root_url()
        self.esi_header = self.request.get('HTTP_X_ESI', None)
        self.is_esi = self.esi_header and True or False

    def img_url(self):
        referer = self.request.getHeader('HTTP_REFERER', '')
        return '/@@tracking_image?referer=%s' % referer

class Messages(base.Messages):
    """ Override base.Messages to customise template.
    """
