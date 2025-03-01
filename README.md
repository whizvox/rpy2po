# rpy2po

This is the public repository for rpy2po, a Python module and CLI tool to convert [Ren'Py](https://www.renpy.org/)
translation files into PO files and back again.

## But why though?

I want to allow for convenient collaborative translation for Ren'Py projects via services such as
[Weblate](https://weblate.org/en/), which support a whole host of different translation file formats. Sadly, Ren'Py
translation files are both completely unsupported by these services and very weird. Rather than translating "text",
Ren'Py requires translation of lines of Ren'Py code, which can be a barrier to entry for anyone who wishes to help with
a project's translation effort, and can easily result in broken code which requires manual intervention.

To summarize, these are the pros and cons of Ren'Py translation files:

| Pros            | Cons                                                  |
|-----------------|-------------------------------------------------------|
| Highly flexible | Unsupported by all collaborative translation services |
|                 | Translators must learn basic Ren'Py syntax            |

The solution to the first con would be to use a more widely-supported translation format. I stumbled upon
[PO files](https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html), which boast many features that are
extremely helpful towards this idea. Each entry can contain translator-specific comments, list all occurrences of a
string in a codebase, and can include a context to differentiate between matching strings.

The solution to the second con would be to extract the text that actually needs translating (the character dialogue)
and use that as the `msgid` and `msgstr` in these PO files.

## Wiki

Check out [the wiki](https://github.com/whizvox/rpy2po/wiki) for detailed information on how to use this module and the
included CLI tool.

## License

This project is licensed by the MIT License, a copy of which is provided at `LICENSE.txt`.