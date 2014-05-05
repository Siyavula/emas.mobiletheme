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
        portal_url = self.context.restrictedTraverse('@@plone_portal_state').portal_url()
        self.dashboard_url = '%s/@@practice/dashboard' % portal_url
        self.reportproblem_url = '%s/@@practice/user-feedback-mobi' % portal_url
        self.expand_chapter_url = '%s/@@practice/dashboard/chapter-' % portal_url

        path = self.request.get_header('PATH_INFO')
        pathParts = path.strip('/').split('/')
        if pathParts[:1] == ['@@practice']:
            del pathParts[0]

        self.view_is_dashboard = (pathParts[:1] == ['dashboard'])
        self.view_is_select_grade = (pathParts[:1] == ['select_grade'])
        self.view_is_question = (pathParts[1:2] == ['question'])
        self.view_is_report_problem = (pathParts[:1] in [['user-feedback-mobi'], ['user-feedback-mobi-success']])

        self.view_not_available_on_mobile = \
            (pathParts[:1] == ['teacher-dashboard']) or \
            (pathParts[:1] == ['question-list']) or \
            (pathParts[:1] == ['admin'])

        if self.view_is_dashboard:
            self.prep_dashboard()
        elif self.view_is_select_grade:
            self.prep_select_grade()
        elif self.view_is_question:
            self.prep_question()
        elif self.view_is_report_problem:
            self.prep_report_problem()
        
        # do final cleanup on html
        self.cleanup()

    def prep_dashboard(self):
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

        anchored = False # <a name="now"/> handled a bit differently from other elements since it comes before the chapter name
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
                    'points': [0,0],
                    'anchor': anchored,
                })
                anchored = False
            if 'dashboard-section-title-2' in classes:
                anchorElement = element.find('a')
                sections[-1]['subsections'].append({
                    'href': anchorElement.get('href'),
                    'alttitle': "Click to practice %s" % anchorElement.text,
                    'title': anchorElement.text,
                })
            if 'dashboard-section-points' in classes:
                sections[-1]['points'][0] = element.text
            if 'dashboard-section-points-total' in classes:
                sections[-1]['points'][1] = element.text
            if 'dashboard-section-anchor' in classes:
                anchored = True
        self.sections = sections

    def prep_select_grade(self):
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

    def prep_question(self):
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
    
    def prep_report_problem(self):
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
        ]
        for xpath in elements_to_remove:
            element = html.find(xpath)
            if element:
                element.getparent().remove(element)

        self.html = lxml.html.tostring(html)
