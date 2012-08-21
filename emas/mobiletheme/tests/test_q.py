import os
import unittest2 as unittest

from AccessControl import Unauthorized
from Products.Five import zcml

from Products.Five import fiveconfigure
from zope.component import getUtility

from base import INTEGRATION_TESTING
from Testing import ZopeTestCase as ztc

from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

from gomobile.mobile.tests import utils as test_utils
from gomobile.mobile.interfaces import MobileRequestType
from gomobile.mobile.interfaces import IMobileRequestDiscriminator
from gomobile.mobile.interfaces import IMobileImageProcessor
from gomobile.mobile.tests.utils import TestMobileRequestDiscriminator
from gomobile.mobile.tests.utils import MOBILE_USER_AGENT
from gomobile.mobile.tests.utils import HIGHEND_MOBILE_USER_AGENT
from gomobile.mobile.tests.utils import UABrowser
from gomobile.mobile.tests.utils import ZCML_INSTALL_TEST_DISCRIMINATOR

from redis import Redis
from redis.utils import from_url
from redis.exceptions import ConnectionError

from rq import Queue, Worker
from rq.scripts import setup_redis
from rq.connections import resolve_connection 

from upfrontsystems.q.scripts.queueprocessor import QueueArgs

from emas.mobiletheme.tests.test_theme import BaseTestCase


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


class TestQueue(BaseTestCase):
    """ Test the queue """

    def test_01_redis_running(self):
        args = QueueArgs()
        setup_redis(args)
        conn = resolve_connection() 
        try:
            conn.echo('ping')
        except ConnectionError:
            print 'No connection; redis is not running. Start the redis server.'

    def test_02_redis_worker_running(self):
        args = QueueArgs()
        setup_redis(args)
        worker_name = Worker.redis_worker_namespace_prefix + args.name
        worker = Worker.find_by_key(worker_name)
        assert worker is not None, 'Worker is not running. Start the worker.'

    def test_03_redis_died(self):
        """ sometimes the redis server can die while the worker keeps running.
            In such cases we have to kill the worker before restarting it.
        """
        args = QueueArgs()
        setup_redis(args)
        worker_name = Worker.redis_worker_namespace_prefix + args.name
        worker = Worker.find_by_key(worker_name)
        worker.connection.shutdown()


def test_suite():
    import unittest
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestQueue))
    return suite
