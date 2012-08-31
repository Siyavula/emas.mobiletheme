from five import grok

from zope.interface import Interface

from pas.plugins.mxit.plugin import member_id
from pas.plugins.mxit.plugin import USER_ID_TOKEN

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
        self.member = self.pps.member()
        self.memberservices = []
        self.msfolder = self.portal.memberservices
        self.services = self.getServices()
        self.isMxit = self.context.restrictedTraverse('@@mobile_tool').isMXit()
        self.navroot = self.pps.navigation_root()
        

        memberid = self.member.getId()
        if memberid:
            cf = {'portal_type' :'emas.app.memberservice'}
            self.memberservices = \
                self.msfolder.getFolderContents(contentFilter=cf)


    def craftPaidLink(self, navroot, service):
        link = ['%s' %service.Title(), '%s/question' %navroot.absolute_url()]
        return link


    def craftNotPaidLink(self, navroot, service):
        if self.isMxit:
            link = ['%s' %service.Title(),
                    '%s/@@mxitpaymentrequest?productId=%s' %(
                        navroot.absolute_url(), service.getId())]
        else:
            link = ['%s' %service.Title(),
                    '%s/@@purchase?productId=%s' %(
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

    
    def getServices(self):
        products_and_services = self.portal.products_and_services
        services = products_and_services.getFolderContents(
            full_objects=True, 
            contentFilter={'portal_type': 'emas.app.service'})
        return services


    def getMXitServices(self, services, memberservices):
        """ Probably good idea to @memoize this.
        """
        paid = []
        notpaid = []
        related_services = \
            [s for s.related_service.to_object in memberservices]

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
            [s for s.related_service.to_object in memberservices]

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
