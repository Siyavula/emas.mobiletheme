"""

    Functional and unit tests for the mobile theme.
    
    Smoke tests to see that the theme installs cleanly and opens some pages.

"""

__author__ = " <>"
__docformat__ = "epytext"
__license__ = "GPL"

from AccessControl import Unauthorized

from Testing import ZopeTestCase as ztc

from Products.Five import zcml
from Products.Five import fiveconfigure
from zope.component import getUtility

from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

from Products.PloneTestCase.layer import PloneSite

from gomobile.mobile.tests import utils as test_utils
from gomobile.mobile.interfaces import MobileRequestType, IMobileRequestDiscriminator, IMobileImageProcessor
from gomobile.mobile.tests.utils import TestMobileRequestDiscriminator
from gomobile.mobile.tests.utils import MOBILE_USER_AGENT, HIGHEND_MOBILE_USER_AGENT
from gomobile.mobile.tests.utils import UABrowser
from gomobile.mobile.tests.utils import ZCML_INSTALL_TEST_DISCRIMINATOR

from gomobiletheme.basic import tests as base


@onsetup
def setup_zcml():

    fiveconfigure.debug_mode = True
    import emas.mobiletheme
    zcml.load_config('configure.zcml', emas.mobiletheme)
    
    # This test specific ZCML installation 
    # will allow you to emulate different web and mobile browsers
    zcml.load_string(ZCML_INSTALL_TEST_DISCRIMINATOR)
    
    fiveconfigure.debug_mode = False

    # We need to tell the testing framework that these products
    # should be available. This can't happen until after we have loaded
    # the ZCML.
    ztc.installPackage('gomobile.mobile')
    ztc.installPackage('emas.mobiletheme')


# The order here is important.
setup_zcml()
ptc.setupPloneSite(products=['gomobile.mobile',
                             'emas.theme',
                             'emas.mobiletheme'])

class BaseTestCase(base.BaseTestCase):
    """ Base classes for the tests specific to the mobile theme. 
    """
    
    def getProductName(self):
        return "emas.mobiletheme"


class ThemeTestCase(BaseTestCase):
    """
    Test theme functionality using Zope test browser.
    """

    def test_render_front_page(self):
        """ Render the front page. 
        
        Assume no exceptions raisen.
        """

        self.setDiscriminateMode(MobileRequestType.MOBILE)
      
        self.browser.open(self.portal.absolute_url())
 
    def test_has_additional_head(self):
        """ Check that our JS file is included correctly.
        
        """

        # Switch to high-end mobile phone rendering
        self.setDiscriminateMode(MobileRequestType.MOBILE)
        self.setUA(HIGHEND_MOBILE_USER_AGENT)
      
        self.browser.open(self.portal.absolute_url())     
        
        html = self.browser.contents
    
        self.assertTrue(("++resource++%s/theme.js" % self.getProductName()) in html)

    def test_render_web(self):
        """ Render web page which should have not been altered by the theme. 
        
        Assume no exceptions raisen.
        """

        self.setDiscriminateMode(MobileRequestType.WEB)
      
        self.browser.open(self.portal.absolute_url())
        

    def test_render_search(self):
        """ Render search page with different inputs. Assert no exceptions risen """

        self.setDiscriminateMode(MobileRequestType.MOBILE)
      
        self.browser.open(self.portal.absolute_url() + "/search")
        
        # Input some values to the search that we see we get
        # zero hits and at least one hit        
        for search_terms in [u"Plone", u"youcantfindthis"]:
            form = self.browser.getForm(name="searchform")
            
            # Fill in the search field
            input = form.getControl(name="SearchableText")
            input.value = search_terms 
            
            # Submit the search form
            form.submit(u"Search")
            

def test_suite():
    import unittest
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ThemeTestCase))
    return suite

