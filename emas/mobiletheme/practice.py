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
        pps = self.context.restrictedTraverse('@@plone_portal_state')
        portal_url = pps.portal_url()
        self.dashboard_url = '%s/@@practice/dashboard' % portal_url
        self.reportproblem_url = \
            '%s/@@practice/user-feedback-mobi' % portal_url
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

        # copy the how-to-write content for use in the template
        self.howtowrite = ''
        for elem in html.findall('.//*[@id="how-to-write-open"]/*'):
            self.howtowrite += lxml.html.tostring(elem)

        # remove div in practice service html
        div = html.find('.//*[@id="how-to-write"]')
        if div:
            div.getparent().remove(div)

        # remove please wait image
        img = html.find('.//*[@id="checking_please_wait"]')
        if img is not None:
            img.getparent().remove(img)

        # remove onclick javascript from submit buttons
        for submit in html.findall('.//input[@type="submit"]'):
            submit.attrib.pop('onclick', None)

        # strip &nbsp; between buttons
        navbuttons = html.find('.//*[@id="nav-buttons"]')
        if navbuttons is not None:
            navbuttons.clear()
            navbuttons.extend(lxml.html.fromstring(
                """<button type="submit" name="retry">Try another question """
                """like this</button><button type="submit" name="nextPage">"""
                """Go to next question</button>"""))

        sidepanel = html.find('.//*[@id="side-panel"]')
        sidepanel.getparent().remove(sidepanel)
        self.html = lxml.html.tostring(html)
