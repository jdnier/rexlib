Tests for token interfaces
==========================

Tests are in a subdirectory so some path munging is necessary.

    >>> import sys
    >>> sys.path.append('../..')

Import the token classes.

	>>> from rexlib.tokens import *

Token
-----

All tokens inherit MAX_REPR_WIDTH from Token, which is used to limit the repr
length. None is used as a sentinal value meaning no limit (display full token).

    >>> token = Text('.' * 128)
    >>> Token.MAX_REPR_WIDTH
    60
    >>> repr(token)
    "Text('...............................................................')"
    >>> len(repr(token))
    71
    >>> Token.MAX_REPR_WIDTH = 20
    >>> repr(token)
    "Text('.......................')"
    >>> len(repr(token))
    31
    >>> Token.MAX_REPR_WIDTH = 0 
    >>> repr(token)
    "Text('...')"
    >>> len(repr(token))
    11
    >>> Token.MAX_REPR_WIDTH = None
    >>> len(repr(token))
    136


Start
-----

Start and Empty tokens use a dictionary interface for attributes. 

    >>> token = Start('<p class="subhead" style="font-weight: bold">')
    >>> 'style' in token
    True
    >>> del token['style']
    >>> 'style' in token
    False
    >>> del token['style']

PI
--

PIs have non-exception-throwing convenience methods like with Start/Empty tags,
only with pseudoattributes.

    >>> token = XmlDecl('<?xml version="1.0" encoding="utf-8"?>')
    >>> 'version' in token
    True
    >>> 'standalone' in token
    False
    >>> del token['encoding']
    >>> 'encoding' in token
    False
    >>> token
    XmlDecl('<?xml version="1.0"?>')
    >>> dict(token._pseudoattributes)
    {'version': '1.0'}

Comment
-------

Comments have no methods of their own, only a content property.

Cdata
-----

Cdata tokens have a to_text_token() method that escapes markup characters, 
removes CDATA section delimeters, and returns a Text token.

    >>> token = Cdata('<![CDATA[ literal <markup/> ]]>')
    >>> token.to_text_token()
    Text(' literal &lt;markup/> ')

AttributeDict
-------------

AttributeDict has a to_xml property that is used for serialization; it's a 
property instead of a method so it can be called from format strings
(e.g., '{self.attributes.to_xml}').

    >>> ad = AttributeDict(dict(id='123', style='padding: 0px;'))
    >>> ad.to_xml
    ' style="padding: 0px;" id="123"'

TODO: Use 'in' instead of has_key() (OrderedDict) and change has_key_nocase()
to has_key().
