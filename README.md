# rpy2po

This is the public repository for rpy2po, a Python library and CLI tool to convert [Ren'Py](https://www.renpy.org/)
translation files into PO files and back again.

## But why though?

I want to allow for convenient collaborative translation for Ren'Py projects via services such as
[Weblate](https://weblate.org/en/), which support a whole host of different translation file formats. Sadly, Ren'Py
translation files are both completely unsupported by these services, and very weird. Rather than translating "text",
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

## How to Use `rpy2po.py`

(You can run `python rpy2po.py --help` for detailed information on each of the command line arguments)

### Arguments

* `--gennames`: Generates an example of a character name map in `char_names.json`. If this is specified, all other
arguments are ignored.
* `--project=<dir>`: (**Required**) The root directory of the Ren'Py project
* `--lang=<lang>`: (**Required**) The language to process. Can supply multiple languages (e.g. `--lang=en --lang=fr`)
* `--export=po|rpy`: (**Default**: `po`) Whether to read Ren'Py files and export to a PO file (`--export=po`), or to
read from a PO file and export Ren'Py
translation files (`--export=rpy`)
* `--filter=<filter>`: (**Default**: `*.rpy`) A file filter for input files. Only used when `--export=po`. Can supply
multiple filters (e.g.
`--filter=script-*.rpy --filter=definitions.rpy`)
* `--dest=<dir>`: (**Default**: `./export`) The directory to output exported PO files. Only used when `--export=po`.
* `--names=<file>`: (**Default**: `char_names.json`) Path to a JSON file containing a mapping of character variable
names to normal character names. Only
used when `--export=po`
* `--stage`: If supplied, exported `.rpy` files will be put in a local `staging` directory rather than in the project
directory. Only used when `--export=rpy`

### Example 1: Generate a PO file

`python rpy2po.py --project=/home/jsmith/RenPyProjects/MyVisualNovel --lang=en`

* Reads all `.rpy` files in `/home/jsmith/RenPyProjects/MyVisualNovel/game/tl/en`
* Generates `./export/en.po`
* Generates `./export/formats.en.po`

`python rpy2po.py --project=C:\Users\jsmith\RenPyProjects\MyCoolVN --lang=en --dest=customexport`

* Reads all `.rpy` files in `/home/jsmith/RenPyProjects/MyVisualNovel/game/tl/en`
* Generates `./customexport/en.po`
* Generates `./customexport/formats.en.po`

`python rpy2po.py --project=C:\Users\jsmith\RenPyProjects\MyCoolVN --lang=en --filter=script-*.rpy`

* Reads all files in `/home/jsmith/RenPyProjects/MyVisualNovel/game/tl/en` that match the `script-*.rpy` filter (e.g. `script-act1.rpy`, `script-emi-a4.rpy`)
* Generates `./export/en.po`
* Generates `./export/formats.en.po`

Will add some more examples here later...

# License

This project is licensed by the MIT License, a copy of which is provided at `LICENSE.txt`.