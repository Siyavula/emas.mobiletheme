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
        self.question = path.endswith('question')

        if self.dashboard:
            self.prepdashboard()
        elif self.question:
            self.prepquestion()

    def prepdashboard(self):
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

    def prepquestion(self):
        html = lxml.html.fromstring(self.html)

        self.questionscompleted = \
            html.find('.//*[@id="mini-dashboard-question-count"]').text
        self.pointsscored = \
            html.find('.//*[@id="mini-dashboard-points-attained"]').text
        self.pointstotal = \
            html.find('.//*[@id="mini-dashboard-points-total"]').text

        sidepanel = html.find('.//*[@id="side-panel"]')
        sidepanel.getparent().remove(sidepanel)
        self.html = lxml.html.tostring(html)
