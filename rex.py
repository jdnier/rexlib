"""
REX/Python -- A single regular expression suitable for tokenizing XML.

Based on Robert D. Cameron's REX/Perl 1.0.

Original copyright notice follows:

    REX/Perl 1.0

    Robert D. Cameron "REX: XML Shallow Parsing with Regular Expressions",
    Technical Report TR 1998-17, School of Computing Science, Simon Fraser
    University, November, 1998.
    Copyright (c) 1998, Robert D. Cameron.
    The following code may be freely used and distributed provided that
    this copyright and citation notice remains intact and that modifications
    or additions are clearly identified.

See Robert Cameron's original paper for a rigorous and detailed explanation of the construction of the REX regular expression.

    http://www.cs.sfu.ca/~cameron/REX.html

"""

import re

#
# XML shallow parsing expression pieces.
#

# The variables in this module are named using the following abbreviations:
#
#    SE: scanning expression
#    CE: continuation expression
#   RSB: right square bracket
#    QM: question mark
#    DT: DOCTYPE
#   SPE: shallow parsing expression
#    RE: regular expression

TextSE = "[^<]+"
UntilHyphen = "[^-]*-"
Until2Hyphens = UntilHyphen + "(?:[^-]" + UntilHyphen + ")*-"
CommentCE = Until2Hyphens + ">?"
UntilRSBs = "[^\\]]*](?:[^\\]]+])*]+"
CDATA_CE = UntilRSBs + "(?:[^\\]>]" + UntilRSBs + ")*>"
S = "[ \\n\\t\\r]+"
NameStrt = "[A-Za-z_:]|[^\\x00-\\x7F]"
NameChar = "[A-Za-z0-9_:.-]|[^\\x00-\\x7F]"
Name = "(?:" + NameStrt + ")(?:" + NameChar + ")*"
QuoteSE = "\"[^\"]*\"|'[^']*'"
DT_IdentSE = S + Name + "(?:" + S + "(?:" + Name + "|" + QuoteSE + "))*"
MarkupDeclCE = "(?:[^\\]\"'><]+|" + QuoteSE + ")*>"
S1 = "[\\n\\r\\t ]"
UntilQMs = "[^?]*\\?+"
PI_Tail = "\\?>|" + S1 + UntilQMs + "(?:[^>?]" + UntilQMs + ")*>"
DT_ItemSE = "<(?:!(?:--" + Until2Hyphens + ">|[^-]" + MarkupDeclCE + ")|\\?" + Name + "(?:" + PI_Tail + "))|%" + Name + ";|" + S
DocTypeCE = DT_IdentSE + "(?:" + S + ")?(?:\\[(?:" + DT_ItemSE + ")*](?:" + S + ")?)?>?"
DeclCE = "--(?:" + CommentCE + ")?|\\[CDATA\\[(?:" + CDATA_CE + ")?|DOCTYPE(?:" + DocTypeCE + ")?"
PI_CE = Name + "(?:" + PI_Tail + ")?"
EndTagCE = Name + "(?:" + S + ")?>?"
AttValSE = "\"[^<\"]*\"|'[^<']*'"
ElemTagCE = Name + "(?:" + S + Name + "(?:" + S + ")?=(?:" + S + ")?(?:" + AttValSE + "))*(?:" + S + ")?/?>?"
MarkupSPE = "<(?:!(?:" + DeclCE + ")?|\\?(?:" + PI_CE + ")?|/(?:" + EndTagCE + ")?|(?:" + ElemTagCE + ")?)"

# The XML shallow parsing expression as a string.
XML_SPE = TextSE + "|" + MarkupSPE

# The XML shallow parsing expression as a compiled regex.
XML_SPE_ = re.compile(XML_SPE)

#
# Shallow parsing functions.
#
def shallow_parse(s):
    """
    Shallow parse, returning a list of token strings.

    >>> rex.shallow_parse('<p>some text</p>')
    ['<p>', 'some text', '</p>']

    """
    return re.findall(XML_SPE, s)

def shallow_iterparse(s):
    """
    Shallow parse, returning an iterator of re match objects.

    >>> rex.shallow_iterparse('<p>some text</p>')
    <callable-iterator object at ...>
    >>> list(rex.shallow_iterparse(s))
    [<_sre.SRE_Match object at ...>,
    <_sre.SRE_Match object at ...>,
    <_sre.SRE_Match object at ...>]

    """
    return re.finditer(XML_SPE, s)

#
# Other expressions developed in the REX paper (named groups added).
#
ElemTagRE = "<(?P<name>" + Name + ")(?P<attributes>(?:" + S + Name + "(?:" + S + ")?=(?:" + S + ")?(?:" + AttValSE + "))*)(" + S + ")?/?>"
ElemTagRE_ = re.compile(ElemTagRE)

#
# Useful fragments (named groups added).
#
AttRE = "(?P<attribute>" + S + "(?P<attribute_name>" + Name + ")(?:" + S + ")?=(?:" + S + ")?(?P<attribute_value>" + AttValSE + "))"
AttRE_ = re.compile(AttRE)

