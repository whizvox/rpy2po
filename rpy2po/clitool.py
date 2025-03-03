import argparse
import glob
import json
import os
import typing
import logging

import polib

from rpy2po import rpytl
from rpy2po.rpytl import DialogueFormats

logger = logging.getLogger("rpy2po")


class Rpy2PoArguments:
    def __init__(self, action: typing.Literal["gennames", "verify", "merge", "exportpo", "exportpot", "exportrpy"],
                 project_dir: str | None, langs: list[str], filters: list[str], dest_dir: str | None,
                 names_path: str | None, pot_path: str | None, stage: bool, ref_lang: str | None):
        self.action = action
        self.project_dir = project_dir
        self.langs = langs
        self.filters = filters
        self.dest_dir = dest_dir
        self.names_path = names_path
        self.pot_path = pot_path
        self.stage = stage
        self.ref_lang = ref_lang


def generate_example_names():
    with open("./char_names.json", "w", encoding="utf-8") as names_file:
        example_names = dict(hi="Hisao", li="Lilly", ha="Hanako", emi="Emi", shi="Shizune", rin="Rin")
        json_output = json.dumps(example_names, indent=4)
        names_file.write(json_output)
    logger.info("Example names file written to char_names.json")


def verify_against_pot(args: Rpy2PoArguments):
    if not os.path.exists(args.pot_path):
        logger.error("POT file \"%s\" does not exist", args.pot_path)
        return
    pot_file = polib.pofile(args.pot_path)
    reports = []
    for lang in args.langs:
        lang_path = os.path.join(args.dest_dir, lang + ".po")
        try:
            lang_file = polib.pofile(lang_path)
        except Exception as e:
            logger.warning("Could not open lang file: \"%s\"", lang_path)
            logger.warning(e)
            continue
        limit = min(len(pot_file), len(lang_file))
        for i in range(limit):
            other = pot_file[i]
            this = lang_file[i]
            if other.msgctxt != this.msgctxt or other.msgid != this.msgid or other.occurrences != this.occurrences:
                reports.append(lang)
    if len(reports) == 0:
        logger.info("All PO files passed verification!")
    else:
        logger.warning("%d PO file(s) failed verification: %s", len(reports), reports)


def merge_with_pot(args: Rpy2PoArguments):
    if not os.path.exists(args.pot_path):
        logger.error("POT file \"%s\" does not exist", args.pot_path)
        return
    pot_file = polib.pofile(args.pot_path, encoding="utf-8")
    for lang in args.langs:
        lang_path = os.path.join(args.dest_dir, lang + ".po")
        try:
            lang_file = polib.pofile(lang_path, wrapwidth=120, encoding="utf-8")
        except Exception as e:
            logger.warning("Could not open lang file \"%s\"", lang_path)
            logger.warning(e)
            continue
        logger.info("Merging and saving \"%s\"", lang_path)
        lang_file.merge(pot_file)
        lang_file.save()


def export_to_po(args: Rpy2PoArguments, as_pot: bool=False):
    if args.project_dir is None:
        logger.error("Project directory not defined. Try --project=DIR")
        return
    if not os.path.exists(args.project_dir) or not os.path.isdir(args.project_dir):
        logger.error("Invalid project directory: \"%s\"", args.project_dir)
        return
    if args.names_path is not None:
        try:
            with open(args.names_path, "r", encoding="utf-8") as name_map_file:
                name_map = json.load(name_map_file)
        except OSError as e:
            logger.warning("Could not read from name maps file")
            logger.warning(e)
            name_map = dict()
    else:
        logger.warning("No name map specified. While this isn't required, it is highly recommended")
        name_map = dict()
    ref_formats = None
    if args.ref_lang is not None:
        ref_name = "formats." + args.ref_lang + ".json"
        ref_path = os.path.join(args.dest_dir, ref_name)
        if not os.path.exists(ref_path):
            logger.error("Could not find a %s file at \"%s\"", ref_name, args.dest_dir)
            return
        ref_formats = DialogueFormats()
        ref_formats.load(ref_path)
    exporter = rpytl.RPY2POExporter(name_map=name_map, formats=ref_formats)
    for lang in args.langs:
        in_files = list()
        root_dir = os.path.join(args.project_dir, "game/tl", lang)
        for file_filter in args.filters:
            files = glob.glob(file_filter, root_dir=root_dir, recursive=True)
            if len(files) == 0:
                logger.warning("No files found using \"%s\"", root_dir + "/" + file_filter)
            else:
                for file_path in files:
                    in_files.append(os.path.join(root_dir, file_path))
        if len(in_files) == 0:
            logger.warning("Skipping %s as no files were found", lang)
        else:
            result = exporter.export(in_files)
            save_path = os.path.join(args.dest_dir, lang + (".pot" if as_pot else ".po"))
            os.makedirs(args.dest_dir, exist_ok=True)
            logger.info("Saving PO file to \"%s\"", save_path)
            result.pofile.save(save_path)
            if len(result.mismatched_formats) > 10:
                for i in range(10):
                    logger.warning(f"Mismatched dialogue format at {result.mismatched_formats[i]}")
                logger.warning(f"\t+{len(result.mismatched_formats) - 10} more...")
            else:
                for hashid in result.mismatched_formats:
                    logger.warning(f"Mismatched dialogue format at {hashid}")
            if result.formats is not None:
                formats_path = os.path.join(args.dest_dir, "formats." + lang + ".json")
                logger.info("Saving formats file to \"%s\"", formats_path)
                result.formats.save(formats_path)


def export_to_rpy(args: Rpy2PoArguments):
    if args.stage:
        tl_dir = "staging"
    else:
        game_dir = os.path.join(args.project_dir, "game")
        if not os.path.exists(game_dir) or not os.path.isdir(game_dir):
            logger.error("Invalid Ren'Py project directory: \"%s\"", args.project_dir)
            return
        tl_dir = os.path.join(game_dir, "tl")
    for lang in args.langs:
        po_path = os.path.join(args.dest_dir, lang + ".po")
        if not os.path.exists(po_path) or not os.path.isfile(po_path):
            logger.warning("Could not find .po file at \"%s\"", po_path)
            continue
        formats_path = os.path.join(args.dest_dir,
                                    "formats." + (args.ref_lang if args.ref_lang is not None else lang) + ".json")
        if not os.path.exists(formats_path):
            logger.error("Missing formats file at \"%s\"", formats_path)
            return
        formats = DialogueFormats()
        formats.load(formats_path)
        exporter = rpytl.PO2RPYExporter(lang, formats)
        rpy_files = exporter.export(po_path)
        for rpy_path, rpy_tl in rpy_files.items():
            # ignore renpy common translations
            if not rpy_path.startswith("renpy/common/00") and len(rpy_tl) > 0:
                rpy_path = os.path.join(tl_dir, lang, os.path.relpath(rpy_path, "game"))
                logger.info("Writing to \"%s\"", rpy_path)
                os.makedirs(os.path.dirname(rpy_path), exist_ok=True)
                rpy_tl.write(rpy_path)


def parse_arguments(args: dict[str, any]) -> Rpy2PoArguments:
    filters = args["filter"]
    pot_path = None
    action = "exportpo"
    if args["gennames"]:
        action = "gennames"
    elif args["verify"] is not None:
        action = "verify"
        pot_path = args["verify"]
    elif args["merge"] is not None:
        action = "merge"
        pot_path = args["merge"]
    elif args["export"] == "rpy":
        action = "exportrpy"
    else:
        if args["export"] == "pot":
            action = "exportpot"
        if len(filters) == 0:
            filters.append("**/*.rpy")
    return Rpy2PoArguments(action, args.get("project", None), args["lang"], filters, args["dest"], args["names"],
                           pot_path, args["stage"], args.get("ref", None))


def main(args: dict[str, any]):
    logging.basicConfig(format="[%(asctime)s] %(levelname)s: %(message)s", level=logging.INFO,
                        handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()])
    logger.info("-----------------------------")
    logger.info("Beginning execution of rpy2po")
    logger.info("-----------------------------")
    prog_args = parse_arguments(args)
    if prog_args.action == "gennames":
        generate_example_names()
    elif prog_args.action == "verify":
        verify_against_pot(prog_args)
    elif prog_args.action == "merge":
        merge_with_pot(prog_args)
    elif prog_args.action == "exportpo" or prog_args.action == "exportpot":
        export_to_po(prog_args, prog_args.action == "exportpot")
    elif prog_args.action == "exportrpy":
        export_to_rpy(prog_args)
    else:
        logger.error("Unknown action: %s", prog_args.action)


def get_argument_parser():
    parser = argparse.ArgumentParser("rpy2po.py",
                                     description="CLI tool to help with converting .rpy files to .po files and back")
    parser.add_argument("--project", action="store", help="The Ren'Py project directory", metavar="DIR")
    parser.add_argument("--lang", action="append", help="The language to configure (i.e. en, es, zh_hans)", default=[])
    parser.add_argument("--filter", action="append", help="A filter for input files", default=[])
    parser.add_argument("--dest", action="store", help="Where to write the exported file(s)", metavar="DIR",
                        default="./export")
    parser.add_argument("--names", action="store", help="Path to a JSON file mapping character variables to names",
                        default="char_names.json")
    parser.add_argument("--stage", action="store_true", help="Whether to stage exported .rpy files")
    parser.add_argument("--ref", action="store", help="The language of the formats file generated from the POT file",
                        metavar="LANG")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--export", action="store", help="Whether to export to a .po file, .pot file, or .rpy files",
                         choices=["po", "pot", "rpy"], default="po")
    actions.add_argument("--gennames", action="store_true", help="Create an example name map", default=False)
    actions.add_argument("--verify", action="store", help="Path to a .pot file to verify against", metavar="FILE")
    actions.add_argument("--merge", action="store", help="Path to a .pot file to merge with", metavar="FILE")

    return parser
