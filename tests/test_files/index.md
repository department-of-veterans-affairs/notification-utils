# Notify Markdown Specification

The files in the `markdown` folder contain syntax that should be permitted by Notification Portal, and each file has a corresponding file in the sibling folders `html` and `plain_text`.  If the input file markdown/text.md is passed to an HTML markdown renderer, the expected output is the contents of html/text.html.  If the input file markdown/text.md is passed to a plain text markdown renderer, the expected output is the contents of plain_text/text.txt.

These files codify the expected behavior of markdown conversion for the Notify application.

The HTML files should not include any styling.  The HTML output should get inserted into a Jinja template that includes CSS.

## Supported markdown

VA Notify markdown support mostly aligns with [Github markdown](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet).  Some additionally supported markdown includes:

- The use of bullets ("•") to denote unordered lists
- The use of "^" to denote a block quote.  The standard ">" also works.  Block quotes can be nested, but this looks bad in plain text.
- Preface a link with ">>" to denote an "action link," with has specific styling for HTML output.  Action links are treated like standard links for plain text output.

## Unsupported markdown

VA Notify markdown is not guaranteed to support:

- Ordered sublists.  Github markdown discusses ordered sublists [here](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet#lists), but a close inspection of the rendered output reveals that ordered sublists are not actually nested.  (Unordered sublists are nested.)
- Sublists nested more than once
- Images and tables in markdown will be deleted and not present in the resulting HTML or plain text output.
