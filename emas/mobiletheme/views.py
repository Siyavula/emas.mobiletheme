from five import grok
from zope.interface import Interface

from Products.ATContentTypes.interface import IATDocument
from plone.directives import form
from Products.CMFCore.utils import getToolByName

from rhaptos.xmlfile.xmlfile import IXMLFile
from gomobile.mobile.browser.views import MobileTool as BaseMobileTool
from interfaces import IThemeLayer

from emas.app.browser.order import Order as BaseOrder
from emas.theme.browser.toc import TableOfContents as BaseTOC

grok.templatedir('templates')
grok.layer(IThemeLayer)

MXIT_MARKER = 'MXit'
MXIT_AGENT_HEADER = 'HTTP_USER_AGENT'

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
        header = self.request.get(MXIT_AGENT_HEADER, '').lower()
        return MXIT_MARKER.lower() in header


class Order(BaseOrder):
    """ Specialised to accommodate mobile workflow and template and to add
        security constraint.
    """
    grok.require('cmf.SetOwnProperties')
    def update(self):
        return super(Order, self).update()


class TableOfContents(BaseTOC):
    """ Helper methods and a template that renders only the table of contents.
    """
    def getContentItems(self, container=None):
        """ Add the actions specified in the portal_actions category,
            'extra_mobile_links'.
        """
        items = super(TableOfContents, self).getContentItems()
        portal_actions = getToolByName(self.context, 'portal_actions')
        actions = portal_actions.listFilteredActionsFor(self.context)
        mobile_items = []

        # don't add the extra links (which includes practice) on MXit
        if not self.context.restrictedTraverse('@@mobile_tool').isMXit():
            for action in actions.get('extra_mobile_links', []):
                tmp_dict = {
                    'Title': action['title'],
                    'absolute_url': action['url'],
                    'css_class': 'practice-link',
                }
                mobile_items.append(tmp_dict)
        mobile_items.extend(items)
        return mobile_items
