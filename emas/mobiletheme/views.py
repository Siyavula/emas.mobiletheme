from five import grok
from plone.directives import form
from rhaptos.xmlfile.xmlfile import IXMLFile
from interfaces import IThemeLayer

grok.templatedir('templates')
grok.layer(IThemeLayer)

class XMLFile(form.DisplayForm):
    grok.context(IXMLFile)
    grok.require('zope2.View')
    grok.name('mobilexmlfile')
    grok.template('xmlfile')
