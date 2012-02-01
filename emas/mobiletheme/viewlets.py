"""

   This module contains all viewlet overrides and new viewlets
   for the mobile theme. 
   
   For more information about how to deal with Grok viewlets see
   
   * http://vincentfretin.ecreall.com/articles/creating-a-viewlet-with-grok
   
   * http://grok.zope.org/doc/current/reference/directives.html

"""

__author__ = " <>"
__docformat__ = "epytext"
__license__ = "GPL"

from zope.component import getMultiAdapter

from zope.interface import Interface

from five import grok

from gomobiletheme.basic import viewlets as base
from gomobile.mobile.interfaces import IMobileImageProcessor

from emas.mobiletheme import MessageFactory as _

# Layer for which against all our viewlets are registered
from interfaces import IThemeLayer

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

