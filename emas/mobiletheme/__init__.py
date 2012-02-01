from zope.i18nmessageid import MessageFactory

# Declare the function which will turn strings to translation ids
MessageFactory = MessageFactory('${namespace_package}.${package}')

def initialize(context):
    """Initializer called when used as a Zope 2 product."""
