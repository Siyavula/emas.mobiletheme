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
        self.expand_chapter_url = '%s/@@practice/dashboard/chapter-' % portal_url
        path = self.request.get_header('PATH_INFO')
        self.dashboard = 'dashboard' in path
        self.selectgrade = path.endswith('select_grade')
        self.question = path.endswith('question')
        self.reportproblem = path.endswith('user-feedback-mobi') or \
                             path.endswith('user-feedback-mobi-success')

        if self.dashboard:
            self.prepdashboard()
        elif self.selectgrade:
            self.prepselectgrade()
        elif self.question:
            self.prepquestion()
        elif self.reportproblem:
            self.prep_reportproblem()
        
        # do final cleanup on html
        self.cleanup()

    def prepdashboard(self):
        html = lxml.html.fromstring(self.html)

        # Subject, grade
        self.booktitle = html.find('.//*[@id="dashboard-book-title"]').text

        # Link to page for changing your grade (if available)
        element = html.find('.//*[@id="dashboard-change-grade"]')
        if element is not None:
            element.tag = 'p'
            self.change_grade = lxml.html.tostring(element)
        else:
            self.change_grade = ''

        # Welcome message
        self.message = html.find('.//*[@id="dashboard-message"]')

        sections = []
        for element in html.findall('.//*[@class]'):
            classes = element.get('class').split()
            if 'dashboard-section-title-1' in classes:
                anchorElement = element.find('a')
                sections.append({
                    'href': anchorElement.get('href'),
                    'alttitle': "Click to practice %s" % anchorElement.text,
                    'title': anchorElement.text,
                    'expandurl': self.expand_chapter_url + str(len(sections)) + '#now',
                    'subsections': [],
                })
            if 'dashboard-section-title-2' in classes:
                anchorElement = element.find('a')
                sections[-1]['subsections'].append({
                    'href': anchorElement.get('href'),
                    'alttitle': "Click to practice %s" % anchorElement.text,
                    'title': anchorElement.text,
                })
        self.sections = sections

    def prepselectgrade(self):
        html = lxml.html.fromstring(self.html)
        self.title = html.find('.//*[@id="select-grade-title"]').text
        self.message = html.find('.//*[@id="select-grade-message"]').text
        grades = []
        for element in html.findall('.//*[@class="select-grade-item"]'):
            anchorElement = element.find('a')
            grades.append({
                'href': anchorElement.get('href'),
                'text': anchorElement.text,
            })
        self.grades = grades

    def prepquestion(self):
        html = lxml.html.fromstring(self.html)

        self.values = {
            'questions_completed': html.find('.//*[@id="mini-dashboard-question-count"]').text,
            'points_scored': html.find('.//*[@id="mini-dashboard-points-attained"]').text,
            'points_total': html.find('.//*[@id="mini-dashboard-points-total"]').text,
        }

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
    
    def prep_reportproblem(self):
        html = lxml.html.fromstring(self.html)
        element = html.find('.//*[@id="reportproblem"]')
        self.reportproblem_form = lxml.html.tostring(element)

    def cleanup(self):
        """ Remove all unnecessary or problematic pieces of html from the local
            'html' attribute. It has an internal list of xpath statements used
            to find and remove the relevant html elements.

            We use this to do final cleanup before returning the html to the
            requesting client.
        """
        html = lxml.html.fromstring(self.html)
        elements_to_remove = [
            './/*[@id="dashboard-future-preload"]',
        ]
        for xpath in elements_to_remove:
            element = html.find(xpath)
            if element:
                element.getparent().remove(element)

        self.html = lxml.html.tostring(html)
