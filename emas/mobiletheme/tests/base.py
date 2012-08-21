from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import quickInstallProduct

from plone.testing import z2

PROJECTNAME = "emas.mobiletheme"

class TestCase(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import plone.app.registry
        import plone.resource
        import plone.app.theming
        import plone.app.folder
        import rhaptos.xmlfile
        import emas.transforms
        import rhaptos.cnxmltransforms
        import rhaptos.compilation
        import upfront.shorturl
        import fullmarks.mathjax
        import siyavula.what
        import collective.topictree
        import emas.theme
        import emas.mobiletheme
        self.loadZCML(package=plone.app.registry)
        self.loadZCML(package=plone.resource)
        self.loadZCML(package=plone.app.theming)
        self.loadZCML(package=rhaptos.xmlfile)
        self.loadZCML(package=emas.transforms)
        self.loadZCML(package=rhaptos.cnxmltransforms)
        self.loadZCML(package=rhaptos.compilation)
        self.loadZCML(package=upfront.shorturl)
        self.loadZCML(package=fullmarks.mathjax)
        self.loadZCML(package=siyavula.what)
        self.loadZCML(package=collective.topictree)
        self.loadZCML(package=emas.theme)
        self.loadZCML('overrides.zcml', package=emas.theme)
        self.loadZCML(package=emas.mobiletheme)

    def setUpPloneSite(self, portal):
        quickInstallProduct(portal, 'emas.theme')
        self.applyProfile(portal, 'emas.theme:default')

        quickInstallProduct(portal, 'emas.mobiletheme')
        self.applyProfile(portal, '%s:default' % PROJECTNAME)

    def tearDownZope(self, app):
        z2.uninstallProduct(app, PROJECTNAME)

FIXTURE = TestCase()
INTEGRATION_TESTING = IntegrationTesting(bases=(FIXTURE,), name="fixture:Integration")

