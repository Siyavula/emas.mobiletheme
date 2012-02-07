import copy

from lxml.etree import ParserError 
from lxml.html import fromstring, tostring
from mobile.htmlprocessing.transformers.basic import BasicCleaner

def process(self, html):
    """ patched method to not encode result when converting back to
        string since this breaks valid html entities.
    """
    
    # Check whether we got ready parse-tree or string input
    result_type = type(html)

    
    if isinstance(html, basestring):
        try:
            doc = fromstring(html)
        except ParserError:
            # Can't handle malformed doc, empty doc, etc.
            return html
    else:
        doc = copy.deepcopy(html)

    # Run XHTML MP specific cleaning
    self.clean_mobile(doc)

    # Run normal cleaning
    if not self.trusted:
        self(doc)

    return tostring(doc, method="xml")

BasicCleaner.process = process

