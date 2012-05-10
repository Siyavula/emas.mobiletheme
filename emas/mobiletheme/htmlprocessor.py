import lxml
from lxml import etree, html
from xml.parsers.expat import ExpatError

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from ZPublisher import NotFound

from zope.component import getMultiAdapter, getUtility
from gomobile.mobile.interfaces import IMobileImageProcessor
from gomobile.mobile.browser.imageprocessor import ResizeViewHelper
from gomobile.mobile.interfaces import IMobileRequestDiscriminator, \
    MobileRequestType
from upfront.mathmlimage import convert

class MathMLProcessor(ResizeViewHelper):

    def process(self, source):
        self.init()

        doc = html.fromstring(source)
        portal_url = getToolByName(self.context, 'portal_url')()

        # svglib don't handle 'semantics' and 'annotations' tags
        def cleanmathml(element):
            for child in element.getchildren():
                cleanmathml(child)
                # strip namespace attrs - this confuses svglib
                for attr in child.keys():
                    if attr.startswith('xmlns'):
                        del child.attrib[attr]
                if child.tag in ('m:annotation-xml','annotation-xml'):
                    element.remove(child)
                if child.tag in ('m:semantics', 'semantics'):
                    # move the children of semantics tag to parent
                    element.extend(child.getchildren())
                    # remove semantics tag
                    element.remove(child)

        for mathml in doc.cssselect('math'):
            display = mathml.get('display', 'inline')
            cleanmathml(mathml)
            mathmlstring = html.tostring(mathml)

            # lxml has a bug that includes text behind closing tag -
            # manually split it off and it later
            mathmlstring, inlinetext = mathmlstring.split('</math>')
            mathmlstring += '</math>'

            path = self.resizer.cache.makePathKey(mathmlstring)
            file = self.resizer.cache.get(path)
            if file is None:
                try:
                    data = convert(mathmlstring)
                    self.resizer.cache.set(path, data)
                except ExpatError:
                    path = 'notfound.png'

            img_tag = '<img class="mathml" src="%s/@@mobile_mathml_image?key=%s.png"/>' % (portal_url, path)
            if display == 'block':
                img_tag = '<div class="mathml">%s</div>' % img_tag

            if inlinetext:
                img = html.fromstring('%s <span>%s</span>' %(
                    img_tag, inlinetext))
            else:
                img = html.fromstring(img_tag)

            mathml.getparent().replace(mathml, img)

        return html.tostring(doc, method="xml")

class MobileMathMLImage(BrowserView):

    def __call__(self):
        key = self.request.get('key')
        if key is None:
            raise NotFound("No key specified")
        filename = key.split('.')[0]
        resizer = getMultiAdapter((self.context, self.request),
                                  IMobileImageProcessor)
        resizer.init()

        file = resizer.cache.get(filename)
        if file:
            f = open(file, "rb")
            data = f.read()
            f.close()
        else:
            raise NotFound("MathML image for key %s not found" % filename)

        self.request.response.setHeader("Content-type", "image/png")
        return data


class MathMLImageRewriter(BrowserView):
    """
    A copy of the gomobile HTMLImageRewriter extended with MathML to
    image conversion
    """

    def processHTML(self, html, trusted=True, only_for_mobile=False):
        """ Rewrite HTML for mobile compatible way.

        @param html: HTML code as a string

        @param trusted: If True do not clean up nasty tags like <script>

        @param only_for_mobile: Perform processing only if the site is
        rendered in mobile mode

        """


        if only_for_mobile:
            # Perform check if we are in mobile rendering mode
            discriminator = getUtility(IMobileRequestDiscriminator)
            flags = discriminator.discriminate(self.context, self.request)
            if not MobileRequestType.MOBILE in flags:
                return html

        resizer = getMultiAdapter((self.context, self.request),
                                  IMobileImageProcessor)

        resizer.init()
        if html is not None and html != "":
            # lxml bails out if input is not sane
            html = resizer.processHTML(html, trusted)

        mathmlconverter = MathMLProcessor(self.context, self.request)
        html = mathmlconverter.process(html)
        return html


    def __call__(self):
        """
        """
        raise RuntimeError("Please do not call this view directly - "
                           "instead use processHTML() method")

