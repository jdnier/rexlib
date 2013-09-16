======
rexlib
======

``rexlib`` is is a pure Python module for working with tokenized XML. It allows you to iterate through the tokens of an XML document just as you would iterate through items in a list and provides an API for manipulating tokens. By creating simple generator functions, you can create very focused XML filters that can be chained together to create surprisingly complex, robust, and efficient XML transformations.

``rexlib`` works at the lexical level and is not necessarily concerned with well formedness or validity. It really shines when you want to make precisely targeted changes to an XML document without disturbing the rest of the document. It's also effective when you want a *simple* way to extract element and attribute content from XML. It's well suited for working with XML that is not well formed, XML that contains syntax errors in markup, and XML where you want control over lexical details that are normally discarded by XML parsers. Text or source code containing islands of markup can also be usefully manulipulated. 

Because ``rexlib`` is relatively simple and implemented in Python, you can use it to create practical, roll-your-own solutions.

``rexlib`` relies on Robert D. Cameron's `REX shallow parsing`_ regular expression for tokenizing XML. REX does the tokenizing; ``rexlib`` is all about making it easy to work with tokenized XML. Combining regex-based shallow parsing with secondary parsing of individual tokens leads to an XML processing API that's more procedural in flavor than event-based and tree-based XML APIs and should feel comfortable to those accustomed to doing text processing.

__
.. _REX shallow parsing: http://www.cs.sfu.ca/~cameron/REX.html


``rexlib`` Basics
=================

``rexlib`` isn't an XML API per se, however it does provide an API for tokens. Each token is a instance of one of the following classes:

    ``Text``
      Plain text: a run of text not containing the ``<`` character

    ``Start``
      A start tag: ``<tag>`` or ``<tag att="val">``

    ``Empty``
        An empty tag: ``<tag/>`` or ``<tag att="val"/>``

    ``End``
        An end tag: ``</tag>``

    ``Comment``
        A comment: ``<!-- comment -->``

    ``PI``
        A processing instruction: ``<?target instruction?>``

    ``XmlDecl``
        An XML Declaration: ``<?xml version="1.0" ...?>``

    ``Doctype``
        A DOCTYPE declaration: ``<!DOCTYPE tag ...>``

    ``Cdata``
        A CDATA section: ``<![CDATA[ literal <markup/> ]]>``

    ``Error``
        A markup error: a token starting with ``<`` that does not end with 
        ``>``

All token classes are subclasses of the abstract class ``Token``. Here is the class hierarchy for tokens::

                                 [Token]
                                    |
    -------------------------------------------------------------------
    |         |           |         |          |           |          |
  Text      [Tag]      Comment      PI      Doctype      Cdata      Error
              |                     |
         ------------            XMLDecl
         |          |
  [StartOrEmpty]   End            
         |
     ---------
     |       |
   Start   Empty

  [...] = abstract class

Let's tokenize some XML and see what we get:

>>> from rexlib import *
>>> s = '<p>Hello <pre>rexlib</pre> World!</p>'
>>> tokens = tokenize(s)

Note that ``tokenize()``, above, is a generator function; it returns a generator object that yields tokens.

>>> type(tokens)
<type 'generator'>

The easiest way to see what's inside ``tokens`` is to wrap it in ``list()``.

>>> print list(tokens)
[Start('<p>'),
 Text('Hello '),
 Start('<pre>'),
 Text('rexlib'),
 End('</pre>'),
 Text(' World!'),
 End('</p>')]

You can also get at the tokens by iterating with a ``for`` loop

>>> tokens = tokenize(s)
>>> for token in tokens:
...     print token
... 
Start('<p>')
Text('Hello ')
Start('<pre>')
Text('rexlib')
End('</pre>')
Text(' World!')
End('</p>')

or you can invoke the generator's ``next()`` method

>>> tokens = tokenize(s)
>>> tokens.next()
Start('<p>')
>>> tokens.next()
Text('Hello ')

or by using a list comprehension.

>>> tokens = tokenize(s)
>>> [ token.xml for token in tokens ]
['<p>', 'Hello ', '<pre>', 'rexlib', '</pre>', ' World!', '</p>']

Note ``token.xml``, in the list comprehension above. All subclasses of Token have an ``xml`` attribute that stores the current serialization of the token. When each token is instantiated, it is parsed into its components (tag name, attributes, etc.). Unless you modify the token, ``token.xml`` is just the original (unaltered) XML string. As soon as you change the token in some way, the token is reserialized (rebuilt from its components). Reserialization doesn't happen until you make a change (or manually call token.reserialize()). For example,

>>> token = Start('<p>')
>>> token.xml
'<p>'

>>> token['class'] = 'block'  # assignment triggers reserialization
>>> token.xml
'<p class="block">'

>>> token.name = 'para'  # assignment triggers reserialization
>>> token.xml
'<para class="block">'

It's worth noting my use of ``Start('<p>')`` in the first line of the example above. You'll rarely instantiate a token manually like this. Normally you'll just use tokenize(). But for testing, its easier to type ``Start('<p>')`` than

>>> tokenize('<p>').next().xml
'<p>'

The main advantage to using tokenize() is that it identifies the type of token (text or markup) and instantiates the proper class. It would be very tedious if you had to create new XML by typing

>>> tokens = iter([Start('<p>'), Text('ouch!'), End('</p>')])

It's much easier to type

>>> tokens = tokenize('<p>ahh!</p>')

When experimenting in the interactive interpreter, it's almost always better to assign your XML string to a variable. This way you can easily refresh your token generator. For example,

>>> s = '<p>some xml string ...</p>'
>>> tokens = tokenize(s)
>>> tokens.next()
Start('<p>')
>>> tokens.next()
Text('some xml string ...')

Say now that you want to start over in order to test something else. All you have to do is refresh the generator.

>>> tokens = tokenize(s)
>>> tokens.next()
Start('<p>')

Don't worry, this doesn't get expensive. Because of the lazy nature of generators/iterators, you're only tokenizing as much as you consume. ``tokenize(s)`` costs nothing. It's not until you start consuming tokens that any actual work happens. The example above is similar in effect to doing a ``seek(0)`` on a file object. For example,

>>> fin = open('some_file')
>>> print fin.read(12)
>>> fin.seek(0)  # go back to beginning of file

If you want to loop over the same sequence of tokens several times, you can also convert the generator to a list and then emulate a token generator using iter().

>>> tokens = tokenize(s)
>>> token_list = list(tokens)
>>> tokens = iter(token_list)  # first pass over sequence
>>> tokens.next()
Start('<p>')
>>> tokens = iter(token_list)  # second pass over sequence
>>> tokens.next()
Start('<p>')

The advantage here is that the token list is reusable while a token generator would be spent after the first pass. To pass a token list (rather than a token generator) to a ``rexlib`` filter (explained below) you'll usually need to wrap it with iter().


Token Filters
=============

Here's a simple example to whet your appetite; it's a token filter that changes tag names according to a mapping you supply.

>>> def tag_filter(tokens, mapping):
...     """Rename tags per supplied mapping."""
...     for token in tokens:
...         if token.is_a(Tag) and token.name in mapping:
...             token.name = mapping[token.name]
...         yield token
... 

The filter doesn't need to differentiate start, end, or empty tags; it only cares that any subclass of ``Tag`` has a ``name`` attribute that may need to be updated. Here's an example of how you might use ``tag_filter``:

>>> s = '<p>...<ex/><br/>...<ex>...</ex>...</p>'
>>> d = { 'p': 'para',
...      'ex': 'extract'}
>>> tokens = tokenize(s)
>>> tokens = tag_filter(tokens, d)
>>> s = concat_tokens(tokens)
>>> s
'<para>...<extract/><br/>...<extract>...</extract>...</para>'


Extracting Content from XML
===========================

Extracting text or attribute values from XML is quite straightforward. Just iterate through the tokens looking for what you're interested in and accumulate it in whatever way is convenient.

Example 1
~~~~~~~~~

Here's a ``rexlib`` solution to `Nelson Minar's`_ problem extracting 'xmlUrl' attributes from an OPML file:

>>> from rexlib import *
>>> s = open('foo.opml').read()
>>> tokens = tokenize(s)
>>> for token in tokens:
...     if token.is_a(StartOrEmpty) and token.has_attribute('xmlUrl'):
...         print token['xmlUrl']

You could also write a simple generator function.

>>> def extract_xmlUrl_atts(tokens):
...     for token in tokens:
...         if token.is_a(StartOrEmpty) and token.has_attribute('xmlUrl'):
...             yield token['xmlUrl']
...
>>> tokens = tokenize(s)
>>> print list(extract_xmlUrl_atts(tokens))

__
.. _Nelson Minar's: http://www.nelson.monkey.org/~nelson/weblog/tech/python/xpath.html


Example 2
~~~~~~~~~

Here's a simple extraction problem lifted from an entry (Jan. 23, 2005) in `Uche Ogbuji's O'Reilly weblog`_: 

    The idea is simply to print all verses containing the word 'begat' [in] `Jon Bosak's Old Testament in XML`_, a 3.3MB document. A quick note on the characteristics of the file: it contains 23145 v elements containing each Bible verse and only text: no child elements. The v elements and their content represent about 3.2 of the file's total 3.3MB.

The fact that the `v` elements contain only text makes this problem even easier. All we need to do is tokenize the ot.xml file, iterate through the tokens looking for ``<v>`` start tags, grab the next token (which we know will be text) and check it for 'begat'; if 'begat' is found, append it to a list. Here's the code:

>>> from rexlib import *
>>> 
>>> ot = open('ot.xml').read()
>>> 
>>> l = []
>>> 
>>> tokens = tokenize(ot)
>>> for token in tokens:
>>>     if token.is_a(Start, 'v'):
>>>             text = tokens.next().xml
>>>             if 'begat' in text:
>>>                     l.append(text)
>>> print '\n'.join(l)

To make this problem a little more realistic, let's pretend the document is marked up a little more richly and that the ``v`` elements contain mixed content (i.e., text and child elements). Once we find a ``<v>`` start tag, we'll need a way to find its matching end tag so that we can examine the full content of the element. ``accumulate_tokens()`` is the ``rexlib`` function we'll use; it's another generator function. Here's the code leading up to using ``accumulate_tokens()``::

    tokens = tokenize(ot)  # remember to reset the token generator
    for token in tokens:
        if token.is_a(Start, 'v'):
            v_tokens = accumulate_tokens(token, tokens)

``accumulate_tokens()`` looks at its first argument (which needs to be a ``Start`` or ``Empty`` token) and iterates through its second argument looking for the matching end token. ``accumulate_tokens()`` is a generator function, which means it returns a generator. That generator is now bound to ``v_tokens``, above.

Remember that generators are lazy: no work is done until you start iterating through them. It's kind of hard to wrap your brain around at first but, at this point in the code, we haven't actually accumulated any tokens. The simplest way to force evaluation is to wrap ``v_tokens`` in a ``list()``. ::

    .       v_list = list(v_tokens)  # unwind the generator

We now have accumulated the tokens that comprise the current ``v`` element and they exist as a list bound to ``v_list``. It may be worth pointing out that ``v_tokens`` is now spent. ``accumulate_tokens()`` advanced through ``tokens`` until it found the matching end tag for ``token``. When the ``for`` loop continues, it implicitly calls ``tokens.next()``, picking up where we left off (the token following the end tag of the element we just accumulated).  

Now it's time to do something with the ``v`` element. Let's say the ``v`` element looks like the following::

    <v>And <a href="#Seth">Seth</a> lived an hundred and five years, and 
       begat <a href="#Enos">Enos</a>:</v>

Here it would be safe to concatenate the tokens into an XML string (markup included) and search for "begat". However, since we're probably only interested in finding "begat" in the text and would rather avoid finding begat, say, in an attribute value, we need a way to strip the markup from the text. The ``rexlib`` function ``concat_tokens()`` will handle both cases.

>>> s = ('<v>And <a href="#Seth">Seth</a> lived an hundred and five years, '
...      'and begat <a href="#Enos">Enos</a>:</v>')

>>> tokens = tokenize(s)
>>> concat_tokens(tokens)  # includes markup
'<v>And <a href="#Seth">Seth</a> lived an hundred and five years, and begat <a href="#Enos">Enos</a>:</v>'

>>> tokens = tokenize(s)
>>> concat_tokens(tokens, Text)  # filters out all but Text tokens
'And Seth lived an hundred and five years, and begat Enos:'

The second argument to ``concat_tokens`` is used as a filter: it will preserve tokens of the type specified. If you wanted only the start and end tags, you could use

>>> tokens = tokenize(s)
>>> concat_tokens(tokens_list, (Start, End))
'<v><a href="#Seth"></a><a href="#Enos"></a></v>'

(Implementation detail: the second argument to ``concat_tokens`` is passed through as the second argument to ``isinstance()``, which requires the tuple.)

Let's restate the previous code and finish it up.

>>> l = []  # to hold the 'begat' verses
>>> tokens = tokenize(ot)
>>> for token in tokens:
>>>     if token.is_a(Start, 'v'):
>>>         v_tokens = accumulate_tokens(token, tokens)
>>>         v_list = list(v_tokens)
>>>         if 'begat' in concat_tokens(v_list, Text):  # search text only
>>>             l.append(concat_tokens(v_list))  # append text and markup

Simple extraction is one possibility. But with just a little additional work, we can turn this code into a token filter that instead enriches the OT markup by adding an attribute to ``v`` elements that contain 'begat'.

>>> def annotate_begat(tokens):
...     for token in tokens:
...         if token.is_a(Start, 'v'):
...             v_tokens = accumulate_tokens(token, tokens)
...             v_list = list(v_tokens)
...             if 'begat' in concat_tokens(v_list, Text):
...                 # add an annotate attribute to <v>
...                 token['annotate'] = 'begat'  # token and v_list[0] are
...                                              # the same object; see why?
...             for token in v_list:
...                 yield token  # yield the element we accumulated
...         else:
...             yield token  # yield all other tokens
... 

Note the use of ``yield``, making ``annotate_begat()`` a generator function. 

Here we have a very focused filter that does one thing well. It's almost always better to keep your filters simple and single-minded. You can chain multiple filters together with very little speed penalty. Except for when you have to use ``list()`` to accumulate tokens, the effect of chaining generators is that each token travels through the entire chain of filters before the next token starts, similar to a Unix pipline. As much as it seems like you must be iterating over the same sequence multiple times, it's more like you're iterating over the sequence just once, with each token percolating through the filter chain. 

>>> tokens = tokenize(s)
>>> tokens = annotate_begat(tokens)
>>> # tokens = annotate_desciple(tokens)  # Here's how you would
>>> # tokens = some_other_filter(tokens)  # chain filters.
>>> concat_tokens(tokens)
'<v annotate="begat">And <a href="#Seth">Seth</a> lived an hundred and five years, and begat <a href="#Enos">Enos</a>:</v>'

In fact, you'll need to keep in mind the lazy execution when wrapping filter chains in ``try``/``except`` blocks. As an example, let's add a filter that raises an exception:

>>> def error_filter(tokens):
...     for token in tokens:
...             raise RuntimeError, 'hit error'
...             yield token
...
>>> tokens = tokenize(s)
>>> try:
...     tokens = annotate_begat(tokens)
...     tokens = error_filter(tokens)
... except RuntimeError, value:
...     print 'Caught error:', value
... 
>>> concat_tokens(tokens)
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  File "rexlib/token_filters.py", line 29, in concat_tokens
    return ''.join([ token.xml for token in tokens ])
  File "<stdin>", line 2, in error_filter
  File "<stdin>", line 2, in annotate_begat
  File "<stdin>", line 3, in error_filter
RuntimeError: hit error

Notice that the exception wasn't caught. That's because the generators don't "unwind" until ``concat_tokens(tokens)`` is run. ``concat_tokens()`` isn't magical, it's just the first bit of code that actually forces iteration though the tokens.


There have been occasions where I've writen token filters thinking as if each filter iterates through the tokens completely before moving on to the next filter, only to find unexpected output. If you have a filter that depends on a previous filter having finished it's job, you'll need to force execution by manually iterating... or wrapping with list()... ::

    tokens = tokenize(s)
    
    tokens = filter1(tokens)
    tokens = filter2(tokens)
    
    token_list = list(tokens)  # causes filter1 and filter2 to run to completion
    tokens = iter(token_list)
    
    tokens = filter3(tokens)
    tokens = filter4(tokens)
    
    s = concat_tokens(tokens)  # causes filter3 and filter4 to run to completion
    
    Or, alternately,
    
    tokens = tokenize(s)
    
    tokens = filter1(tokens)
    tokens = filter2(tokens)
    
    for token in tokens:
        ...  # a for loop also causes filters1 and filter2 to run to completion

Keep in mind that using list(tokens), not to mention concat_tokens(), will load all the tokens into memory at once; this could consume a lot of memory if you're working with very large XML files. Simple token filters are very memory friendly and fast, much like a pipeline!

__
.. _Uche Ogbuji's O'Reilly weblog: http://www.oreillynet.com/pub/wlg/6291
.. _Jon Bosak's Old Testament in XML: http://www.ibiblio.org/bosak/xml/eg/religion.2.00.xml.zip


API for Tokens
==============

Each token type has it's own API (methods, properties, attributes).

``Token``
=========

All tokens inherit from an abstract base class, ``Token``, which provides the following informal interface:

Methods:
~~~~~~~~
    ``is_a(token_class)``
        Checks to see whether the current token (self) is an instance of ``token_class``.

    ``reserialize()``
        Rebuilds the token's ``xml`` attribute based on internal state. Whenever a change is made to the token, ``reserialize()`` is automatically called. About the only time you'll  call ``reserialize`` manually is when you've changed the ``template`` class attribute and want the token to reflect the change. See the ``template`` attribute, described below. 

    ``__repr__()``
        Controls the representation of the the token in the interactive interpreter. By default, shows only the first 45 characters of the ``xml`` attribute (controlled by the class attribute ``MAX_REPR_WIDTH``); for example,

        >>> Start('<very-long-tag-name att1="value1" att2="value2" att3="value3">')
        Start('<very-long-tag-name att1="value1" att2="value2" ...')

Attributes:
~~~~~~~~~~~
    ``xml``
        Stores the serialized form of the token.
 
    ``template``
        String template used for reserialization. ``template`` is a class attribute, shared by all instances. If, for example, you wanted ``Empty`` tags to serialize as ``<tag />`` rather than ``<tag/>`` you could set the class attribute ``Empty.template = '<%s%s />`` and write a token filter that invokes each ``Empty`` token's ``reserialize()`` method. Setting ``Empty.template`` does not cause reserialization automatically because the class doesn't hold references to its instances. The default value for ``Empty.template`` is ``<%s%s/>``.

	``encoding``
		Stores the encoding declared in a document's XML declaration. Defaults to sys.getdefaultencoding. [TODO: What about processing fragments -- only use it if you want to be encoding-aware? How to handle fragments if internal Unicode fanciness is happening?]

``Text``
--------

To the basic interface inherited from ``Token``, the ``Text`` class adds one property, ``isspace``. ``Text`` is the only token class that does not implement a ``reserialize()`` method -- not much point since it, by definition, doesn't contain any markup. To modify a ``Text`` token, just assign directly to its ``xml`` attribute.

Properties:
~~~~~~~~~~~
    ``isspace``
        The value of ``isspace`` will be ``True`` if the token contains only whitespace; it's False otherwise.


``Start``, ``Empty``, \[``StartOrEmpty``\]
------------------------------------------

The interface for ``Start`` and ``Empty`` tokens is the same. Both inherit from the abstract ``StartOrEmpty`` class. While you'll never see an instance of ``StartOrEmpty``, it is useful when doing isinstance() tests. For example, 

>>> start_token = Start('<tag att="value">')
>>> empty_token = Empty('<tag att="value"/>')
>>> start_token.is_a(StartOrEmpty)                               
True
>>> empty_token.is_a(StartOrEmpty)
True
>>> start_token.is_a(Empty)
False

Note that ``token.is_a(Start)`` is equivalent to ``isinstance(token, Start)``, however ``is_a()`` reads better (to me at least) and, for ``Start``, ``Empty``, and ``End`` tokens (subclasses of ``Tag``), ``is_a()`` lets you add one or more tag names as arguments to refine the test.

>>> token = Start('<p>')
>>> isinstance(token, Start)
True
>>> token.is_a(Start, 'p')     
True
>>> token.is_a(Start, 'a', 'body', 'span')
False

For processing instructions, ``is_a()`` lets you specify targets (rather than tag names).

Another useful idiom when you want to find one of a number of tags is

>>> tag_names = ['p', 'a', 'span', 'i', 'b', 'body']
>>> token.is_a(Start, *tag_names)
True

Remember, ``StartOrEmpty`` will match both start and empty tags; ``End`` will match end tags; and ``Tag`` will match start, empty, and end tags.

>>> token.is_a(StartOrEmpty), token.is_a(End), token.is_a(Tag)
(True, False, True)

Methods:
~~~~~~~~
    ``is_a(token_class, *names)``
        Checks to see whether the current token (``self``) is an instance of ``token_class``. You can also pass one or more tag names as arguments to refine the test.

    ``has_attribute(attribute_name)``
        Checks if token has an attribute named ``attribute_name``; returns ``True`` or ``False``.

    ``delete_attribute(attribute_name)``
        Deletes attribute named ``attribute_name`` if it exists; no error is raised if it doesn't exist.

    ``set_attribute_order(attribute_order=[], sort=False)``
        Re-orders attributes based on ``attribute_order`` list. Any attributes listed in ``attribute_order`` will appear first (and in that order); any remaining attributes will follow in original order. If ``sort`` is set to ``True``, any *remaining* attributes will appear in case-insensitive sorted order. If you want to sort all attributes, use either ``set_attribute_order(sort=True)`` or ``set_attribute_order(attribute_order=[], sort=True)``.

    ``__getitem__``, ``__setitem__``, and ``__delitem__``
        Attributes can be assigned, retrieved, and deleted using index notation 
        on each token.

        >>> token = Start('<p>')
        >>> token['class'] = 'block'  # assign attribute
        Start('<p class="block">')

        >>> token['class']  # get attribute
        'block'
        
        >>> del token['class']  # delete attribute
        >>> token  
        Start('<p>')
    
        It may be be less error prone to use ``delete_attribute('attribute_name')`` since it won't raise an error if the attribute doesn't exist.

        >>> token.delete_attribute('class')

Attributes:
~~~~~~~~~~~
    ``attributes``
        A dictionary-like object that preserves attribute order. You'll usually get and set attributes using index notation. See ``__getitem__`` description above for examples.

        ``attributes`` is an instance of ``AttributeDict``, which adds three methods to the usual dictionary interface: ``has_key_nocase()``, which simplifies matching attributes with inconsistent case; ``set_attribute_order()``, which lets you specify attribute order; and ``toXml()``, which serializes the attributes as XML.

        >>> token = Start('<p Class="block" indent="no">')
        >>> token.attributes
        {'Class': 'block', 'indent': 'no'}
        >>> token.attributes.has_key_nocase('class')
        True

        >>> token.set_attribute_order(['indent', 'Class'])
        >>> token
        Start('<p indent="no" Class="block">')

        >>> token.attributes.toXml()
        ' Class="block" indent'
        >>> token.template % (token.name, token.attributes.toXml())
        '<p Class="block" indent="no">'

        Note that ``toXml()`` normalizes attribute value delimiters to double quotes. Any double quotes appearing in attribute values are escaped as &quot;. Adjust the source if you prefer single quotes.

        >>> token = Start("""<p x='funky "quoted" attribute'>""")
        >>> token
        Start('<p x=\'funky "quoted" attribute\'>')
        >>> token.attributes
        {'x': 'funky "quoted" attribute'}
        >>> token.attributes.toXml()
        ' x="funky &quot;quoted&quot; attribute"'

Note that this normalization only happens if the token is modified (which triggers the ``reserialize()`` method).


Properties:
~~~~~~~~~~~
   ``name``
        The tag name.

    ``ns_prefix``
        The namespace prefix, if present; an empty string otherwise. 

        *Namespaces disclaimer:* Since ``rexlib`` works mostly at the lexical level, it doesn't try to be sophisticated about namespaces. Tag names are treated as strings; you're free to map them to URIs and track scope as part of a token filter. However, if namespaces are important to your application, it wouldn't be hard for you to extend ``rexlib``, say to make ``is_a()`` tests work something like ``token.is_a(Start, (HTML_URI, 'p'))`` to match ``<html:p>`` and where "html" is actually mapped to a URI for purposes of comparison. Of course, each token would then need store the namespace mappings that were in effect when it was instantiated. More practically, the Tag class could be used to store all known namespace mappings as they're encountered (with the mapping being visible to the ``Start``, ``Empty``, and ``End`` subclasses); this would be much lighter-weight solution. The whole point of ``rexlib`` for me was that it was easy to extend whenever a new problem proved akward to solve with XSLT, etc. So don't be afraid to read the source and modify it to solve the problems you face.


Exploring the token APIs
========================

``Start``
~~~~~~~~~

Let's first take a look at the ``Start`` token:

>>> s = '<p class="text" indent="no">'
>>> token = Start(s)
>>> token
Start('<p class="text" indent="no">')

>>> dir(token)  # the list below is trimmed
['attributes', 'delete_attribute', 'has_attribute', 'is_a', 'local_part', 
 'name', 'prefix', 'reserialize', 'set_attribute_order', 'template', 'xml']

Here are examples of how the methods and attributes for ``Start`` tokens are used:

>>> token.xml
'<p class="text" indent="no">'

>>> token.name
'p'

Note that ``name`` is a property rather than a simple attribute so that when you assign a new name

>>> token.name = 'para'

reserialization is triggered.

>>> token.xml
'<para class="text" indent="no">'

Another property is ``ns_prefix``.

>>> token = Start('<xhtml:p>') 
>>> token.ns_prefix  
'xhtml'

>>> token.ns_prefix = 'html'
>>> token.xml
'<html:p>'

>>> token.ns_prefix = ''
>>> token.xml
'<p>'

You can also change the namespace prefix by changing ``token.name``.

>>> token.name = 'html:p'
>>> token.xml
'<html:p>'


XML attributes are stored in a special dictionary that keeps track of order.

>>> token.attributes
{'class': 'text', 'indent': 'no'}
>>> token.has_attribute('class')
True
>>> token.delete_attribute('class')
>>> token.xml
'<p indent="no">'

>>> token.is_a(Start)
True
>>> token.is_a(Start, 'p', 'para')
True

>>> token['class'] = 'newer_text'          
>>> token.xml
'<p indent="no" class="newer_text">'

>>> token.set_attribute_order(['class', 'indent'])
>>> token.xml
'<p class="newer_text" indent="no">'

>>> token.name = 'para'
>>> token.xml
'<para class="newer_text" indent="no">'

>>> token.template
'<%s%s>'
>>> token.template % (token.name, token.attributes.toXml())
'<para class="newer_text" indent="no">'


``Empty``
~~~~~~~~~

The ``Empty`` token is exactly the same as ``Start`` except for it's ``template`` class attribute.

>>> Start.template
'<%s%s>'
>>> Empty.template
'<%s%s/>'

``End``
~~~~~~~

The ``End`` token does not have an ``attributes`` attribute and has a different ``template`` class attribute.

>>> End.template
'</%s>'

``Text``
~~~~~~~~

The ``Text`` token is the most primitive. It's has only one attribute.

>>> token = Text('Here is some text')
>>> token.xml
'Here is some text'

It also has an ``isspace`` property, used to test whether the token is all whitespace.

>>> token.isspace
False
>>> Text('  \t\r \n').isspace  
True

``PI``
~~~~~~

Here are the basics of the ``PI`` token.

>>> s = '<?xml version="1.0" encoding="utf-8"?>'
>>> token = PI(s)

``PI`` tokens have two useful attributes, ``target`` and ``instruction``.

>>> token.target
'xml'
>>> token.instruction
'version="1.0" encoding="utf-8"'

Processing instructions will sometimes contain pseudo-attributes, as in the example above. You can read a processing instruction's pseudo-attributes just like you would attributes

>>> token['version']                   
'1.0'
>>> token['encoding']
'utf-8'

Note, however, that the ``PI`` tokens pseudo attributes are read only.

>>> token['encoding'] = "ascii"
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
TypeError: object does not support item assignment

If you want to change a pseudo-attribute, you'll need to rewrite the whole instruction. For example

>>> token.instruction = 'version="1.0" encoding="ascii"'
>>> token.xml
'<?xml version="1.0" encoding="ascii"?>'


``XmlDecl``
~~~~~~~~~~~~

``Doctype``
~~~~~~~~~~~

``Cdata``
~~~~~~~~~

``Comment``
~~~~~~~~~~~

``Error``
~~~~~~~~~


TO DO:
======

Remaining tokens, above.

Explain the UTF-8 expectations of the SPE. What about codecs.open() vs converting to Unicode for each token separately? What about changing the SPE to use Unicode? Don't forget PCRE's DFA algorithm -- how to access pcre_test from Python?

Document Token.encoding and Doctype trigger that updates class attribute.

Show examples of enumerate() idiom and why it's useful: lets you do lookaheads by calling next() within a loop but makes it easy to keep track of current index while also letting you use continue to skip over some code but continue looping.

Add a Limitations section, giving examples where token processing can become onerous or error-prone.

Explain that SGML can be tokenized by using a modified shallow parsing expression, providing that the SGML resembles XML (handles SGML's different PI and empty tag syntax -- although lack of well-formedness makes SGML processing not terribly fun: show example of making SGML well-formed (sgml -> xml), etc.). (Add rex_sgml.py?)

Note that assigning directly to token.xml (except for ``Text``) should not be done if there's a chance that reserialization might be triggered later on: ``reserialize()`` overwrites ``token.xml`` based on internal state. (I'd rather not make ``token.xml`` a property.)

Gather together more real-world (simple, complex, and too-complex) examples.


----

Copyright 2013, David Niergarth

