Tests for token properties
==========================

Tests are in a subdirectory so some path munging is necessary.

>>> import sys
>>> sys.path.append('../..')

Import the token classes.

>>> from rexlib.tokens import *

Token properties
================

Text tokens have a single property: isspace.

>>> token = Text('Here is some text.')
>>> token.xml
'Here is some text.'
>>> token.isspace
False
>>> token.xml = '  \n\t\v  '
>>> token.isspace
True

Start tokens have two properties: name and ns_prefix.

>>> token = Start('<tagname attr1="one" attr2="two">')
>>> token.name
'tagname'
>>> token.xml
'<tagname attr1="one" attr2="two">'
>>> token.name = 'tagname2'
>>> token.xml
'<tagname2 attr1="one" attr2="two">'
>>> token = Start('<namespace:tagname attr1="one" attr2="two">')
>>> token.name
'namespace:tagname'
>>> token.ns_prefix
'namespace'
>>> token.ns_prefix = 'namespace2'
>>> token.xml
'<namespace2:tagname attr1="one" attr2="two">'
>>> token.name = 'tagname2'
>>> token.xml
'<tagname2 attr1="one" attr2="two">'
>>> token.ns_prefix
''

Empty tokens have two properties: name and ns_prefix.

>>> token = Empty('<tagname attr1="one" attr2="two"/>')
>>> token.name
'tagname'
>>> token.xml
'<tagname attr1="one" attr2="two"/>'
>>> token.name = 'tagname2'
>>> token.xml
'<tagname2 attr1="one" attr2="two"/>'
>>> token = Empty('<namespace:tagname attr1="one" attr2="two"/>')
>>> token.name
'namespace:tagname'
>>> token.ns_prefix
'namespace'
>>> token.ns_prefix = 'namespace2'
>>> token.xml
'<namespace2:tagname attr1="one" attr2="two"/>'
>>> token.name = 'tagname2'
>>> token.xml
'<tagname2 attr1="one" attr2="two"/>'
>>> token.ns_prefix
''

End tokens have two properties: name and ns_prefix.

>>> token = End('</tagname>')
>>> token.name
'tagname'
>>> token.xml
'</tagname>'
>>> token.name = 'tagname2'
>>> token.xml
'</tagname2>'
>>> token.name = 'namespace:tagname'
>>> token.xml
'</namespace:tagname>'
>>> token.name
'namespace:tagname'
>>> token.ns_prefix
'namespace'
>>> token.name = 'tagname2'
>>> token.xml
'</tagname2>'
>>> token.ns_prefix
''

Comment tokens have a single property: content.

>>> token = Comment('<!-- A comment. -->')
>>> token.content
' A comment. '
>>> token.xml
'<!-- A comment. -->'
>>> token.content = 'A different comment.   '
>>> token.xml
'<!--A different comment.   -->'

Processing instructions (PIs) have two properties: target and instruction.

>>> token = PI('<?targetname instructions go here?>')
>>> token.target
'targetname'
>>> token.instruction
'instructions go here'
>>> token.xml
'<?targetname instructions go here?>'
>>> token.target = 'targetname2'
>>> token.xml
'<?targetname2 instructions go here?>'
>>> token.instruction = 'other instructions'
>>> token.xml
'<?targetname2 other instructions?>'

PIs also recognize pseudo-attributes in the instruction.

>>> token = PI('<?targetname pseudoattr1="value1" pseudoattr2="value2 value3"?>')
>>> token.target
'targetname'
>>> token.instruction
'pseudoattr1="value1" pseudoattr2="value2 value3"'
>>> token['pseudoattr1']
'value1'
>>> token['pseudoattr1'] = 'value4'
>>> token.xml
'<?targetname pseudoattr1="value4" pseudoattr2="value2 value3"?>'
>>> token['pseudoattr3'] = 'value5'
>>> token.xml
'<?targetname pseudoattr1="value4" pseudoattr2="value2 value3" pseudoattr3="value5"?>'
>>> 'pseudoattr2' in token
True
>>> 'pseudoattr4' in token
False
>>> del token['pseudoattr2']
>>> token.xml
'<?targetname pseudoattr1="value4" pseudoattr3="value5"?>'
>>> token.instruction = 'simple instruction'
>>> 'pseudoattr1' in token
False
>>> token.xml
'<?targetname simple instruction?>'
>>> token['att1'] = 'one'
>>> token['attr2'] = 'two'
>>> token.xml
'<?targetname simple instruction att1="one" attr2="two"?>'
>>> token.instruction
'simple instruction att1="one" attr2="two"'

XML Declarations (XmlDecl) are a subclass of PI and so have the same
properties.

>>> token = XmlDecl('<?xml version="1.0" encoding="utf-8"?>')
>>> token.target
'xml'
>>> token.instruction
'version="1.0" encoding="utf-8"'
>>> token['version']
'1.0'

Doctypes have four properties: document_element, identifier_type, identifier,
and internal_subset.

>>> token = Doctype('<!DOCTYPE x:body SYSTEM "/S:/xml/dtd/xhtml1-strict-prefixed.dtd" [<!ENTITY abc "xyz">]>')
>>> token.document_element
'x:body'
>>> token.id_type
'SYSTEM'
>>> token.id_value
'/S:/xml/dtd/xhtml1-strict-prefixed.dtd'
>>> token.internal_subset
'<!ENTITY abc "xyz">'
>>> token = Doctype('<!DOCTYPE x:body SYSTEM "/S:/xml/dtd/xhtml1-strict-prefixed.dtd" [<!ENTITY abc "xyz">]>')

>>> token.document_element = 'html'
>>> token.id_type = 'PUBLIC'
>>> token.id_value = '-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'
>>> token.internal_subset = ''
>>> token.xml
'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'


CDATA sections (Cdata) have two properties: content and escaped_content.

>>> token = Cdata('<![CDATA[ literal <markup/> ]]>')
>>> token.to_text_token()
Text(' literal &lt;markup/> ')
>>> token.content
' literal <markup/> '
>>> token.escaped_content
' literal &lt;markup/> '
>>> token.content = 'abc'
>>> token.xml
'<![CDATA[abc]]>'

Error tokens add a span attribute, which shows the token's location in the original string.

>>> s = '<p>Some <i text.</p>'
>>> tokens = tokenize(s, error_stream=None)
>>> for token in tokens:
...     if token.is_a(Error):
...         print repr(token)
...         print token.span
...
Error('<i ')
(8, 11)
>>> s[8:11]
'<i '

In the example above, the tokenizer will also report syntax errors on stderr, showing the exact location of the error. ::

    Syntax error in markup:
    "<p>Some <i
                text.</p>"

This behavior can be disabled by setting the tokenizer's error_stream to None.

>>> tokens = tokenize(s, error_stream=None)
