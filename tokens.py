"""
XML token classes representing mark up and text.

The property idiom used in this module is discussed here:

    http://docs.python.org/release/3.2/library/functions.html#property

"""

import re
import sys
from collections import OrderedDict

from .rex import XML_SPE_, ElemTagRE_, AttRE_
#from rex_sgml import SGML_SPE_


#
# Token Classes
#

class Token(object):
    """
    Abstract superclass for all token classes.

    """
    __slots__ = ['xml']
    template = NotImplemented
    # TODO: Move encoding to tokenizer function(s).
    encoding = sys.getdefaultencoding()

    MAX_REPR_WIDTH = 60

    def __repr__(self):
        """
        Tokens longer than MAX_REPR_WIDTH will be sliced (with an elipsis
        added to indicate that the whole token is not being displayed). This
        is useful for keeping the display of Text tokens (which can be very
        long) managable.

        To change the slice size used for all tokens, set the class variable
        Token.MAX_REPR_WIDTH. Setting it to None will cause the full token
        to be displayed; the usual Python convention,
        eval(repr(token)) == token, then holds.

        """
        text = self.xml
        MAX_REPR_WIDTH = self.MAX_REPR_WIDTH
        if MAX_REPR_WIDTH is not None and len(text) > MAX_REPR_WIDTH:
            text = '{0}...'.format(text[:MAX_REPR_WIDTH])
        return '{self.__class__.__name__}({text!r})'.format(
            self=self, text=text)

    def is_a(self, token_class, *_not_used):
        """
        Check whether the current token is an instance of class token_class.

        token.is_a(Start) reads as "token is a Start?"

        Positional arguments are used by some token classes (Tag: *names,
        PI: *targets).

        """
        return isinstance(self, token_class)

    def reserialize(self):
        """
        Update self.xml based on internal state.
        """
        raise NotImplementedError


class Text(Token):
    """
    Plain text: a run of text not containing the "<" character.

    """
    __slots__ = []

    def __init__(self, xml):
        self.xml = xml

    @property
    def isspace(self):
        """isspace property: token is whitespace"""
        return self.xml.isspace()


class Tag(Token):
    """
    Abstract superclass for Start, End, and Empty.

    """
    __slots__ = ['_name']

    def is_a(self, token_class, *names):
        return (isinstance(self, token_class)
                and (not names or self.name in names))

    @property
    def name(self):
        """name property: the tag name"""
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        self.reserialize()

    # TODO: add basic namespace extraction support for attributes?

    @property
    def ns_prefix(self):
        """ns_prefix property: namespace prefix of qualified tag name"""
        qname = self._name
        return ':' in qname and qname.split(':')[0] or ''

    @ns_prefix.setter
    def ns_prefix(self, prefix):
        qname = self._name
        if ':' in qname:
            old_prefix, name = qname.split(':', 1)
        else:
            old_prefix, name = '', qname
        if old_prefix != prefix:
            # Don't reserialize needlessly.
            if prefix:
                self._name = '{prefix}:{name}'.format(**locals())
            else:
                self._name = name
            self.reserialize()


class StartOrEmpty(Tag):
    """
    Abstract superclass for Start and Empty

    """
    __slots__ = ['attributes']

    def __init__(self, xml):
        self.xml = xml
        # Parse element name and attributes.
        m = ElemTagRE_.search(xml)
        self._name = m.group('name')
        self.attributes = attributes = AttributeDict(token=self)
        for m in AttRE_.finditer(m.group('attributes')):
            attributes[m.group('attribute_name')] = m.group('attribute_value')[1:-1]

    def __getitem__(self, attribute_name):
        return self.attributes.get(attribute_name)

    def __setitem__(self, attribute_name, xml):
        self.attributes[attribute_name] = xml

    def __delitem__(self, attribute_name):
        del self.attributes[attribute_name]

    def __contains__(self, attribute_name):
        return attribute_name in self.attributes

    def delete_attribute(self, attribute_name):
        if attribute_name in self.attributes:
            del self.attributes[attribute_name]

    def set_attribute_order(self, attribute_order=[], sort=False):
        """
        Re-order attributes based on attribute_order list. Any attributes
        listed in attribute_order will appear first (and in that order); any
        remaining attributes will follow in original order. If sort is set
        to true, remaining attributes will appear in case-insensitive sorted
        order.

        """
        self.attributes.set_attribute_order(attribute_order, sort)

    def reserialize(self):
        self.xml = self.template.format(self=self)


class Start(StartOrEmpty):
    """
    A start tag: <tag> or <tag att="val">

    """
    __slots__ = []
    template = '<{self.name}{self.attributes.to_xml}>'

    def __init__(self, xml):
        super(Start, self).__init__(xml)


class Empty(StartOrEmpty):
    """
    An empty tag: <tag/> or <tag att="val"/>

    """
    __slots__ = []
    template = '<{self.name}{self.attributes.to_xml}/>'

    def __init__(self, xml):
        super(Empty, self).__init__(xml)


class End(Tag):
    """
    An end tag: </tag>

    """
    __slots__ = []
    template = '</{self.name}>'

    def __init__(self, xml):
        self.xml = xml
        self._name = xml.split('/')[1][:-1].strip()

    def reserialize(self):
        self.xml = self.template.format(self=self)


class Comment(Token):
    """
    A comment: <!-- comment -->

    """
    __slots__ = ['_content']
    template = '<!--{self.content}-->'

    def __init__(self, xml):
        self.xml = xml
        self._content = xml[4:-3]

    def reserialize(self):
        self.xml = self.template.format(self=self)

    @property
    def content(self):
        """content property: the content of the comment"""
        return self._content

    @content.setter
    def content(self, s):
        self._content = s
        self.reserialize()


class PI(Token):
    """
    A processing instruction: <?target instruction?>

    """
    __slots__ = ['_target', '_instruction', '_pseudoattributes']
    template = '<?{self.target}{self.space}{self.instruction}?>'

    def __init__(self, xml):
        self.xml = xml
        self._pseudoattributes = None

        # Parse PI into target and instruction
        #   XML: <?target instruction?> (endslice -> -2 for xml)
        #  SGML: <?target instruction>  (endslice -> -1 for sgml)
        endslice = -2 if xml.endswith('?>') else -1
        try:
            self._target, self._instruction = xml[2:endslice].split(None, 1)
        except ValueError:
            # The PI has a target but no instruction.
            self._target = xml[2:endslice]
            self._instruction = ''
        self._target = self._target.strip()
        self._instruction = self._instruction.strip()

    def __getitem__(self, attribute_name):
        """
        Wait to parse instruction for pseudoattributes until first attribute
        lookup.

        """
        if not self._pseudoattributes:
            self._parse_pseudoattributes()
        return self._pseudoattributes.get(attribute_name)

    def __setitem__(self, attribute_name, value):
        """
        Replace a pseudoattribute if it exists; otherwise append it to the
        end of the instruction.

        """
        if not self._pseudoattributes:
            self._parse_pseudoattributes()
        self._pseudoattributes[attribute_name] = value
        span = self._pseudoattributes.spans.get(attribute_name)
        if span:
            i, j = span
            l = list(self._instruction)
            l[i:j] = ' {attribute_name}="{value}"'.format(**locals())
            self._instruction = ''.join(l)
        else:
            self._instruction += ' {attribute_name}="{value}"'.format(**locals())

        self._locate_pseudoattributes()
        self.reserialize()

    def __delitem__(self, attribute_name):
        if not self._pseudoattributes:
            self._parse_pseudoattributes()

        del self._pseudoattributes[attribute_name]
        span = self._pseudoattributes.spans[attribute_name]
        i, j = span
        l = list(self._instruction)
        del l[i:j]
        self._instruction = ''.join(l)

        self._locate_pseudoattributes()
        self.reserialize()

    def __contains__(self, attribute_name):
        if self._pseudoattributes is not None:
            return attribute_name in self._pseudoattributes
        else:
            return False

    def _parse_pseudoattributes(self):
        """
        Find anything attribute-like in the PI instruction and store as
        attributes.

        """
        self._pseudoattributes = AttributeDict(token=self)

        # Add a spans attribute to store the offsets of pseudoattributes.
        self._pseudoattributes.spans = {}
        self._locate_pseudoattributes()

    def _locate_pseudoattributes(self):
        """
        Find the offsets of pseudoattributes within self._instruction.
        This method is called whenever a pseudoattribute is updated
        or deleted.

        """
        spans = self._pseudoattributes.spans
        pseudoattributes = self._pseudoattributes
        if pseudoattributes:
            # Clear any previous values.
            pseudoattributes.clear()
            spans.clear()

        # Regex AttRE_, requires initial whitespace to match, hence the added
        # ' ', below.
        for m in AttRE_.finditer(' ' + self._instruction):
            attribute_name = m.group('attribute_name')
            pseudoattributes[attribute_name] = m.group('attribute_value')[1:-1]  # strip delimeters
            # Get the span for the attribute using the 'attribute' named group,
            # which includes the preceding whitespace.
            i, j = m.span('attribute')
            # Compensate span for initial space added above.
            if i - 1 < 0:
                # avoid negative slices
                spans[attribute_name] = (0, j - 1)
            else:
                spans[attribute_name] = (i - 1, j - 1)

    def reserialize(self):
        """
        Normalization note: instruction will be normalized to remove initial
        whitespace.

        """
        self._instruction = self._instruction.lstrip()
        self.xml = self.template.format(self=self)

    def is_a(self, token_class, *targets):
        return (isinstance(self, token_class)
                and (not targets or self.target in targets))

    @property
    def target(self):
        """target property: the PI target"""
        return self._target

    @target.setter
    def target(self, val):
        self._target = val
        self.reserialize()

    @property
    def instruction(self):
        """instruction property: the PI instruction"""
        return self._instruction

    @instruction.setter
    def instruction(self, val):
        self._instruction = val
        self._pseudoattributes = None
        self.reserialize()

    @property
    def space(self):
        """
        space property: space necessary to separate target and instruction
        (' ' if instructions is not empty, otherwise '').

        """
        return ' ' if self.instruction.lstrip() else ''


class XmlDecl(PI):
    """
    An XML Declaration: <?xml version="1.0" encoding="utf-8" ...?>

    """
    __slots__ = []

    def __init__(self, xml):
        super(XmlDecl, self).__init__(xml)
        encoding = self['encoding']  # the XmlDecl encoding pseudoattribute
        if encoding:
            Token.encoding = encoding


doctype_parser_ = re.compile("""\
(?xs)
<!DOCTYPE\s+(?P<document_element>\S+)
(?:(?:\s+(?P<id_type>SYSTEM|PUBLIC))(?:\s+(?P<delim>["'])
(?P<id_value>.*?)(?P=delim))?)?
(?:\s*\[(?P<internal_subset>.*)\])?
\s*>
""")


class Doctype(Token):
    """
    A DOCTYPE declaration: <!DOCTYPE tag ...>

    For the following example:

        <!DOCTYPE x:body SYSTEM "/S:/xml/dtd/xhtml1-strict-prefixed.dtd"
          [<!ENTITY abc "xyz">]>

    self.document_element -> 'x:body'
    self.id_type          -> 'SYSTEM'
    self.id_value         -> '/S:/xml/dtd/xhtml1-strict-prefixed.dtd'
    self.internal_subset  -> '<!ENTITY abc "xyz">'

    """
    __slots__ = ['_document_element', '_id_type', '_id_value',
                 '_internal_subset']
    template = '<!DOCTYPE {0}>'

    def __init__(self, xml):
        self.xml = xml
        m = doctype_parser_.search(xml)
        if m:
            d = m.groupdict()
            self._document_element = d['document_element']
            self._id_type = d['id_type'] or ''
            self._id_value = d['id_value'] or ''
            self._internal_subset = d['internal_subset'] or ''
        else:
            raise SecondaryParsingError(
                'unexpected DOCTYPE found: {self.xml}'
                .format(self=self)
            )

    def reserialize(self):
        l = [self.document_element]
        if self._id_type:
            l.append(self._id_type)
        if self._id_value:
            l.append('"{self._id_value}"'.format(self=self))
        if self._internal_subset:
            l.append('[{self._internal_subset}]'.format(self=self))
        self.xml = self.template.format(' '.join(l))

    @property
    def document_element(self):
        """document_element property: the document element name"""
        return self._document_element

    @document_element.setter
    def document_element(self, val):
        self._document_element = val
        self.reserialize()

    @property
    def id_type(self):
        """id_type property: either "PUBLIC" or "SYSTEM" or """""
        return self._id_type

    @id_type.setter
    def id_type(self, val):
        self._id_type = val
        self.reserialize()

    @property
    def id_value(self):
        """id_value property: a public URI or system path"""
        return self._id_value

    @id_value.setter
    def id_value(self, val):
        self._id_value = val
        self.reserialize()

    @property
    def internal_subset(self):
        """internal_subset property: the internal DTD subset"""
        return self._internal_subset

    @internal_subset.setter
    def internal_subset(self, val):
        self._internal_subset = val
        self.reserialize()


class Cdata(Token):
    """
    A CDATA section: <![CDATA[ literal <markup/> ]]>

    """
    __slots__ = ['_content']
    template = '<![CDATA[{self.content}]]>'

    def __init__(self, xml):
        self.xml = xml
        self._content = self.xml[9:-3]

    def reserialize(self):
        self.xml = self.template.format(self=self)

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        self._content = content
        self.reserialize()

    @property
    def escaped_content(self):
        return self._content.replace('&', '&amp;').replace('<', '&lt;')

    def to_text_token(self):
        """
        Escape markup characters and remove CDATA section delimiters, returning
        a Text token.

        """
        return Text(self.escaped_content)


class Error(Token):
    """
    A markup error: Token starts with '<' but does not end with '>'.

    """
    __slots__ = ['span', 'line', 'column']

    def __init__(self, xml, span, line=None, column=None):
        self.xml = xml
        self.span = span  # (start, end) position of token in original string
        # TODO: Adjust tokenizer to add line number and column when desired.
        # (Tokenizer option? Tokenizer subclass? Only calculate when/after an
        # error is encountered?).

    def reserialize(self):
        pass


#
# Utility classes
#

class AttributeDict(OrderedDict):
    """
    A dictionary that preserves the order in which attributes are added.
    If the constructor is passed a dictionary with attributes, the order
    for those attributes will be random; however, attributes added
    subsequently will be ordered following the initial population of
    attributes.

    self.token is a reference back to the Start or Empty token that
    instantiated the AttributeDict; it's used to trigger re-serialization
    in the token when an attribute is changed via token.attributes.

    """
    def __init__(self, d=None, token=None):
        self.token = token
        if d is None:
            d = {}
        OrderedDict.__init__(self, d)

    def __setitem__(self, key, item):
        OrderedDict.__setitem__(self, key, item)
        if self.token:
            self.token.reserialize()

    def __missing__(self, key):
        """Set a default for missing key, rather than raising an exception."""
        return ''

    def __delitem__(self, key):
        """Remove items without raising exceptions."""
        if key in self:
            OrderedDict.__delitem__(self, key)
            if self.token:
                self.token.reserialize()

    def set_attribute_order(self, attribute_order, sort=False):
        """
        Re-order attributes based on attribute_order list. Any attributes
        listed in attribute_order will appear first (and in that order); any
        remaining attributes will follow in original order. If sort is set
        to true, remaining attributes will appear in case-insensitive sorted
        order.

        """
        d = OrderedDict(self)
        self.clear()
        if attribute_order:
            for attribute_name in attribute_order:
                if attribute_name in d:
                    self[attribute_name] = d[attribute_name]
                    d.pop(attribute_name)
        if sort and d:
            # Do a case-insensitive sort on remaining attributes.
            for key in sorted(d, key=str.lower):
                self[key] = d[key]
        elif d:
            # If there are any remaining attribute names in d, add them now.
            for key in d:
                self[key] = d[key]
        del d
        if self.token:
            self.token.reserialize()

    @property
    def to_xml(self):
        """
        Serialize attribute dict to a string of attributes in the form
        ' attr1="value 1" attr2="value 2"'.

        Normalization note: Attribute value delimiters will be normalized to
        double quotes. Any double quotes appearing in attribute values are
        escaped as &quot;.

        """
        try:
            return ''.join(
                ' {attribute_name}="{attribute_value}"'
                .format(
                    attribute_name=attribute_name,
                    attribute_value=attribute_value.replace('"', '&quot;')
                )
                for attribute_name, attribute_value in self.items()
            )
        except AttributeError:
            raise RexlibError(
                'Attribute value was not a string: {self}'
                .format(self=self)
            )

    def has_key_nocase(self, key):
        """A case-insensitive version of 'attribute_name' in self."""
        return key.lower() in [k.lower() for k in self]


#
# Exceptions
#

class RexlibError(Exception):
    """Superclass for all rexlib exceptions."""
    def __init__(self, val):
        self.val = val

    def __str__(self):
        return self.val


class MarkupError(RexlibError):
    """Used for syntax errors in markup."""
    def __str__(self):
        return 'Syntax error in markup: "{self.val}"'.format(self=self)


class WellformednessError(RexlibError):
    """Used for tag-nesting errors."""
    def __str__(self):
        return 'Wellformedness error: "{self.val}"'.format(self=self)


class SecondaryParsingError(RexlibError):
    """Used to indicate errors during secondary parsing."""
    def __str__(self):
        return 'Secondary parsing error: "{self.val}"'.format(self=self)


#
# The tokenizer
#

def tokenize(input, SPE_=XML_SPE_, error_stream=sys.stderr):
    """
    A generator function for classifying each token matched by the REX shallow
    parsing expression.

    Set SPE_=SGML_SPE_ to tokenize SGML.

    """
    tokenizer = SPE_.finditer
    for m in tokenizer(input):
        xml = m.group(0)

        if xml[0] != '<':
            # Token is text
            yield Text(xml)

        else:
            if xml[-1] == '>':
                # Token is markup
                c = xml[1]

                if c not in '/!?':
                    if xml[-2] == '/':
                        yield Empty(xml)
                    else:
                        yield Start(xml)

                elif c == '/':
                    yield End(xml)

                elif c == '!':
                    if xml.startswith('<!--'):
                        yield Comment(xml)
                    elif xml[2] == '[':
                        yield Cdata(xml)
                    elif xml.startswith('<!DOCTYPE'):
                        yield Doctype(xml)

                elif c == '?':
                    if xml.startswith('<?xml '):
                        yield XmlDecl(xml)
                    else:
                        yield PI(xml)
            else:
                # REX's error condition (a markup item not ending with '>').
                yield Error(xml, span=m.span())
                if error_stream:
                    error_stream.write(
                        pprint_error_context(m, 'Syntax error in markup'))


#def stream_tokenizer(fin, SPE_=XML_SPE_):
#    """
#    Tokenize a steam to match objects.
#      - one token lookahead
#      - allows strings to be split into multiple tokens (so that really
#        long strings don't accumulate in memory)
#
#    TODO: There's a bug in the code below that I haven't gone back to find
#        yet, the symptom being overlaping tokens.
#
#    """
#    m_prev = None
#    for s in stream_reader(fin):
#        if m_prev:
#            xml = m_prev.group(0)
#            if xml.startswith('<'):
#                if xml.endswith('>'):
#                    yield m_prev
#                else:
#                    # Incomplete markup; prepend to next buffer.
#                    s = '%s%s' % (xml, s)
#            else:
#                # Allowing text to be yielded as multiple tokens.
#                yield m_prev
#            m_prev = None
#
#        for m in SPE_.finditer(s):
#            xml = m.group(0)
#            if m_prev:
#                yield m_prev
#            m_prev = m
#    if m_prev:
#        yield m_prev


#
# Utility functions
#

def pprint_error_context(m, msg, context_size=30):
    """
    Prettyprint a markup error's context.

    """
    s = m.string
    end = m.end()
    start_ellipsis, end_ellipsis = '', ''
    if end >= context_size:
        start = end - context_size
        if end != context_size:
            start_ellipsis = '...'
    else:
        # Start must not be negative due to the special meaning of negative
        # slice indexes.
        start = 0

    if end + context_size < len(s):
        end_ellipsis = '...'

    before = repr(
        '{0}"{1}'.format(start_ellipsis, s[start:end])
    )[1:-1]

    after = repr(
        '{0}"{1}' .format(s[end:end + context_size], end_ellipsis)
    )[1:-1]

    indent = ' ' * len(before)

    return (
        '\n    {msg}:\n    {before}\n    {indent}{after}\n'
        .format(**locals())
    )
