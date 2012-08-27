from zope.interface import Interface
from Products.ATContentTypes.interface import IATDocument
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


class Document(form.DisplayForm):
    grok.context(IATDocument)
    grok.require('zope2.View')
    grok.name('mobiledocumentdefault')
    grok.template('document')

    def update(self):
        self.w['body'] = self.context.getText()


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
