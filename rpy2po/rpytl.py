import datetime
import os
import re
import json
import logging

import polib


logger = logging.getLogger("rpytl")


class RenPyDialogue:
    def __init__(self, who: str | None, who_name: str | None, what: str, srcfmt: str, nameonly: bool=False):
        self.who = who
        self.who_name = who_name
        self.what = what
        self.srcfmt = srcfmt
        self.nameonly = nameonly

    def __eq__(self, other):
        return other is not None and self.who == other.who and self.who_name == other.who_name and \
               self.what == other.what and self.srcfmt == other.srcfmt


def parse_dialogue(line: str, name_map: dict[str, str]) -> RenPyDialogue | None:
    who = None
    who_name = None
    what = None
    srcfmt = None
    nameonly = False
    if (m := re.search(r'^"(.+)" "(.*)"( nointeract)?$', line, re.MULTILINE)) is not None:
        who = m[1]
        who_name = who
        what = m[2]
        srcfmt = line[0:m.start(1)] + "[who]" + line[m.end(1):m.start(2)] + "[what]" + line[m.end(2):]
        nameonly = True
    elif (m := re.search(r'^(.+) "(.*)"( nointeract)?$', line, re.MULTILINE)) is not None:
        who = m[1]
        who_name = name_map.get(who, None)
        what = m[2]
        srcfmt = line[0:m.start(2)] + "[what]" + line[m.end(2):]
    elif (m := re.search(r'^"(.*)"( nointeract)?$', line, re.MULTILINE)) is not None:
        who_name = "Narrator"
        what = m.group(1)
        srcfmt = line[0:m.start(1)] + "[what]" + line[m.end(1):]
    if m is None:
        return None
    return RenPyDialogue(who, who_name, what, srcfmt, nameonly)


class RenPyTranslationEntry:
    def __init__(self, hashid: str|None, lang: str, orig: str, text: str, file: str, line: int):
        self.hashid = hashid
        self.lang = lang
        self.orig = orig
        self.text = text
        self.file = file
        self.line = line

    def __str__(self):
        return f"[{self.file}:{self.line}] {self.hashid} {self.lang}\n# {self.orig}\n{self.text}"

    def is_dialogue(self):
        return self.hashid is not None

    def extract_orig_dialogue(self, name_map: dict[str, str]) -> RenPyDialogue | None:
        return parse_dialogue(self.orig, name_map)

    def extract_text_dialogue(self, name_map: dict[str, str]) -> RenPyDialogue | None:
        return parse_dialogue(self.text, name_map)


class RenPyTranslationFile:
    def __init__(self, entries: list[RenPyTranslationEntry]=None):
        if entries is None:
            self.entries = []
        else:
            self.entries = entries

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def append(self, entry: RenPyTranslationEntry):
        self.entries.append(entry)

    def get_lang(self, exhaustive: bool=False) -> str | None:
        lang = None
        if len(self.entries) > 0:
            lang = self.entries[0].lang
        if exhaustive:
            for entry in self:
                if lang != entry.lang:
                    raise Exception("Inconsistent language in translation file")
        return lang

    def write(self, file_path: str | os.PathLike[str], encoding: str="utf-8-sig", timestamp: bool | str=True) -> None:
        """
        Writes a RenPy translation file to standard .rpy format
        :param file_path: Path of the file to write
        :param encoding: The file encoding to use
        :param timestamp: As a bool: whether to write a timestamp at the top of the file. As a str: the format of the
        timestamp to write at the top of the file
        """
        with open(file_path, mode="w", encoding=encoding) as file:
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp_format = timestamp
                else:
                    timestamp_format = "%Y-%m-%d %H:%M:%S"
                file.write(f"# Translation saved {datetime.datetime.now().strftime(timestamp_format)}\n\n")
            in_strings = False
            for entry in self:
                if entry.is_dialogue():
                    if in_strings:
                        in_strings = False
                    file.write(f"# {entry.file}:{entry.line}\n")
                    file.write(f"translate {entry.lang} {entry.hashid}:\n\n")
                    for line in entry.orig.splitlines():
                        file.write(f"    # {line}\n")
                    for line in entry.text.splitlines():
                        file.write(f"    {line}\n")
                    file.write("\n")
                else:
                    if not in_strings:
                        file.write(f"translate {entry.lang} strings:\n\n")
                        in_strings = True
                    file.write(f"    # {entry.file}:{entry.line}\n")
                    file.write(f"    old \"{entry.orig}\"\n")
                    file.write(f"    new \"{entry.text}\"\n\n")


def read_translation_file(file_path: str | os.PathLike[str], encoding="utf-8-sig") -> RenPyTranslationFile:
    entries = []
    with open(file_path, mode="r", encoding=encoding) as fp:
        linenum = 0
        hashid = None
        lang = None
        orig = None
        text = None
        srcfile = None
        srcline = None
        for line in fp.readlines():
            linenum += 1
            line = line.rstrip()
            if line == "":
                continue
            if (m := re.match(r'^ *# (.*\.rpy):(\d+)$', line)) is not None:
                if srcfile is not None:
                    entry = RenPyTranslationEntry(hashid, lang, orig, text, srcfile, srcline)
                    entries.append(entry)
                    orig = None
                    text = None
                srcfile = m.group(1)
                srcline = int(m.group(2))
            elif (m := re.match(r'^translate (.+) strings:$', line)) is not None:
                if srcfile is not None:
                    entry = RenPyTranslationEntry(hashid, lang, orig, text, srcfile, srcline)
                    entries.append(entry)
                    orig = None
                    text = None
                    srcfile = None
                lang = m.group(1)
                hashid = None
            elif (m := re.match(r'^ {4}old "(.*)"$', line)) is not None:
                orig = m.group(1)
            elif (m := re.match(r'^ {4}new "(.*)"$', line)) is not None:
                text = m.group(1)
            elif (m := re.match(r'^translate (.+) (.+):$', line)) is not None:
                lang = m.group(1)
                hashid = m.group(2)
            elif (m := re.match(r'^ {4}# (.*)$', line)) is not None:
                if orig is not None:
                    orig += '\n' + m.group(1)
                else:
                    orig = m.group(1)
            elif (m := re.match(r'^ {4}(.*)$', line)) is not None:
                if text is not None:
                    text += '\n' + m.group(1)
                else:
                    text = m.group(1)
            elif not line.startswith("#"):
                print(f"WARN: Unknown line found at {file_path}:{linenum}")
                print(f"{line}\n")
        if srcfile is not None:
            entry = RenPyTranslationEntry(hashid, lang, orig, text, srcfile, srcline)
            entries.append(entry)
    return RenPyTranslationFile(entries)


class DialogueFormats(dict[str, str]):
    def __init__(self, formats: dict[str, list[str]] | None=None):
        super().__init__()
        if formats is not None:
            self._load(formats)

    def _load(self, formats: dict[str, list[str]]):
        for srcfmt, ids in formats.items():
            for hashid in ids:
                self[hashid] = srcfmt

    def format_rpy(self, hashid: str, dialogue: str, orig_code: str | None=None) -> str:
        srcfmt = self.get(hashid, None)
        if srcfmt is None:
            return dialogue
        index = srcfmt.find("[who]")
        if index >= 0:
            if dialogue == "" and orig_code is not None:
                parsed_dialogue = parse_dialogue(orig_code, dict())
                if parsed_dialogue is not None and parsed_dialogue.nameonly:
                    srcfmt = srcfmt.replace("[who]", parsed_dialogue.who_name)
                else:
                    logger.warning("Translated dialogue code has nameonly character, but original does not: %s", hashid)
            else:
                tokens = dialogue.split("::", 1)
                if len(tokens) == 2:
                    name = tokens[0].strip()
                    dialogue = tokens[1].strip()
                    srcfmt = srcfmt[0:index] + name + srcfmt[index+5:]
        return srcfmt.replace("[what]", dialogue)

    def to_json(self) -> dict[str, list[str]]:
        jsonobj = {}
        for hashid, srcfmt in self.items():
            ids = jsonobj.setdefault(srcfmt, list())
            ids.append(hashid)
        return jsonobj

    def save(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.to_json(), file, indent=4)

    def load(self, file_path: str):
        self.clear()
        with open(file_path, "r", encoding="utf-8") as file:
            jsonobj = json.load(file)
            self._load(jsonobj)


class POExportResult:
    def __init__(self, pofile: polib.POFile, formats: DialogueFormats | None, mismatched_formats: list[str] | None=None):
        """
        Result of exporting a Ren'Py translation file to a PO file
        :param pofile: The PO file to be written
        :param formats: The dialogue formats
        :param mismatched_formats: All hashids with mismatched dialogue formats
        """
        self.pofile = pofile
        self.formats = formats
        if mismatched_formats is None:
            self.mismatched_formats = []
        else:
            self.mismatched_formats = mismatched_formats


class RPY2POExporter:
    def __init__(self, read_encoding: str="utf-8-sig", wrapwidth: int = 80, write_encoding: str = "utf-8",
                 check_for_duplicates: bool = False, merge_duplicates: bool=False,
                 name_map: dict[str, str] | None=None, formats: DialogueFormats | None=None):
        """
        A utility class to assist with exporting .rpy files to .po files
        :param read_encoding: The encoding to use when reading .rpy files
        :param wrapwidth: The wrap width of the resulting .po file
        :param write_encoding: The encoding to use when writing the .po file
        :param check_for_duplicates: Whether to check for duplicate entries in the .po file
        :param merge_duplicates: Whether to merge duplicate translations using multiple occurrences
        :param name_map: A dictionary to map character code names to human-readable names for translators if the entry
        is a line of dialogue
        :param formats: A reference dialogue formats object. If None, a formats object is returned in #export. If not
        None, no formats object is returned in #export, but each entry will be verified against it.
        """
        self.read_encoding = read_encoding
        self.wrapwidth = wrapwidth
        self.write_encoding = write_encoding
        self.check_for_duplicates = check_for_duplicates
        self.merge_duplicates = merge_duplicates
        self.name_map = name_map if name_map is not None else {}
        self.formats = formats

    def export(self, in_paths: list[str | os.PathLike[str]]) -> POExportResult:
        pofile = polib.POFile(wrapwidth=self.wrapwidth, encoding=self.write_encoding,
                              check_for_duplicates=self.check_for_duplicates)
        all_occurrences: dict[str, polib.POEntry] = {}
        if self.formats is None:
            formats = DialogueFormats()
        else:
            formats = None
        missing_names = set()
        mismatched_formats = list()
        for in_path in in_paths:
            logger.info("Reading from \"%s\"", in_path)
            rpyfile = read_translation_file(in_path, encoding=self.read_encoding)
            for entry in rpyfile:
                comment = None
                if entry.is_dialogue():
                    orig_dialogue = entry.extract_orig_dialogue(self.name_map)
                    text_dialogue = entry.extract_text_dialogue(self.name_map)
                    if orig_dialogue is None:
                        msgid = entry.orig
                    else:
                        msgid = orig_dialogue.what
                        # name-only characters pose a slight challenge: a translator will have to translate both the
                        # name of the character and the dialogue. the most flexible solution is to bake the name of the
                        # character into the dialogue string. so a RenPy source line that looks like this:
                        #   "Doctor" "How are you today?"
                        # will be converted to this:
                        #   msgid "Doctor :: How are you today?"
                        if orig_dialogue.nameonly:
                            msgid = orig_dialogue.who_name + " :: " + msgid
                    if text_dialogue is None:
                        msgstr = entry.text
                    else:
                        msgstr = text_dialogue.what
                        # translated name-only exchanges have one added rule: if the dialogue is untranslated (an empty
                        # string), don't put anything in for the msgstr. This is purely because Weblate counts
                        # *anything* that isn't an empty string as translated.
                        if text_dialogue.nameonly and msgstr != "":
                            msgstr = text_dialogue.who_name + " :: " + msgstr
                    if orig_dialogue is None:
                        if self.formats is None:
                            formats[entry.hashid] = entry.orig
                        elif self.formats.get(entry.hashid) != entry.orig:
                            mismatched_formats.append(entry.hashid)
                    else:
                        if orig_dialogue.who_name is None:
                            if orig_dialogue.who not in missing_names:
                                missing_names.add(orig_dialogue.who)
                                logger.warning("Missing name from name map: %s", orig_dialogue.who)
                        else:
                            comment = orig_dialogue.who_name + " speaking"
                        if self.formats is None:
                            formats[entry.hashid] = orig_dialogue.srcfmt
                        elif self.formats.get(entry.hashid) != orig_dialogue.srcfmt:
                            mismatched_formats.append(entry.hashid)
                else:
                    msgid = entry.orig
                    msgstr = entry.text
                msgctxt = entry.hashid
                if msgctxt is None and self.merge_duplicates:
                    if msgid in all_occurrences:
                        poentry = all_occurrences[msgid]
                        poentry.occurrences.append((entry.file, str(entry.line)))
                    else:
                        poentry = polib.POEntry(msgid=msgid, msgstr=msgstr, msgctxt=msgctxt,
                                                comment=comment, occurrences=[(entry.file, str(entry.line))])
                        pofile.append(poentry)
                        all_occurrences[msgid] = poentry
                else:
                    poentry = polib.POEntry(msgid=msgid, msgstr=msgstr, msgctxt=msgctxt,
                                            comment=comment, occurrences=[(entry.file, str(entry.line))])
                    pofile.append(poentry)
        return POExportResult(pofile, formats, mismatched_formats)


class RenPyTranslationFiles(dict[str, RenPyTranslationFile]):
    def __init__(self, lang: str):
        super().__init__()
        self.lang = lang

    def save_all(self, dest: str):
        for rpypath, rpyfile in self.items():
            rpypath = os.path.join(dest, self.lang, os.path.relpath(rpypath, "game"))
            logger.info("Writing to \"%s\"", rpypath)
            os.makedirs(os.path.dirname(rpypath), exist_ok=True)
            rpyfile.write(rpypath)


class PO2RPYExporter:
    def __init__(self, lang: str, formats: DialogueFormats, read_encoding: str="utf-8", write_encoding: str="utf-8-sig",
                 timestamp: str | bool=True, combine_all: bool=False):
        """
        A utility class to assist in generating .rpy translation files from a .po file
        :param lang: The language of the file (English is "en", Spanish is "es", French is "fr", etc.)
        :param formats: Dialogue formats to rebuild RenPy code blocks
        :param read_encoding: The encoding to use when reading the .po file
        :param write_encoding: The encoding to use when writing the .rpy files
        :param timestamp: Whether to include the timestamp in the .rpy files
        :param combine_all: Whether to combine all .rpy files into one file
        """
        self.lang = lang
        self.formats = formats
        self.read_encoding = read_encoding
        self.write_encoding = write_encoding
        self.timestamp = timestamp
        self.combine_all = combine_all

    def export(self, in_path: str | os.PathLike[str]) -> RenPyTranslationFiles:
        rpy_files = RenPyTranslationFiles(self.lang)
        if self.combine_all:
            all_file = RenPyTranslationFile()
            rpy_files[f"{self.lang}.rpy"] = all_file
        else:
            all_file = None
        pofile = polib.pofile(in_path, encoding=self.read_encoding)
        for entry in pofile:
            for file, line in entry.occurrences:
                if self.combine_all:
                    rpyfile = all_file
                elif file in rpy_files:
                    rpyfile = rpy_files[file]
                else:
                    rpyfile = RenPyTranslationFile()
                    rpy_files[file] = rpyfile
                if entry.msgctxt is None:
                    orig = entry.msgid
                    text = entry.msgstr
                    hashid = None
                else:
                    hashid = entry.msgctxt
                    orig = self.formats.format_rpy(hashid, entry.msgid)
                    text = self.formats.format_rpy(hashid, entry.msgstr, orig)
                rpy_entry = RenPyTranslationEntry(hashid, self.lang, orig, text, file, int(line))
                rpyfile.append(rpy_entry)
        return rpy_files

