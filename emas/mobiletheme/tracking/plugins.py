from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from collective.googleanalytics.tracking.plugins \
    import AnalyticsBaseTrackingPlugin

class AnalyticsMobileTrackingPlugin(AnalyticsBaseTrackingPlugin):
    """
    A tracking plugin for devices that cannot handle javascript.
    """
    
    __call__ = ViewPageTemplateFile('tracking.pt')
