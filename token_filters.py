"""
Some simple REX filters.

"""

from collections import OrderedDict

from .tokens import *

__all__ = ['concat_tokens', 'wellformedness_check', 'expand_empty_tags', 'find_all_contexts']


def concat_tokens(tokens, token_filter=None):
    """
    Concatenates tokens as XML.

    Optional token_filter will be used as the second argument to an
    isinstance() test, e.g.,

        concat_tokens(tokens, Text)

    will concatenate only Text tokens. The token_filter argument can be
    a class or type or tuple of classes and types.

    TODO:
    * Should probably create a version of concat_tokens that uses a generator
    expression (rather than a list comprehension) so you can write output
    incrementally. (Although writing (token.xml for token in tokens) would be
    pretty easy, its the error handling this function provides that saves a
    lot of time.)

    """
    # The following assertion is to aid in debugging a common but
    # difficult-to-pinpoint programming mistake.
    assert not isinstance(tokens, (str, unicode)), (
        'concat_tokens() was passed a string rather than a sequence of tokens.\n\n  tokens[:100]:\n    %s'
        % repr(tokens[:100])
    )
    try:
        if token_filter:
            return ''.join([token.xml for token in tokens if isinstance(token, token_filter)])
        else:
            return ''.join([token.xml for token in tokens])
    except AttributeError, value:
        raise RexlibError('An AttributeError was raised in concat_tokens(): %s' % value)


def wellformedness_check(tokens):
    """
    A filter that ensures tags nest correctly and no Error tokens are present.

    """
    stack = []
    for token in tokens:
        if token.is_a(Start):
            stack.append(token)
        elif token.is_a(End):
            try:
                start = stack.pop()
            except IndexError:
                raise WellformednessError('Extra end tag found: "%s"' % token.xml)
            if start.name != token.name:
                raise WellformednessError('"%s" matched by "%s"' % (start.xml, token.xml))
        elif token.is_a(Error):
            raise MarkupError(token.xml + tokens.next().xml)
        yield token


def expand_empty_tags(tokens, keep_minimized=None):
    """
    Expands XML empty tags (<empty/>) to a start-end pair (<empty></empty>)
    unless the element name is in keep_minimized.

    Useful to solve serialization issues introduced by XSLT processors'
    penchant for expressing any element without content as an Empty tag
    (at least when XSLT processing well-formed files).

    Also useful when converting to SGML and you need certain empty tags
    minimized (e.g., because they're declared in an SGML DTD as EMPTY) but
    others expressed as a start-end pair.

    """
    for token in tokens:
        if isinstance(token, Empty):
            if keep_minimized and token.name in keep_minimized:
                yield token
            else:
                token.__class__ = Start
                token.reserialize()
                yield Start(token.xml.replace('/', ''))
                yield End('</%s>' % token.name)
        else:
            yield token


def find_all_contexts(tokens):
    """Return a set of unique XML paths found in tokens."""
    stack = []
    contexts = OrderedDict()
    for token in tokens:
        if token.is_a(StartOrEmpty):
            stack.append(token.name)
            path = '/'.join(stack)
            if path not in contexts:
                contexts[path] = None
            if token.is_a(Empty):
                stack.pop()
        elif token.is_a(End):
            stack.pop()
    return contexts.keys()
