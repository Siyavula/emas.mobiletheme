from zope.schema import List, TextLine, Bool, Int
from zope.interface import Interface
from plone.registry import field

import gomobiletheme.basic.interfaces as base

from emas.mobiletheme import MessageFactory as _


class IThemeLayer(base.IThemeLayer):
    """  Mobile theme layer.

    All views viewlets registered against this layer will be visible
    when the mobile theme is activated.
    """


class IEmasMobileThemeSettings(Interface):
    """ Describes settings for the mobile theme.
    """

    maths_gacode = TextLine(
        title=_(u'Everythingmaths.co.za GA code'),
        description=_(u'Google Analytics tracking code for Everythingmaths.'),
        required=True
    )

    science_gacode = TextLine(
        title=_(u'Everythingscience.co.za GA code'),
        description=_(u'Google Analytics tracking code for Everythingscience.'),
        required=True
    )

    redis_port = Int(
        title=_(u'Redis port'),
        description=_(u'Port where redis runs'),
        default=6666,
        required=True
    )

