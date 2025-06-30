import json
import logging
import os
import pathlib

logger = logging.getLogger("climenu")

class Configuration:
    def __init__(self, project_dir: str, out_langs: list[str], primary_lang: str, merge_duplicates: bool,
                 timestamp: bool):
        self.project_dir = project_dir
        self.out_langs = out_langs
        self.primary_lang = primary_lang
        self.merge_duplicates = merge_duplicates
        self.timestamp = timestamp

    def to_dict(self) -> dict[str, any]:
        return {
            "project_dir": self.project_dir,
            "out_langs": self.out_langs,
            "primary_lang": self.primary_lang,
            "merge_duplicates": self.merge_duplicates,
            "timestamp": self.timestamp
        }

    def save(self, file_path: str | os.PathLike[str]):
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(self.to_dict(), fp, indent=4)

def read_config_from_dict(obj: dict[str, any]) -> Configuration:
    return Configuration(**obj)

_DEFAULT_CONFIG = Configuration(None, list(), "en", True, True)
_DEFAULT_CHAR_NAMES = {
    "@": "Narrator",
    "centered": "Narrator (centered)",
    "n": "Narrator (NVL)",
    "extend": "Last person"
}
_CONFIG_FILE_PATH = "config.json"

def _start_section(title):
    print()
    print("┌" + "─" * (len(title) + 4) + "┐")
    print("│  " + title + "  │")
    print("└" + "─" * (len(title) + 4) + "┘")

def _load_config():
    file_path = pathlib.Path(_CONFIG_FILE_PATH)
    if file_path.exists():
        try:
            with file_path.open("r", encoding="utf-8") as fp:
                return read_config_from_dict(json.load(fp))
        except IOError as e:
            print(f"ERROR: Could not read from {_CONFIG_FILE_PATH}")
            print(e)
    return Configuration(**_DEFAULT_CONFIG.to_dict())

def define_configuration():
    config = _load_config()
    _start_section("Configuration Settings")
    run = True
    modified = False
    while run:
        print()
        print(f"[1] Project directory           | {config.project_dir or '(not set)'}")
        print(f"[2] Output languages            | {','.join(config.out_langs) or '(not set)'}")
        print(f"[3] Primary language            | {config.primary_lang}")
        print(f"[4] Merge duplicates (.po/.pot) | {'Yes' if config.merge_duplicates else 'No'}")
        print(f"[5] Write timestamp (.rpy)      | {'Yes' if config.timestamp else 'No'}")
        print("[S] Save configuration file")
        print("[X] Exit")
        option = input("> ").lower()
        if option == "1":
            print("Define the project directory, or leave blank to cancel.")
            print("Project directory should contain the `game` directory at the top level.")
            option = input("> ")
            if option != "":
                file_path = pathlib.Path(option)
                if not file_path.exists():
                    print("ERROR: Directory does not exist")
                elif not file_path.is_dir():
                    print("ERROR: Not a directory")
                else:
                    config.project_dir = option
                    modified = True
        elif option == "2":
            print("Define output languages, or leave blank to cancel.")
            print("Languages should be separated by a comma (i.e. `ru,es,de`).")
            option = input("> ")
            if option != "":
                out_langs = option.split(",")
                i = 0
                while i < len(out_langs):
                    out_langs[i] = out_langs[i].strip()
                    if out_langs[i] == "":
                        del out_langs[i]
                    else:
                        i += 1
                config.out_langs = out_langs
                modified = True
        elif option == "3":
            print("Define the primary language, or leave blank to cancel.")
            print("Only set this if the primary language is not English.")
            option = input("> ")
            if option != "":
                config.primary_lang = option.strip()
                modified = True
        elif option == "4":
            print("Define whether to merge duplicate entries when converting from .rpy to .po/.pot files.")
            print("[Y] Yes")
            print("[N] No")
            print("[X] Cancel")
            option = input("> ").lower()
            if option == "y":
                config.merge_duplicates = True
                modified = True
            elif option == "n":
                config.merge_duplicates = False
                modified = True
        elif option == "5":
            print("Define whether to write the timestamp when creating .rpy files.")
            print("[Y] Yes")
            print("[N] No")
            print("[X] Cancel")
            option = input("> ").lower()
            if option == "y":
                config.timestamp = True
                modified = True
            elif option == "n":
                config.timestamp = False
                modified = True
        elif option == "s":
            try:
                config.save(_CONFIG_FILE_PATH)
                modified = False
            except IOError as e:
                print(f"ERROR: Could not save {_CONFIG_FILE_PATH}")
                print(e)
        elif option == "x":
            if modified:
                print("You have unsaved changes. Do you want to save them?")
                print("[Y] Yes")
                print("[N] No")
                print("[X] Cancel")
                option = input("> ").lower()
                if option == "y":
                    try:
                        config.save(_CONFIG_FILE_PATH)
                        run = False
                        continue
                    except IOError as e:
                        print(f"ERROR: Could not save {_CONFIG_FILE_PATH}")
                        print(e)
                elif option != "n":
                    continue
            run = False
        else:
            print(f"Invalid option: {option}")


def define_char_names():
    char_names = dict(_DEFAULT_CHAR_NAMES)
    _start_section("Define Character Names")
    run = True
    while run:
        print()
        print("[A] Add new character names")
        print("[D] Delete character name")
        print("[C] Clear all character names")
        print("[L] List all character names")
        print("[R] Read character names from file")
        print("[W] Write character names to file")
        print("[X] Exit")
        option = input("> ").lower()
        if option == "a":
            add = True
            print("Type `<variable> <name>`, then press Enter to enter a new character name (Use `@` for the narrator).")
            print("Type `x` to stop inputting names.")
            while add:
                name = input("> ")
                tokens = name.split(" ", 2)
                if len(tokens) == 2:
                    if tokens[0] in char_names:
                        print(f"{tokens[0]} is already defined. Do you want to override it?")
                        print("[Y] Yes")
                        print("[N] No")
                        option = input("> ").lower()
                        if option != "y":
                            continue
                    char_names[tokens[0]] = tokens[1]
                elif tokens[0].lower() == "x":
                    add = False
                else:
                    print(f"Invalid format: {name}")
        elif option == "d":
            print("Input the variable of the character name to delete.")
            option = input("> ")
            if option in char_names:
                del char_names[option]
            else:
                print(f"Unknown variable: {option}")
        elif option == "c":
            print("Are you sure you wish to clear all character names?")
            print("[Y] Yes")
            print("[N] No")
            print("[R] Reset to default")
            option = input("> ").lower()
            if option == "y":
                char_names.clear()
            elif option == "r":
                char_names = dict(_DEFAULT_CHAR_NAMES)
        elif option == "l":
            sorted_names = sorted(char_names.keys())
            for name in sorted_names:
                print(f"  {name}: {char_names[name]}")
        elif option == "r":
            print("Input the name of the file to read from.")
            print("Leave blank to use `char_names.json`, or type `x` to cancel.")
            option = input("> ")
            if option == "":
                option = "char_names.json"
            if option.lower() != "x":
                file_path = pathlib.Path(option)
                if file_path.exists():
                    try:
                        with file_path.open("r", encoding="utf-8") as fp:
                            char_names = dict(json.load(fp))
                    except IOError as e:
                        print(f"ERROR: Could not read file `{option}`:")
                        print(e)
                else:
                    print(f"Invalid file path: {option}")
        elif option == "w":
            print("Input the name of the file to write to.")
            print("Leave blank to use `char_names.json`, or type `x` to cancel.")
            option = input("> ")
            if option == "":
                option = "char_names.json"
            if option.lower() != "x":
                file_path = pathlib.Path(option)
                if file_path.exists():
                    try:
                        with file_path.open("w", encoding="utf-8") as fp:
                            json.dump(char_names, fp, indent=4, sort_keys=True)
                    except IOError as e:
                        print(f"ERROR: Could not read file `{option}`:")
                        print(e)
                else:
                    print(f"Invalid file path: {option}")
        elif option == "x":
            run = False
        else:
            print(f"Invalid option: {option}")

def generate_pot_file():
    _start_section("Generate POT File")


def show_interactive_menu():
    pass
