from zope.interface import Interface
from five import grok
from plone.directives import form
from rhaptos.xmlfile.xmlfile import IXMLFile
from gomobile.mobile.browser.views import MobileTool as BaseMobileTool
from interfaces import IThemeLayer

grok.templatedir('templates')
grok.layer(IThemeLayer)

class XMLFile(form.DisplayForm):
    grok.context(IXMLFile)
    grok.require('zope2.View')
    grok.name('mobilexmlfile')
    grok.template('xmlfile')


class MobileTool(BaseMobileTool):
    """ Specialise check for low end phones
    """

    def isLowEndPhone(self):
        """ override to check for Mxit """
        if self.isMXit():
            return True
        else:
            return super(MobileTool, self).isLowEndPhone()

    def isMXit(self):
        return "MXit WebBot" in self.request.get('HTTP_USER_AGENT', '')
