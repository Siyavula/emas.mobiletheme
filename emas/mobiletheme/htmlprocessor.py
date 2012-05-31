import sys
import os
import re
import subprocess
import tempfile
import xml.sax.saxutils as saxutils
from cStringIO import StringIO
import Image
import ImageDraw
import ImageFont
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


# HTML entities we convert to png for the sake of mxit
ENTITIES = [
    '&#8960;',
    '&#8474;',
    '&#8484;',
    '&#8496;',
    '&#8248;',
    '&#1013;',
    '&#8469;',
    '&#160;',
    '&#8477;',
    '&#120237;',
    '&#8942;',
    '&#119842;',
    '&#119848;',
    '&#119837;',
    '&#119834;',
    '&#119847;',
    '&#119853;',
    '&#119855;',
    '&#119836;',
    '&#119838;',
]


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


class MxitHTMLProcessor(BrowserView):
    
    def process(self, source):
        if source is None and source == "":
            return source

        doc = html.fromstring(source)
        for example in doc.cssselect('div.example'):
            example.getparent().remove(example)
        return html.tostring(doc, method="xml")


class HTMLEntityProcessor(ResizeViewHelper):
    font = ImageFont.truetype(
        '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',24)

    def __init__(self, context, request):
        super(HTMLEntityProcessor, self).__init__(context, request)
        self.init()
        self.entities_image_map = {}
        portal_url = getToolByName(self.context, 'portal_url')()
        for entity in ENTITIES:
            path = self.resizer.cache.makePathKey(entity)
            file = self.resizer.cache.get(path)
            if file is None:
                # get the unicode for the character
                entity_code = html.fromstring(entity).text
                data = self.convert(entity_code)
                if not data or len(data) < 1:
                    path = 'notfound.png'
                else:
                    self.resizer.cache.set(path, data)

            img_tag = '<img class="mathml" src="%s/@@mobile_mathml_image?key=%s.png"/>' % (portal_url, path)
            self.entities_image_map[entity] = img_tag
    
    def convert(self, entity_code):
        # Get the width and height of the given text, as a 2-tuple.
        size = self.font.getsize(entity_code)
        im = Image.new("RGBA", size, (255,255,255))
        draw = ImageDraw.Draw(im)
        draw.text((0,6), entity_code, font=self.font, fill=(0,0,0))
        del draw
        img_buffer = StringIO()
        im.save(img_buffer, format="PNG")
        return img_buffer.getvalue()

    def process(self, source):
        for entity, tag in self.entities_image_map.items():
            while source.find(entity) > 0:
                source = source.replace(entity, tag)
        return source


class UnicodeProcessor(HTMLEntityProcessor):
    """ Specialize the HTMLEntityProcessor to look for the unicode codepoints
        instead of the html entities. The substition of the found codepoints
        with the cached images remains the same.
    """
    def process(self, source):
        for entity, tag in self.entities_image_map.items():
            entity_code = html.fromstring(entity).text
            while source.find(entity_code) > 0:
                source = source.replace(entity_code, tag)
        return source


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


class MxitTableProcessor(BrowserView):
    """
    Convert tables to images for mxit.
    """
    
    def process(self, source):
        if source is None and source == "":
            return source

        resizer = getMultiAdapter((self.context, self.request),
                                  IMobileImageProcessor)
        resizer.init()
        portal_url = getToolByName(self.context, 'portal_url')()
        doc = html.fromstring(source)
        for table in doc.cssselect('table'):
            table_source = html.tostring(table, method="html")
            path = resizer.cache.makePathKey(table_source)
            file = resizer.cache.get(path)
            if file is None:
                data = self.convert(table_source)
                if not data or len(data) < 1:
                    path = 'notfound'
                else:
                    resizer.cache.set(path, data)

            img_tag = '<img src="%s/@@mobile_mathml_image?key=%s.png"/>' % (portal_url, path)
            element = html.fromstring(img_tag)
            table.getparent().replace(table, element)
        return html.tostring(doc, method='xml')

    def convert(self, table, quality='30', width='320'):
        """
        Convert the html table with wkhtmltoimage, like so:
            wkhtmltoimage --quality 30 --width 320 table.html table.png
        """
        
        #TODO: make 'quality' and 'width' configurable,
        #      maybe portal properties?
        cmdargs = ['wkhtmltoimage',
                   '--quality',
                   quality,
                   '--width',
                   width,
                   '-',
                   '-'
        ]
        process = subprocess.Popen(cmdargs,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate(table)
        
        return stdout


class LatexProcessor(BrowserView):
    """
    Convert latex to png for mobile devices. 
    """

    latexHeader = r"""
    \documentclass{article}
    \usepackage{amsmath,amssymb}

    % Maths commands
    \newcommand{\pdist}[3]{#1\left(#2 \,\middle|\, #3\right)} % probability distribution (conditional)
    \newcommand{\pdista}[2]{#1\left(#2\right)} % probability distribution (unconditional)
    \renewcommand{\vec}[1]{{\boldsymbol{#1}}} % vector symbol
    \newcommand{\mat}[1]{{\boldsymbol{#1}}} % matrix symbol
    \newcommand{\prop}[1]{\mathbb{#1}} % proposition symbol
    \newcommand{\model}[1]{\mathcal{#1}} % model symbol

    \begin{document}
    \pagestyle{empty}
    """

    latexFooter = r"""
    \end{document}"""

    
    def process(self, source):
        """
        Find all the latex that has to be converted,
        Check the resizer cache and if it has not been converted,
        feed it to the convert method and cache the result.
        """

        if source is None and source == "":
            return source

        resizer = getMultiAdapter((self.context, self.request),
                                  IMobileImageProcessor)
        resizer.init()
        portal_url = getToolByName(self.context, 'portal_url')()
        doc = html.fromstring(source)
        
        tmp_dict = {}
        # find the latext in the source
        pattern = re.compile(r'\\\[.*?\\\]', re.DOTALL)
        for match in pattern.finditer(source):
            latex = source[match.start():match.end()]
            path = resizer.cache.makePathKey(latex)
            # check the resizer cache
            file = resizer.cache.get(path)
            if file is None:
                # convert the latex to png
                data = self.convert(latex)
                if not data or len(data) < 1:
                    # if we cannot do the latex to png convertion,
                    # we keep the latex
                    continue
                else:
                    resizer.cache.set(path, data)

            img_tag = '<img src="%s/@@mobile_mathml_image?key=%s.png"/>' % (portal_url, path)
            tmp_dict[latex] = img_tag
        
        for latex, img_tag in tmp_dict.items():
            while source.find(latex) > 0:
                source = source.replace(latex, img_tag)
        return source

    def convert(self, latex, dpi='120'):
        
        cachedir = '/tmp'
        workfile = tempfile.mkstemp(dir=cachedir)
        fp = open(workfile[1], 'wb')
        fp.write(self.latexHeader)
        fp.write(saxutils.unescape(latex))
        fp.write(self.latexFooter)
        fp.close()

        cmdargs = ['latex',
                   '-output-directory',
                   '/tmp',
                   '-interaction',
                   'nonstopmode',
                   '-output-format',
                   'dvi',
                   workfile[1],
                   ]
        process = subprocess.Popen(cmdargs,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        rendered, stderr = process.communicate(latex)
       
        dvifile = os.path.join(cachedir, '%s.dvi' %workfile[1])
        pngfile = os.path.join(cachedir, '%s.png' %workfile[1])
        cmdargs = ['dvipng',
                   '-q',
                   '-D',
                   dpi,
                   '-T',
                   'tight',
                   '-o',
                   pngfile,
                   dvifile,
        ]
        process = subprocess.Popen(cmdargs,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        try:
            outfile = open(pngfile, 'rb')
            data = outfile.readlines()
            outfile.close()
        except IOError:
            data = None
        
        for extension in ['tex', 'dvi', 'aux', 'log', 'png']:
            try:
                os.unlink(os.path.join(cachedir, '%s.%s' %(workfile[1], extension)))
            except OSError:
                # it's ok, the file does not exist, so no need to do cleanup.
                pass

        return data and ''.join(data) or None


class HTMLImageRewriter(BrowserView):
    """
    A copy of the gomobile HTMLImageRewriter extended with:
    - MathML to image conversion
    - unicode to image conversion (for selected unicode chars)
    - cleanup of worked solution divs
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

        latexconverter = LatexProcessor(self.context, self.request)
        html = latexconverter.process(html)

        mob_tool = getMultiAdapter((self.context, self.request),
                                   name='mobile_tool')
        #if mob_tool.isMXit():
        if True:
            mxitprocessor = MxitHTMLProcessor(self.context,
                                              self.request)
            html = mxitprocessor.process(html)

            entity_processor = HTMLEntityProcessor(self.context,
                                                   self.request)
            html = entity_processor.process(html)

            unicode_to_image_processor = UnicodeProcessor(self.context,
                                                          self.request)
            html = unicode_to_image_processor.process(html)

            mxit_table_processor = MxitTableProcessor(self.context,
                                                      self.request)
            html = mxit_table_processor.process(html)

        return html


    def __call__(self):
        """
        """
        raise RuntimeError("Please do not call this view directly - "
                           "instead use processHTML() method")

