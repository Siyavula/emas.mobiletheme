import sys
import os
import re
import logging
import subprocess
import tempfile
import urllib
from cStringIO import StringIO
try:
    import Image
    import ImageDraw
    import ImageFont
except ImportError:
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFont
from lxml import etree, html
from xml.parsers.expat import ExpatError

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from ZPublisher import NotFound

from zope.component import getMultiAdapter, getUtility
from gomobile.imageinfo.interfaces import IImageInfoUtility
from gomobile.mobile.interfaces import IMobileImageProcessor
from gomobile.mobile.browser.imageprocessor import MobileImageProcessor \
    as BaseMobileImageProcessor
from gomobile.mobile.browser.imageprocessor import ResizeViewHelper
from gomobile.mobile.interfaces import IMobileRequestDiscriminator, \
    MobileRequestType
from mobile.sniffer.utilities import get_user_agent_hash
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

logger = logging.getLogger("Resizer")

VIEW_NAME = "@@mobile_image"

class MobileImageProcessor(BaseMobileImageProcessor):
    """ Modify gomobile image processor to resize and cache when html is
        processed.
    """

    def getImageDownloadURL(self, url, properties={}):
        """
        Return download URL for image which is put through image resizer.

        @param url: Source image URI, relative to context, or absolite URL

        @param properties: Extra options needed to be given to the
        resizer, e.g. padding, max width, etc.

        @return: String, URL where to resized image can be downloaded.
            This URL varies by the user agent.
        """
        self.init()

        url = self.mapURL(url)

        path = self.cache.makePathKey(url)
        file = self.cache.get(path)
        if file is None:
            helper = ResizeViewHelper(self.context, self.request)
            helper.init()
            helper.parseParameters({'conserve_aspect_ration': True, 'url': url})
            width, height = helper.resolveDimensions()
            tool = getUtility(IImageInfoUtility)

            logger.debug(
                "Resizing image to mobile dimensions %d %d" % (
                    width, height)
                )
            data, format = tool.getURLResizedImage(url, width, height,
                                                   conserve_aspect_ration=True)

            # Mercifully cache broken images from remote HTTP downloads
            if data is None:
                value = ""
            else:
                value = data.getvalue()

            self.cache.set(path, value)

        # Prepare arguments for the image resizer view
        new_props = {"conserve_aspect_ration" : "true"}
        new_props.update(properties)

        new_props["key"] = path

        if self.isUserAgentSpecific(url, new_props):
            # Check if the result may vary by user agnt
            new_props["user_agent_md5"] = get_user_agent_hash(self.request)

        new_props = self.finalizeViewArguments(new_props)

        return (self.site.absolute_url() + "/" + VIEW_NAME + "?" +
                urllib.urlencode(new_props))


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

            img_tag = '<img class="mathml" src="%s/%s?key=%s.png"/>' % (
                portal_url, VIEW_NAME, path)
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
        if not source:
            return source

        doc = html.fromstring(source)
        for example in doc.cssselect('div.example'):
            example.getparent().remove(example)
        
        # the the source from our stripped doc above
        source = html.tostring(doc, method="xml")
        
        # MXit has a number of emoticons including things like:
        # (c) that is rendered as chillies.
        # We stop this behaviour by removing the first round-brace from
        # all single, non-digit characters enclosed in round-braces.
        # First we match all non-digit characters enclosed in round-braces,
        # marking all but the first round brace as a group named='element'
        pattern=re.compile('\((?P<element>\D\))')
        # Then we replace the letter in round-braces with the group named
        # 'element', thereby stripping away the first round-brace.
        source = pattern.sub(r'\g<element>', source)
            
        return source

fontdir = os.path.join(os.path.dirname(__file__), 'font')

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

            img_tag = '<img class="mathml" src="%s/@@mobile_image?key=%s.png"/>' % (portal_url, path)
            self.entities_image_map[entity] = img_tag
    
    def convert(self, entity_code):
        # Get the width and height of the given text, as a tuple.
        size = self.font.getsize(entity_code)
        im = Image.new("RGBA", size, (255,255,255,0))
        draw = ImageDraw.Draw(im)
        draw.text((0,8), entity_code, font=self.font, fill=(0,0,0))
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


class MobileImage(BrowserView):

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

        content_type = "image/" + self.resolveCacheFormat(data)
        self.request.response.setHeader("Content-type", content_type)
        return data

    def resolveCacheFormat(self, data):
        """
        Peek cached file first bytes to get the format.
        """
        if data[0:3] == "PNG":
            return "png"
        elif data[0:3] == "GIF":
            return "gif"
        else:
            return "jpeg"


class MxitTableProcessor(BrowserView):
    """
    Convert tables to images for mxit.
    """
    
    def process(self, source):
        if not source:
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

            img_tag = '<img src="%s/@@mobile_image?key=%s.png"/>' % (portal_url, path)
            element = html.fromstring(img_tag)
            table.getparent().replace(table, element)
        return html.tostring(doc, method='xml')

    def convert(self, table, quality='90', width='320'):
        """
        Convert the html table with wkhtmltoimage, like so:
            wkhtmltoimage --quality 70 --width 320 table.html table.png
        """
        
        #TODO: make 'quality' and 'width' configurable,
        #      maybe portal properties?
        cmdargs = ['wkhtmltoimage',
                   '--format',
                   'png',
                   '--quality',
                   quality,
                   '--width',
                   width,
                   '--transparent',
                   '-',
                   '-'
        ]
       
        process = subprocess.Popen(cmdargs,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate(table)

        # Now the resultant image goes through imagemagick
        # to set the background transparent.
        format_arg = 'png:-'
        cmdargs = ['convert',
                   '-transparent',
                   'white',
                   '-',
                   format_arg
                  ]
        data = stdout
        process = subprocess.Popen(cmdargs,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate(data)

        return stdout


class LatexProcessor(BrowserView):
    """
    Convert latex to png for mobile devices. 
    """

    latexUnicode = r"""
% Punctuation
\DeclareUnicodeCharacter{00A0}{~}
\DeclareUnicodeCharacter{2019}{'}
\DeclareUnicodeCharacter{201C}{``}
\DeclareUnicodeCharacter{201D}{''}
\DeclareUnicodeCharacter{2013}{--}
\DeclareUnicodeCharacter{2014}{---}

% Greek upper case
\DeclareUnicodeCharacter{0393}{\ensuremath{\Gamma{}}}
\DeclareUnicodeCharacter{0394}{\ensuremath{\Delta{}}}
\DeclareUnicodeCharacter{0398}{\ensuremath{\Theta{}}}
\DeclareUnicodeCharacter{039B}{\ensuremath{\Lambda{}}}
\DeclareUnicodeCharacter{039E}{\ensuremath{\Xi{}}}
\DeclareUnicodeCharacter{03A0}{\ensuremath{\Pi{}}}
\DeclareUnicodeCharacter{03A3}{\ensuremath{\Sigma{}}}
\DeclareUnicodeCharacter{03A5}{\ensuremath{\Upsilon{}}}
\DeclareUnicodeCharacter{03A6}{\ensuremath{\Phi{}}}
\DeclareUnicodeCharacter{03A8}{\ensuremath{\Psi{}}}
\DeclareUnicodeCharacter{03A9}{\ensuremath{\Omega{}}}

% Greek lower case
\DeclareUnicodeCharacter{03B1}{\ensuremath{\alpha{}}}
\DeclareUnicodeCharacter{03B2}{\ensuremath{\beta{}}}
\DeclareUnicodeCharacter{03B3}{\ensuremath{\gamma{}}}
\DeclareUnicodeCharacter{03B4}{\ensuremath{\delta{}}}
\DeclareUnicodeCharacter{03B5}{\ensuremath{\varepsilon{}}}
\DeclareUnicodeCharacter{03B6}{\ensuremath{\zeta{}}}
\DeclareUnicodeCharacter{03B7}{\ensuremath{\eta{}}}
\DeclareUnicodeCharacter{03B8}{\ensuremath{\theta{}}}
\DeclareUnicodeCharacter{03B9}{\ensuremath{\iota{}}}
\DeclareUnicodeCharacter{03BA}{\ensuremath{\kappa{}}}
\DeclareUnicodeCharacter{03BB}{\ensuremath{\lambda{}}}
\DeclareUnicodeCharacter{03BC}{\ensuremath{\mu{}}}
\DeclareUnicodeCharacter{03BD}{\ensuremath{\nu{}}}
\DeclareUnicodeCharacter{03BE}{\ensuremath{\xi{}}}
\DeclareUnicodeCharacter{03BF}{\ensuremath{\omicron{}}}
\DeclareUnicodeCharacter{03C0}{\ensuremath{\pi{}}}
\DeclareUnicodeCharacter{03C1}{\ensuremath{\rho{}}}
\DeclareUnicodeCharacter{03C2}{\ensuremath{\varsigma{}}}
\DeclareUnicodeCharacter{03C3}{\ensuremath{\sigma{}}}
\DeclareUnicodeCharacter{03C4}{\ensuremath{\tau{}}}
\DeclareUnicodeCharacter{03C5}{\ensuremath{\upsilon{}}}
\DeclareUnicodeCharacter{03C6}{\ensuremath{\phi{}}}
\DeclareUnicodeCharacter{03C7}{\ensuremath{\chi{}}}
\DeclareUnicodeCharacter{03C8}{\ensuremath{\psi{}}}
\DeclareUnicodeCharacter{03C9}{\ensuremath{\omega{}}}
\DeclareUnicodeCharacter{03F5}{\ensuremath{\epsilon{}}}

% Units
\DeclareUnicodeCharacter{00B0}{\ensuremath{^{\circ}}}
\DeclareUnicodeCharacter{2103}{\ensuremath{^{\circ}\text{C}}}

% Blackboard math
\DeclareUnicodeCharacter{2115}{\ensuremath{\mathbb{N}}}
\DeclareUnicodeCharacter{211A}{\ensuremath{\mathbb{Q}}}
\DeclareUnicodeCharacter{211D}{\ensuremath{\mathbb{R}}}
\DeclareUnicodeCharacter{2124}{\ensuremath{\mathbb{Z}}}

% Math symbols
\DeclareUnicodeCharacter{00B1}{\ensuremath{\pm{}}}
\DeclareUnicodeCharacter{00B7}{\ensuremath{\cdot{}}}
\DeclareUnicodeCharacter{00D7}{\ensuremath{\times{}}}
\DeclareUnicodeCharacter{00F7}{\ensuremath{\div{}}}
\DeclareUnicodeCharacter{2113}{\ensuremath{\ell{}}}
\DeclareUnicodeCharacter{2192}{\ensuremath{\rightarrow{}}}
\DeclareUnicodeCharacter{21CB}{\ensuremath{\leftrightharpoons{}}}
\DeclareUnicodeCharacter{21CC}{\ensuremath{\rightleftharpoons{}}}
\DeclareUnicodeCharacter{2208}{\ensuremath{\in{}}}
\DeclareUnicodeCharacter{2211}{\ensuremath{\sum{}}}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}} % minus sign
\DeclareUnicodeCharacter{221D}{\ensuremath{\propto{}}}
\DeclareUnicodeCharacter{221E}{\ensuremath{\infty{}}}
\DeclareUnicodeCharacter{2225}{\ensuremath{\parallel{}}}
\DeclareUnicodeCharacter{2234}{\ensuremath{\therefore{}}}
\DeclareUnicodeCharacter{2248}{\ensuremath{\approx{}}}
\DeclareUnicodeCharacter{2260}{\ensuremath{\ne{}}}
\DeclareUnicodeCharacter{2264}{\ensuremath{\le{}}}
\DeclareUnicodeCharacter{22A5}{\ensuremath{\perp{}}}
\DeclareUnicodeCharacter{22EF}{\ensuremath{\cdots{}}}
"""

    latexHeader = r"""
\documentclass{article}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage[utf8]{inputenc}""" + latexUnicode + r"""
\begin{document}
\pagestyle{empty}
"""

    latexFooter = r"""
\end{document}
"""

    
    def process(self, source):
        """
        Find all the latex that has to be converted,
        Check the resizer cache and if it has not been converted,
        feed it to the convert method and cache the result.
        """

        if not source:
            return source

        resizer = getMultiAdapter((self.context, self.request),
                                  IMobileImageProcessor)
        resizer.init()
        portal_url = getToolByName(self.context, 'portal_url')()
        doc = html.fromstring(source)
        
        img_dict = {}
        # find the block latext in the source
        # we add a break before the block levels to create some space
        pattern = re.compile(r'\\\[.*?\\\]', re.DOTALL)
        img_dict.update(
            self.latext_png_map(source, pattern, resizer, portal_url, '<br/>')
        )
        
        # find the in-line latex
        pattern = re.compile(r'\\\(.*?\\\)', re.DOTALL)
        img_dict.update(
            self.latext_png_map(source, pattern, resizer, portal_url)
        )
        
        for latex, img_tag in img_dict.items():
            while source.find(latex) > 0:
                source = source.replace(latex, img_tag)
        return source

    def latext_png_map(self, source, pattern, resizer, portal_url, extra=''):
        tmp_dict = {}
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

            img_tag = (
                '%s<img src="%s/@@mobile_image?key=%s.png"/>'
                % (extra, portal_url, path)
            )
            tmp_dict[latex] = img_tag
        return tmp_dict

    def convert(self, latex, dpi='120'):
        
        cachedir = '/tmp'
        workfile = tempfile.mkstemp(dir=cachedir)
        fp = open(workfile[1], 'wb')
        fp.write(self.latexHeader)
        fp.write(html.fromstring(latex).text.encode('utf-8'))
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
                   '-bg',
                   'Transparent',
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
        
        resizer = MobileImageProcessor(self.context, self.request)

        resizer.init()
        if html is not None and html != "":
            # hack to remove encoding declaration
            encoding_declaration = ' encoding="utf-8"'
            html = ''.join(html.split(encoding_declaration))
            
            # lxml bails out if input is not sane
            html = resizer.processHTML(html, trusted)

        mathmlconverter = MathMLProcessor(self.context, self.request)
        html = mathmlconverter.process(html)

        latexconverter = LatexProcessor(self.context, self.request)
        html = latexconverter.process(html)

        mob_tool = getMultiAdapter((self.context, self.request),
                                   name='mobile_tool')
        if mob_tool.isMXit():
            mxitprocessor = MxitHTMLProcessor(self.context, self.request)
            html = mxitprocessor.process(html)

            mxit_table_processor = MxitTableProcessor(self.context,
                                                      self.request)
            html = mxit_table_processor.process(html)

        if mob_tool.isLowEndPhone():
            entity_processor = HTMLEntityProcessor(self.context, self.request)
            html = entity_processor.process(html)

            unicode_to_image_processor = UnicodeProcessor(self.context,
                                                          self.request)
            html = unicode_to_image_processor.process(html)


        return html


    def __call__(self):
        """
        """
        raise RuntimeError("Please do not call this view directly - "
                           "instead use processHTML() method")

