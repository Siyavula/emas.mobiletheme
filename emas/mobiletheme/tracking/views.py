from pyga.requests import Tracker, Page, Session, Visitor

from five import grok
from zope.interface import Interface
from zope.component import queryUtility
from plone.registry.interfaces import IRegistry

from emas.mobiletheme.interfaces import IThemeLayer
from emas.mobiletheme.interfaces import IEmasMobileThemeSettings

grok.layer(IThemeLayer)

class Tracking_Image(grok.View):
    """ We use this as a hook to do server side Google Analytics tracking.
    """
    grok.context(Interface)
    grok.require('zope2.View')

        
    def render(self):
        # Return an empty string, since this is a 'no-user-interface' view.
        return ''
    
    def update(self):
        # get the nav root
        pps = self.context.restrictedTraverse('@@plone_portal_state')
        navroot = pps.navigation_root()

        # get the subject
        subject = navroot.getId()

        # get the GA code from the registry
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IEmasMobileThemeSettings)
        gacode = getattr(settings, '%s_gacode' %subject)
        if not gacode:
            return

        # make the call to google analytics
        tracker = Tracker(gacode, 'everything%s.co.za' %subject)
        visitor = Visitor()
        visitor.ip_address = self.request.getClientAddr()
        session = Session()
        # drop the science or maths from the path
        path_elements = ('',) + self.context.getPhysicalPath()[2:]
        page = Page('/'.join(path_elements))
        tracker.track_pageview(page, session, visitor)
