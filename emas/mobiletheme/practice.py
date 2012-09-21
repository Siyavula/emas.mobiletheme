import lxml

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

    index = ViewPageTemplateFile('templates/practice.pt')
    

    def isPracticeService(self):
        """
        """
        path = self.context.getPhysicalPath()
        return PRACTICE_URL in path.split('/')

    def update(self):
        path = self.request.get_header('PATH_INFO')
        self.dashboard = path.endswith('dashboard')

        if not self.dashboard:
            return

        html = lxml.html.fromstring(self.html)

        self.booktitle = html.find('.//*[@id="dashboard-book-title"]').text
        sections = []
        for section in html.findall(
                './/*[@class="dashboard-section-title-1"]/a'):
            sections.append({
                'href': section.get('href'),
                'alttitle': "Click to practice %s" % section.text,
                'title': section.text
                }
            )
        self.sections = sections
