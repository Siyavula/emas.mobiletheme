import os
import hashlib
from five import grok
from zope.interface import Interface
from zope.component import queryUtility
from plone.registry.interfaces import IRegistry
from plone.app.caching.operations.utils import formatDateTime
from plone.app.caching.operations.utils import getExpiration

from upfront.analyticsqueue.factory import get_q
from upfront.analyticsqueue.googlequeue import GAQueueProcessor

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

        response = self.request.RESPONSE
        # never cache this image
        if response.getHeader('Last-Modified'):
            del response.headers['last-modified']
        response.setHeader('Expires', formatDateTime(getExpiration(0)))
        response.setHeader('Cache-Control',
                           'max-age=0, must-revalidate, private')
        response.setHeader('Content-Type', 'image/png')
        response.setHeader('Content-Length', len(img))
        response.write(img)
    
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
        
        for key in ['REMOTE_ADDR', 'HTTP_X_FORWARDED_FOR', 'HTTP_USER_AGENT',
                    'HTTP_ACCEPT_LANGUAGE', 'AUTHENTICATED_USER',]:
            value = self.request.get(key)
            if hasattr(value, 'aq_inner'):
                value = self.request.get(key).aq_base
                if key == 'AUTHENTICATED_USER':
                    value = value.getId()
            if value:
                entry[key] = value

        port = getattr(settings, 'redis_port', 6379)
        entry['redis-port'] = port
        gaq = get_q(q_name='google_analytics_q', port=port)
        gaq.enqueue(GAQueueProcessor.deliver, entry)
