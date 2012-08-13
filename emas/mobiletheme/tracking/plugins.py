from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from collective.googleanalytics.tracking.plugins \
    import AnalyticsBaseTrackingPlugin
import pyga

class AnalyticsMobileTrackingPlugin(AnalyticsBaseTrackingPlugin):
    """
    A tracking plugin for devices that cannot handle javascript.
    """
    
    def __call__(self):
        return ViewPageTemplateFile('mobile.pt')
