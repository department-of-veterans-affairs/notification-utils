# Mistune

An odd name for a markdown parser to generate HTML and text content based on templates. The functions and classes in
`formatters.py` use [mistune 0.8.4](https://mistune.readthedocs.io/en/v0.8.4/). Here some hints at how to modify the
behaviour.

## high level view

Mistune parses a text based on regular expressions and creates a list of tokens along with their corresponding text , if
feasible. For example `{'type': 'list_item_end'}` is a token that does not have any text
while `{'type': 'text', 'text': 'three'}` is a token with text. While traversing the tokens, a lexer object will decide
whether a header, paragraph, etc. should be generated, and the renderer generates the output. Mistune regards any text
within a document to be either a block or inline. Therefore, BlockGrammar and BlockLexer identify block tokens while
InlineGrammar and InlineLexer identify inline tokens within each block. Each lexer class contains a set of rules which
are applied until all the text is broken into tokens. Each rule corresponds to one regular expression defined in the
grammar class. Markdown class parses text using the lexer objects and then uses renderer object to generate output.  
The grammar classes contain the majority of the regular expressions which are complicated but powerful. However, a
number of regular expressions are buried inside the code to for example generate a line break token between two text
tokens which complicates overriding the classes. Mistune is designed such that a developer can override the class
methods and use a placeholder object to generate a structure and then use the structure to generate the desired output,
using specialized renderers.

## Notification-utils use of Mistune

Notification-utils has defined 4 renderers with self-explanatory names:

```
NotifyLetterMarkdownPreviewRenderer(mistune.Renderer)
NotifyEmailMarkdownRenderer(NotifyLetterMarkdownPreviewRenderer)
NotifyPlainTextEmailMarkdownRenderer(NotifyEmailMarkdownRenderer)
NotifyEmailPreheaderMarkdownRenderer(NotifyPlainTextEmailMarkdownRenderer)
``` 

Some Mistune grammar regular expressions are overridden rather than defining new grammar and lexer classes. This is not
a complaint but rather an observation.

## overriding the linebreak behavior

NotifyEmailBlockLexer inherits from BlockLexer and NotifyEmailMarkdown inherits from Markdown, so the generated html
paragraphs can have different styles depending on whether part of a list block or not. Another approach would have been
to refactor the `formatters.py` code which would have been high risk as the reason for overriding the regular
expressions was not documented in any of the change history.