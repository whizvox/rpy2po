import glob
import json
import logging
import os
import pathlib
import shutil

import rpy2po.rpytl

logger = logging.getLogger("climenu")

###################
#  Configuration  #
###################

class Configuration:
    def __init__(self, project_dir: str | None, out_langs: list[str], primary_lang: str, merge_duplicates: bool,
                 timestamp: bool, files_included: list[str], files_excluded: list[str]):
        self.project_dir = project_dir
        self.out_langs = out_langs
        self.primary_lang = primary_lang
        self.merge_duplicates = merge_duplicates
        self.timestamp = timestamp
        self.files_included = files_included
        self.files_excluded = files_excluded

    def get_game_dir(self) -> pathlib.Path:
        return pathlib.Path(self.project_dir, "game")

    def get_translation_dir(self, tl_name) -> pathlib.Path:
        return self.get_game_dir() / "tl" / tl_name

    def to_dict(self) -> dict[str, any]:
        return {
            "project_dir": self.project_dir,
            "out_langs": self.out_langs,
            "primary_lang": self.primary_lang,
            "merge_duplicates": self.merge_duplicates,
            "timestamp": self.timestamp,
            "files_included": self.files_included,
            "files_excluded": self.files_excluded
        }

    def save(self, file_path: str | os.PathLike[str]):
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(self.to_dict(), fp, indent=4)

_DEFAULT_CONFIG = Configuration(None, list(), "en", True, True, list(), list())
_CONFIG_FILE_PATH = "config.json"

def load_config() -> Configuration:
    file_path = pathlib.Path(_CONFIG_FILE_PATH)
    if file_path.exists():
        try:
            with file_path.open("r", encoding="utf-8") as fp:
                obj = json.load(fp)
                return Configuration(**obj)
        except IOError as e:
            print(f"ERROR: Could not read from {_CONFIG_FILE_PATH}")
            print(e)
    return Configuration(**_DEFAULT_CONFIG.to_dict())

######################
#  Ren'Py Utilities  #
######################

def find_translation_files(config: Configuration, tl_name: str) -> list[str]:
    tl_dir = config.get_translation_dir(tl_name)
    return glob.glob("*.rpy", root_dir=tl_dir, recursive=True)


#######################
#  Menu Base Classes  #
#######################

class MenuException(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

def check_project_dir(config: Configuration) -> None:
    if config.project_dir is None:
        raise MenuException("Project directory is not defined")

class MenuOption:
    def __init__(self, choice: str, description: str, action):
        self.choice = choice
        self.description = description
        self.action = action

class Menu:
    def __init__(self, title: str, options: list[MenuOption], loop: bool=True, exit_text: str= "Exit"):
        self.title = title
        self.options = options
        self.loop = loop
        self.exit_text = exit_text

    def _print_title(self):
        print("╔" + ("═" * (len(self.title) + 4)) + "╗")
        print("║  " + self.title + "  ║")
        print("╚" + ("═" * (len(self.title) + 4)) + "╝")

    def show(self):
        run = True
        while run:
            self._print_title()
            print("Select an option and press Enter.")
            for option in self.options:
                print(f"[{option.choice.upper()}] {option.description}")
            print(f"[X] {self.exit_text}")
            choice = input("> ").lower()
            if choice == "x":
                run = False
            else:
                action = None
                for option in self.options:
                    if choice == option.choice.lower():
                        action = option.action
                        break
                if action is not None:
                    try:
                        action()
                    except MenuException as e:
                        print("ERROR: " + e.message)
                else:
                    print(f"Invalid option: {choice}")
            if not self.loop:
                run = False
            print()

def show_selection_menu(prompt: str, options: list[tuple[str, str]], cancel: bool=True) -> str | None:
    print(prompt)
    for option in options:
        print(f"[{option[0].upper()}] {option[1]}")
    if cancel:
        print("[X] Cancel")
    choice = input("> ").lower()
    if cancel and choice == "x":
        return None
    for option in options:
        if option[0].lower() == choice:
            return choice
    print(f"Invalid option: {choice}")
    return None

def show_yes_no_menu(prompt: str, cancel: bool=True) -> bool | None:
    return show_selection_menu(prompt, [("y", "Yes"), ("n", "No")], cancel=cancel)


#######################
#  Specialized Menus  #
#######################

class TranslationFilesMenu(Menu):
    def __init__(self):
        super().__init__("Manage Translation Files", [
            MenuOption("a", "Include all translation files", self.include_all),
            MenuOption("c", "Choose translation files", self.choose_files),
            MenuOption("l", "List all included translation files", self.list_files)
        ])

    def include_all(self):
        config = load_config()
        check_project_dir(config)
        files = find_translation_files(config, config.primary_lang)
        if len(files) > 0:
            print(f"Found {len(files)} files:")
            if len(files) < 11:
                for file in files:
                    print(f"- {file}")
            else:
                for i in range(10):
                    print(f"- {files[i]}")
                print(f"- and {len(files)-10} more...")
            choice = show_yes_no_menu("Would you like to include all of these files?", cancel=False)
            if choice == "y":
                config.files_included.clear()
                config.files_included.extend(files)
                config.files_excluded.clear()
                config.save(_CONFIG_FILE_PATH)
                print("All files have been included.")
        else:
            print(f"Found no translation files for primary language ({config.primary_lang}). You most likely need to generate these translations first.")

    def choose_files(self):
        config = load_config()
        check_project_dir(config)
        files = find_translation_files(config, config.primary_lang)
        if len(files) > 0:
            # check if the includes and excluded file lists are not empty
            if len(config.files_included) > 0 or len(config.files_excluded) > 0:
                new_files = []
                for file in files:
                    if file not in config.files_included and file not in config.files_excluded:
                        new_files.append(file)
                if len(new_files) > 0:
                    print(f"Found {len(new_files)} files unaccounted for:")
                    if len(new_files) < 11:
                        for file in new_files:
                            print(f"- {file}")
                    else:
                        for i in range(10):
                            print(f"- {new_files[i]}")
                        print(f"- and {len(new_files)-10} more...")
                    choice = show_yes_no_menu("Would you like to choose from these files?", cancel=False)
                    if choice == "y":
                        files = new_files
            new_included = []
            new_excluded = []
            print("For each of the following files, refer to the following options (if left blank and if applicable, the current status is used):")
            print("[I] Include the file")
            print("[E] Exclude the file")
            print("[X] Exit without saving")
            index = 0
            for file in files:
                index += 1
                run = True
                while run:
                    run = False
                    print(f"({index}/{len(files)}) {file}")
                    print("Current status: ", end="")
                    if file in config.files_included:
                        print("Included")
                    elif file in config.files_excluded:
                        print("Excluded")
                    else:
                        print("Untracked")
                    choice = input("> ").lower()
                    if choice == "i":
                        new_included.append(file)
                    elif choice == "e":
                        new_excluded.append(file)
                    elif choice == "x":
                        return
                    elif choice == "":
                        if file in config.files_included:
                            new_included.append(file)
                        elif file in config.files_excluded:
                            new_excluded.append(file)
                        else:
                            print("File is untracked! Please specify whether to include or exclude the file.")
                            run = True
                    else:
                        print(f"Invalid option: {choice}")
                        run = True
            config.files_included.clear()
            config.files_included.extend(new_included)
            config.files_excluded.clear()
            config.files_excluded.extend(new_excluded)
            config.save(_CONFIG_FILE_PATH)
        else:
            print(f"Found no translation files for primary language ({config.primary_lang}). You most likely need to generate these translations first.")

    def list_files(self):
        config = load_config()
        check_project_dir(config)
        files = find_translation_files(config, config.primary_lang)
        missing_files = []
        if len(config.files_included) > 0:
            print("Included files:")
            for file in config.files_included:
                if file in files:
                    print(f"- {file}")
                else:
                    missing_files.append(file)
        if len(config.files_excluded) > 0:
            print("Excluded files:")
            for file in config.files_excluded:
                if file in files:
                    print(f"- {file}")
                else:
                    missing_files.append(file)
        untracked_files = []
        for file in files:
            if file not in config.files_included and file not in config.files_excluded:
                untracked_files.append(file)
        if len(untracked_files) > 0:
            print(f"Found {len(untracked_files)} untracked file(s):")
            for file in untracked_files:
                print(f"- {file}")
        if len(missing_files) > 0:
            print(f"WARNING: Found {len(missing_files)} missing file(s):")
            for file in missing_files:
                print(f"- {file}")

class ConfigurationMenu(Menu):
    def __init__(self):
        super().__init__("Manage Configuration Settings", [
            MenuOption("1", "Project directory", self.set_project_dir),
            MenuOption("2", "Output languages", self.set_out_langs),
            MenuOption("3", "Primary language", self.set_primary_lang),
            MenuOption("4", "Merge duplicates (.po/.pot)", self.set_merge_duplicates),
            MenuOption("5", "Write timestamp (.rpy)", self.set_write_timestamp)
        ])
        self.modified = False
        self.config = load_config()

    def show(self):
        run = True
        while run:
            run = False
            super().show()
            if self.modified:
                choice = show_yes_no_menu("You have unsaved changes. Do you want to save them?")
                if choice == "y":
                    try:
                        self.config.save(_CONFIG_FILE_PATH)
                    except IOError as e:
                        print(f"ERROR: Could not save {_CONFIG_FILE_PATH}")
                        print(e)
                elif choice != "n":
                    run = True

    def set_project_dir(self):
        print("Define the project directory, or leave blank to cancel.")
        print("Project directory should contain the `game` directory at the top level.")
        choice = input("> ")
        if choice != "":
            file_path = pathlib.Path(choice)
            if not file_path.exists():
                print("Directory does not exist!")
            elif not file_path.is_dir():
                print("That is not a directory!")
            else:
                self.config.project_dir = choice
                self.modified = True

    def set_out_langs(self):
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
            self.config.out_langs = out_langs
            self.modified = True

    def set_primary_lang(self):
        print("Define the primary language, or leave blank to cancel.")
        print("Only set this if the primary language is not English.")
        option = input("> ")
        if option != "":
            self.config.primary_lang = option.strip()
            self.modified = True

    def set_merge_duplicates(self):
        choice = show_yes_no_menu("Define whether to merge duplicate entries when converting from .rpy to .po/.pot files.")
        if choice == "y":
            self.config.merge_duplicates = True
            self.modified = True
        elif choice == "n":
            self.config.merge_duplicates = False
            self.modified = True

    def set_write_timestamp(self):
        print("Define whether to write the timestamp when creating .rpy files.")
        print("[Y] Yes")
        print("[N] No")
        print("[X] Cancel")
        option = input("> ").lower()
        if option == "y":
            self.config.timestamp = True
            self.modified = True
        elif option == "n":
            self.config.timestamp = False
            self.modified = True

    def save_file(self):
        try:
            self.config.save(_CONFIG_FILE_PATH)
            self.modified = False
            print("Configuration file saved")
        except IOError as e:
            print(f"ERROR: Could not save {_CONFIG_FILE_PATH}")
            print(e)


class MainMenu(Menu):
    def __init__(self):
        super().__init__("RPY2PO CLI Interactive Menu", [
            MenuOption("t", "Manage translation files", lambda: TranslationFilesMenu().show()),
            MenuOption("c", "Manage configuration settings", lambda: ConfigurationMenu().show()),
            MenuOption("n", "Manage character names", lambda: None),
            MenuOption("o", "Generate POT file", lambda: None),
            MenuOption("p", "Generate PO files", lambda: None),
            MenuOption("r", "Export Ren'Py translations", lambda: None),
            MenuOption("m", "Merge old translations with new POT file", lambda: None)
        ])

# _DEFAULT_CHAR_NAMES = {
#     "@": "Narrator",
#     "centered": "Narrator (centered)",
#     "n": "Narrator (NVL)",
#     "extend": "Last person"
# }
# _CHAR_NAMES_FILE_PATH = "char_names.json"
#
# def _check_project_dir(config: Configuration) -> bool:
#     if config.project_dir is None:
#         return config.prompt_project_dir()
#     return True
#
# def _read_char_names(path: str) -> dict[str, any] | None:
#     file_path = pathlib.Path(path)
#     if file_path.exists():
#         try:
#             with file_path.open("r", encoding="utf-8") as fp:
#                 return dict(json.load(fp))
#         except IOError as e:
#             print(f"ERROR: Could not read file `{path}`:")
#             print(e)
#     else:
#         print(f"Invalid file path: {path}")
#     return None

# def _check_char_names() -> dict[str, any] | None:
#     char_names = _read_char_names(_CHAR_NAMES_FILE_PATH)
#     if char_names is None:
#         print(f"Could not find names file at `{_CHAR_NAMES_FILE_PATH}`. What would you like to do?")
#         print("[D] Define names")
#         print("[U] Use another file")
#         print("[X] Cancel")
#         option = input("> ").lower()
#         if option == 'd':
#             define_char_names()
#         elif option == 'u':
#             print("Type the name of the file to use, or leave blank to cancel.")
#             option = input("> ")
#             if option != "":
#                 char_names = _read_char_names(option)
#     return char_names


# def define_char_names():
#     char_names = dict(_DEFAULT_CHAR_NAMES)
#     _start_section("Define Character Names")
#     run = True
#     while run:
#         print("[A] Add new character names")
#         print("[D] Delete character name")
#         print("[C] Clear all character names")
#         print("[L] List all character names")
#         print("[S] Scan for and set undefined names")
#         print("[R] Read character names from file")
#         print("[W] Write character names to file")
#         print("[X] Exit")
#         option = input("> ").lower()
#         if option == "a":
#             add = True
#             print("Type `<variable> <name>`, then press Enter to enter a new character name (Use `@` for the narrator).")
#             print("Type `x` to stop inputting names.")
#             while add:
#                 name = input("> ")
#                 tokens = name.split(" ", 2)
#                 if len(tokens) == 2:
#                     if tokens[0] in char_names:
#                         print(f"{tokens[0]} is already defined. Do you want to override it?")
#                         print("[Y] Yes")
#                         print("[N] No")
#                         option = input("> ").lower()
#                         if option != "y":
#                             continue
#                     char_names[tokens[0]] = tokens[1]
#                 elif tokens[0].lower() == "x":
#                     add = False
#                 else:
#                     print(f"Invalid format: {name}")
#         elif option == "d":
#             print("Input the variable of the character name to delete.")
#             option = input("> ")
#             if option in char_names:
#                 del char_names[option]
#             else:
#                 print(f"Unknown variable: {option}")
#         elif option == "c":
#             print("Are you sure you wish to clear all character names?")
#             print("[Y] Yes")
#             print("[N] No")
#             print("[R] Reset to default")
#             option = input("> ").lower()
#             if option == "y":
#                 char_names.clear()
#             elif option == "r":
#                 char_names = dict(_DEFAULT_CHAR_NAMES)
#         elif option == "l":
#             sorted_names = sorted(char_names.keys())
#             for name in sorted_names:
#                 print(f"  {name}: {char_names[name]}")
#         elif option == "s":
#             config = load_config()
#             if not _check_project_dir(config):
#                 continue
#             tl_dir = pathlib.Path(config.project_dir) / "game/tl" / config.primary_lang
#             files = glob.glob("**/*.rpy", root_dir=tl_dir, recursive=True)
#             unknown_names = []
#             if len(files) > 0:
#                 for file in files:
#                     tl_file = rpy2po.rpytl.read_translation_file(pathlib.Path(tl_dir, file))
#                     for entry in tl_file:
#                         if entry.is_dialogue():
#                             dialogue = entry.extract_orig_dialogue(char_names)
#                             if dialogue is not None and dialogue.who_name is None and dialogue.who not in char_names and dialogue.who not in unknown_names:
#                                 unknown_names.append(dialogue.who)
#                 if len(unknown_names) > 0:
#                     print("Type the name of the character, or keep blank to leave undefined.")
#                     index = 0
#                     size = len(unknown_names)
#                     for name in sorted(unknown_names):
#                         print(f"({index+1}/{size}) Define a character name for `{name}`:")
#                         option = input("> ")
#                         if option != "":
#                             char_names[name] = option
#                         index += 1
#             else:
#                 print(f"No files found in {tl_dir}. Maybe you need to generate the primary language translations first?")
#         elif option == "r":
#             print("Input the name of the file to read from.")
#             print(f"Leave blank to use `{_CHAR_NAMES_FILE_PATH}`, or type X to cancel.")
#             option = input("> ")
#             if option == "":
#                 option = _CHAR_NAMES_FILE_PATH
#             if option.lower() != "x":
#                 read_char_names = _read_char_names(option)
#                 if read_char_names is not None:
#                     char_names = read_char_names
#         elif option == "w":
#             print("Input the name of the file to write to.")
#             print(f"Leave blank to use `{_CHAR_NAMES_FILE_PATH}`, or type `x` to cancel.")
#             option = input("> ")
#             if option == "":
#                 option = _CHAR_NAMES_FILE_PATH
#             if option.lower() != "x":
#                 file_path = pathlib.Path(option)
#                 if file_path.exists():
#                     try:
#                         with file_path.open("w", encoding="utf-8") as fp:
#                             json.dump(char_names, fp, indent=4, sort_keys=True)
#                     except IOError as e:
#                         print(f"ERROR: Could not read file `{option}`:")
#                         print(e)
#                 else:
#                     print(f"Invalid file path: {option}")
#         elif option == "x":
#             run = False
#         else:
#             print(f"Invalid option: {option}")

# def generate_pot_file():
#     _start_section("Generate POT File")
#     config = load_config()
#     if not _check_project_dir(config):
#         return
#     char_names = _check_char_names()
#     if char_names is None:
#         return
#     show_instructions = True
#     tl_dir = pathlib.Path(config.project_dir) / "game/tl" / config.primary_lang
#     if tl_dir.exists():
#         print(f"Translations for primary language ({config.primary_lang}) have been found. What would you like to do?")
#         print("[D] Delete them and generate new ones")
#         print("[U] Use them to generate a POT file")
#         print("[X] Cancel")
#         option = input("> ").lower()
#         if option == 'd':
#             shutil.rmtree(tl_dir)
#             print("Primary language translations have been deleted.")
#         elif option == 'u':
#             show_instructions = False
#         else:
#             if option != "x":
#                 print(f"Invalid option: {option}")
#                 return
#     if show_instructions:
#         print("Please follow the instructions below.")
#         print("1. Open the Ren'Py Launcher")
#         print("2. Under the `Actions` section, click on `Generate Translations`")
#         print(f"3. For the language, type `{config.primary_lang}`")
#         print("4. Make sure `Generate empty strings for translations` is selected")
#         print("5. Click on `Generate translations`")
#         print()
#         print("Press Enter once translations have finished generating, or type X to cancel.")
#         option = input("> ").lower()
#         if option == "x":
#             return
#         if not tl_dir.exists():
#             print(f"ERROR: Directory `{tl_dir}` does not exist! Did you follow the instructions correctly?")
#             return
#     exporter = rpy2po.rpytl.RPY2POExporter(merge_duplicates=config.merge_duplicates)
#     file_filter = "**/*.rpy"
#     run = True
#     while run:
#         in_paths = glob.glob(file_filter, root_dir=tl_dir, recursive=True)
#         if len(in_paths) == 0:
#             if file_filter == "**/*.rpy":
#                 print(f"No Ren'Py translation files found at `{tl_dir}`!")
#                 run = False
#             else:
#                 print(f"No Ren'Py translation files found! Would you like to change the filter?")
#
#         elif len(in_paths) > 0:
#             print(f"{len(in_paths)} files found:")
#             if len(in_paths) < 11:
#                 for in_path in in_paths:
#                     print("  " + in_path)
#             else:
#                 for i in range(10):
#                     print("  " + in_paths[i])
#                 print(f"  (+{len(in_paths) - 10} more...)")
#             print("Would you like to use these files?")
#             print("[Y] Yes")
#             print("[F] Set a file filter")
#             print("[S] ")


def show_interactive_menu():
    MainMenu().show()
