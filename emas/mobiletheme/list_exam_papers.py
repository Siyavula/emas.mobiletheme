from five import grok
from zope.interface import Interface
from Products.CMFCore.utils import getToolByName

from pas.plugins.mxit.plugin import member_id
from pas.plugins.mxit.plugin import USER_ID_TOKEN

from emas.theme.browser.mxitpayment import EXAM_PAPERS_URL
from emas.theme.browser.mxitpayment import SUBJECT_MAP

from interfaces import IThemeLayer

grok.templatedir('templates')
grok.layer(IThemeLayer)


class List_Exam_Papers(grok.View):
    """
        Custom view for past-exam-papers
    """

    grok.context(Interface)
    grok.require('zope2.View')
    grok.name('list-exam-papers')
    
    def getURLs(self):
        memberid = member_id(self.request.get(USER_ID_TOKEN))
        pps = self.context.restrictedTraverse('@@plone_portal_state')
        navroot = pps.navigation_root()
        
        urls = {
                'payed': [],
                'notpayed': [] 
               }
        gt = getToolByName(self.context, 'portal_groups')
        for subject, groupname in SUBJECT_MAP.items():
            subject = subject.title()
            group = gt.getGroupById(groupname)
            # check if the current mxit member belongs to the ExamPapers group
            if memberid in group.getMemberIds():
                tmp_list = urls['payed']
                url = '%s/%s' %(navroot.absolute_url() , EXAM_PAPERS_URL)
                tmp_list.append([url, u'Past %s Exam Papers' %subject])
                urls['payed'] = tmp_list
            else:
                tmp_list = urls['notpayed']
                url = '%s/@@mxitpaymentrequest?productId=%s' %(
                    navroot.absolute_url(), groupname
                )
                tmp_list.append([url, u'Past %s Exam Papers' %subject])
                urls['notpayed'] = tmp_list
        return urls
    
    def isExamPapersFolder(self):
        """
            Testing for some interface would be better, but for the moment
            we check the last path segment.
        """
        path = self.context.getPhysicalPath()
        return EXAM_PAPERS_URL.split('/')[-1] in path
