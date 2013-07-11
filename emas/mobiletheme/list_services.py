from five import grok

from zope.interface import Interface

from plone.uuid.interfaces import IUUID

from emas.app.memberservice import MemberServicesDataAccess
from emas.app.browser.utils import practice_service_intids

from interfaces import IThemeLayer

PRACTICE_URL = '@@practice'
MXIT_SERVICE = 'mxit'

grok.templatedir('templates')
grok.layer(IThemeLayer)


class List_Services(grok.View):
    """
        Custom view for mobile practice service
    """

    grok.context(Interface)
    grok.require('zope2.View')
    grok.name('list-services')
    
    def __init__(self, context, request):
        super(List_Services, self).__init__(context, request)
        self.pps = self.context.restrictedTraverse('@@plone_portal_state')
        self.portal = self.pps.portal()
        self.portal_url = self.pps.portal_url()
        self.member = self.pps.member()
        self.memberservices = []
        self.isMxit = self.context.restrictedTraverse('@@mobile_tool').isMXit()
        self.navroot = self.pps.navigation_root()
        self.subject = self.getSubject(self.navroot)
        self.services = self._getServices(self.portal, self.subject)
        self.dao = MemberServicesDataAccess(self.context)

        memberid = self.member.getId()
        if memberid:
            ids = practice_service_intids(self.context)
            self.memberservices = \
                self.dao.get_memberservices_by_subject(memberid, self.subject)

    def getSubject(self, navroot):
        return navroot.getId()

    def craftPaidLink(self, navroot, service):
        access_path = service.access_path
        link = ['%s' % service.Title(),
                '%s/%s' % (navroot.absolute_url(), access_path)]
        return link

    def craftNotPaidLink(self, navroot, service):
        if self.isMxit:
            link = ['%s' % service.Title(),
                    '%s/@@mxitpaymentrequest?productId=%s' % (
                        navroot.absolute_url(), service.getId())]
        else:
            link = ['%s' % service.Title(),
                    '%s/@@purchase?productId=%s' % (
                        navroot.absolute_url(), service.getId())]
        return link

    def getURLs(self):
        urls = {
                'paid': [],
                'notpaid': []
               }
        
        if self.isMxit:
            paid, notpaid = self.getMXitServices(
                                self.services, self.memberservices)
        else:
            paid, notpaid = self.getWebAndMobileServices(
                                self.services, self.memberservices)

        urls['paid'] = \
            [self.craftPaidLink(self.navroot, s) for s in paid]
        
        urls['notpaid'] = \
            [self.craftNotPaidLink(self.navroot, s) for s in notpaid]

        return urls

    def _getServices(self, portal, subject):
        products_and_services = portal.products_and_services
        services = products_and_services.getFolderContents(
            full_objects=True,
            contentFilter={'portal_type': 'emas.app.service',
                           'subject': subject})
        return services

    def getMXitServices(self, services, memberservices):
        """ Probably good idea to @memoize this.
        """
        paid = []
        notpaid = []
        related_services = \
            [s.related_service.to_object for s in memberservices]

        for service in services:
            # we are only interested in the mxit services now
            if MXIT_SERVICE in service.channels:
                if service in related_services:
                    paid.append(service)
                else:
                    notpaid.append(service)
        return paid, notpaid
        
    def getWebAndMobileServices(self, services, memberservices):
        """ Probably good idea to @memoize this too.
        """
        paid = []
        notpaid = []
        related_services = \
            [s.related_service.to_object for s in memberservices]

        for service in services:
            if MXIT_SERVICE not in service.channels:
                if service in related_services:
                    paid.append(service)
                else:
                    notpaid.append(service)
        return paid, notpaid
        
    def isPracticeService(self):
        """
        """
        path = self.context.getPhysicalPath()
        return PRACTICE_URL.split('/')[-1] in path
