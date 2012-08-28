import os
import hashlib
from five import grok
from zope.interface import Interface
from zope.component import queryUtility
from plone.registry.interfaces import IRegistry

from upfront.analyticsqueue.factory import get_q
from upfront.analyticsqueue.googlequeue import GoogleQueue 

from emas.mobiletheme.interfaces import IThemeLayer
from emas.mobiletheme.interfaces import IEmasMobileThemeSettings

grok.layer(IThemeLayer)

dirname = os.path.dirname(__file__)

class Tracking_Image(grok.View):
    """ We use this as a hook to do server side Google Analytics tracking.
    """
    grok.context(Interface)
    grok.require('zope2.View')

        
    def render(self):
        """ Return a transparent 1x1 pixel png image
        """
        img = open(os.path.join(dirname, 'tracking.png'), 'rb')
        img = img.read()

        self.request.RESPONSE.setHeader('Content-Type', 'image/png')
        self.request.RESPONSE.setHeader('Content-Length', len(img))
        self.request.RESPONSE.write(img)
    
    def update(self):
        entry = {}

        # get the nav root
        pps = self.context.restrictedTraverse('@@plone_portal_state')
        navroot = pps.navigation_root()
        # get the subject
        subject = navroot.getId()
        entry['subject'] = subject
        entry['domain'] = 'everything%s.co.za' %subject

        # get the GA code from the registry
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IEmasMobileThemeSettings)

        gacode = getattr(settings, '%s_gacode' %subject, None)
        if not gacode:
            return
        entry['gacode'] = gacode

        entry['referer'] = self.request.getHeader('HTTP_REFERER')

        entry['title'] = self.context.Title()

        remote_address = self.request.getHeader(
                'HTTP_X_FORWARDED_FOR', self.request.getHeader('REMOTE_ADDR'))
        entry['remote_address'] = remote_address
        entry['user_agent'] = self.request.getHeader('HTTP_USER_AGENT')

        # drop the science or maths from the path
        path = self.context.getPhysicalPath()
        path_elements = ('',) + path[3:]
        path = '/'.join(path_elements)
        entry['path'] = path

        locale = getattr(self.request, 'locale')
        entry['locale'] = locale.getLocaleID()

        user = self.request.get('AUTHENTICATED_USER')
        userid = user.getId()
        if userid:
            unique_id = int(hashlib.md5(userid).hexdigest(), 16)
        else: 
            unique_id = int(hashlib.md5(remote_address).hexdigest(), 16)
        entry['unique_id'] = unique_id

        port = getattr(settings, 'redis_port', 6379)
        gaq = get_q(q_name='google_analytics_q', port=port)
        gaq.enqueue(GoogleQueue.deliver, entry)
