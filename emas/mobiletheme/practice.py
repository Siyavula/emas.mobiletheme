import lxml
import urlparse

from zope.interface import Interface
from Products.CMFCore.utils import getToolByName

from pas.plugins.mxit.plugin import member_id
from pas.plugins.mxit.plugin import USER_ID_TOKEN

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from emas.theme.browser.practice import Practice as BasePractice

from interfaces import IThemeLayer

PRACTICE_URL = '@@practice'


class MobilePractice(BasePractice):
    """
        Custom view for mobile practice service
    """
    # mobile practice expiry warning period is only 7 days as per Siyavula team
    # request.
    NUM_DAYS = 7

    index = ViewPageTemplateFile('templates/practice.pt')
    

    def isPracticeService(self):
        """
        """
        path = self.context.getPhysicalPath()
        return PRACTICE_URL in path.split('/')

    def update(self):
        self.view_is_handled_by_monassis = True
        self.cleanup()

    def cleanup(self):
        """ Remove all unnecessary or problematic pieces of html from the local
            'html' attribute. It has an internal list of xpath statements used
            to find and remove the relevant html elements.

            We use this to do final cleanup before returning the html to the
            requesting client.
        """
        ''' # NOTE: Removed since this doesn't do anything anymore
        html = lxml.html.fromstring(self.html)

        elements_to_remove = [
        ]
        for xpath in elements_to_remove:
            element = html.find(xpath)
            if element:
                element.getparent().remove(element)

        self.html = lxml.html.tostring(html)
        '''
        pass
