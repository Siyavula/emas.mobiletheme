from zope.interface import Interface
from Products.CMFCore.utils import getToolByName

from pas.plugins.mxit.plugin import member_id
from pas.plugins.mxit.plugin import USER_ID_TOKEN

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from emas.theme.browser.practice import Practice as BasePractice

from interfaces import IThemeLayer

PRACTICE_URL = '@@practice'


class MXitPractice(BasePractice):
    """
        Custom view for mobile practice service
    """

    index = ViewPageTemplateFile('templates/practice.pt')
    

    def isPracticeService(self):
        """
        """
        path = self.context.getPhysicalPath()
        return PRACTICE_URL in path.split('/')
