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

    def get_translation_dir(self, lang: str | None=None) -> pathlib.Path:
        if lang is None:
            lang = self.primary_lang
        return self.get_game_dir() / "tl" / lang

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

def find_translation_files(config: Configuration, lang: str | None=None) -> list[str]:
    tl_dir = config.get_translation_dir(lang)
    return glob.glob("**/*.rpy", root_dir=tl_dir, recursive=True)


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

def find_and_check_translation_files(config: Configuration, lang: str | None=None) -> list[str]:
    files = find_translation_files(config, lang)
    if len(files) == 0:
        raise MenuException(f"Could not find translation files for language: {lang}")
    return files

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

def prompt_selection(prompt: str, options: list[tuple[str, str]], cancel: bool=True) -> str | None:
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

def prompt_yes_no(prompt: str, cancel: bool=True) -> bool | None:
    return prompt_selection(prompt, [("y", "Yes"), ("n", "No")], cancel=cancel)


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
            choice = prompt_yes_no("Would you like to include all of these files?", cancel=False)
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
                    choice = prompt_yes_no("Would you like to choose from these files?", cancel=False)
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
            MenuOption("1", "", self.set_project_dir),
            MenuOption("2", "", self.set_out_langs),
            MenuOption("3", "", self.set_primary_lang),
            MenuOption("4", "", self.set_merge_duplicates),
            MenuOption("5", "", self.set_write_timestamp),
            MenuOption("s", "Save configuration file", self.save_file)
        ])
        self.modified = False
        self.config = load_config()
        self._update_descriptions()

    def _update_descriptions(self):
        self.options[0].description = f"Project directory           | {self.config.project_dir or '(undefined)'}"
        self.options[1].description = f"Output languages            | {'(undefined)' if len(self.config.out_langs) == 0 else ','.join(self.config.out_langs)}"
        self.options[2].description = f"Primary language            | {self.config.primary_lang}"
        self.options[3].description = f"Merge duplicates (.po/.pot) | {'Yes' if self.config.merge_duplicates else 'No'}"
        self.options[4].description = f"Write timestamp (.rpy)      | {'Yes' if self.config.timestamp else 'No'}"

    def show(self):
        run = True
        while run:
            run = False
            super().show()
            if self.modified:
                choice = prompt_yes_no("You have unsaved changes. Do you want to save them?")
                if choice == "y":
                    self.save_file()
                elif choice == "x":
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
                self._update_descriptions()

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
            self._update_descriptions()

    def set_primary_lang(self):
        print("Define the primary language, or leave blank to cancel.")
        print("Only set this if the primary language is not English.")
        option = input("> ")
        if option != "":
            self.config.primary_lang = option.strip()
            self.modified = True
            self._update_descriptions()

    def set_merge_duplicates(self):
        choice = prompt_yes_no("Define whether to merge duplicate entries when converting from .rpy to .po/.pot files.")
        if choice == "y":
            self.config.merge_duplicates = True
            self.modified = True
            self._update_descriptions()
        elif choice == "n":
            self.config.merge_duplicates = False
            self.modified = True
            self._update_descriptions()

    def set_write_timestamp(self):
        print("Define whether to write the timestamp when creating .rpy files.")
        print("[Y] Yes")
        print("[N] No")
        print("[X] Cancel")
        option = input("> ").lower()
        if option == "y":
            self.config.timestamp = True
            self.modified = True
            self._update_descriptions()
        elif option == "n":
            self.config.timestamp = False
            self.modified = True
            self._update_descriptions()

    def save_file(self):
        try:
            self.config.save(_CONFIG_FILE_PATH)
            self.modified = False
            print("Configuration file saved")
        except IOError as e:
            print(f"ERROR: Could not save {_CONFIG_FILE_PATH}")
            print(e)

# Character names menu

_DEFAULT_CHAR_NAMES = {
    "centered": "Narrator (centered)",
    "n": "Narrator (NVL)",
    "extend": "Last person"
}
_CHAR_NAMES_FILE_PATH = "char_names.json"

def load_char_names() -> dict[str, str]:
    names_path = pathlib.Path(_CHAR_NAMES_FILE_PATH)
    if names_path.exists():
        try:
            with names_path.open("r", encoding="utf-8") as fp:
                return dict(json.load(fp))
        except IOError as e:
            print(f"ERROR: Could not read file `{_CHAR_NAMES_FILE_PATH}`:")
            print(e)
    return dict(_DEFAULT_CHAR_NAMES)

class CharacterNamesMenu(Menu):
    def __init__(self):
        super().__init__("Manage Character Names", [
            MenuOption("f", "Find and define names", self.find_and_define),
            MenuOption("c", "Clear all character names", self.clear_names),
            MenuOption("l", "List all character names", self.list_names),
            MenuOption("s", "Write character names to file", self.save_file)
        ])
        names_path = pathlib.Path(_CHAR_NAMES_FILE_PATH)
        self.char_names = load_char_names()
        self.modified = False

    def show(self):
        run = True
        while run:
            run = False
            super().show()
            if self.modified:
                choice = prompt_yes_no("You have unsaved changes. Do you want to save them?")
                if choice == "y":
                    self.save_file()
                elif choice == "x":
                    run = True

    def find_and_define(self):
        config = load_config()
        check_project_dir(config)
        new_names = {}
        for file in config.files_included:
            file_path = config.get_translation_dir() / file
            tl_file = rpy2po.rpytl.read_translation_file(file_path)
            for entry in tl_file:
                if entry.is_dialogue():
                    dialogue = entry.extract_orig_dialogue(self.char_names)
                    if dialogue is not None and dialogue.who is not None and not dialogue.nameonly and dialogue.who not in new_names:
                        new_names[dialogue.who] = dialogue.who_name
        print("For all names, specify one of the following things:")
        print("- The name of the character to use in translation contexts")
        print("- Leave blank to use the current name")
        print("- `X` to cancel")
        sorted_names = list(sorted(new_names.keys()))
        for i in range(len(sorted_names)):
            who = sorted_names[i]
            print(f"({i+1}/{len(new_names)}) {who}")
            if who in self.char_names:
                print(f"Current name: {self.char_names[who]}")
            new_name = input("> ")
            if new_name.lower() == "x":
                return
            elif new_name != "":
                new_names[who] = new_name
        self.char_names.clear()
        self.char_names.update(new_names)
        self.modified = True

    def clear_names(self):
        choice = prompt_yes_no("Are you sure you wish to clear all character names?", cancel=False)
        if choice == "y":
            self.char_names.clear()
            self.modified = True

    def list_names(self):
        if len(self.char_names) > 0:
            print("Character names:")
            for who in sorted(self.char_names.keys()):
                print(f"- {who}: {self.char_names[who]}")
        else:
            print("No character names found. Maybe you need to find and define them first?")

    def save_file(self):
        try:
            with open(_CHAR_NAMES_FILE_PATH, "w", encoding="utf-8") as fp:
                json.dump(self.char_names, fp, indent=4)
            print(f"Character names file saved to {_CHAR_NAMES_FILE_PATH}")
            self.modified = False
        except IOError as e:
            print(f"Could not save file {_CHAR_NAMES_FILE_PATH}")
            print(e)

###############
#  Main Menu  #
###############

class MainMenu(Menu):
    def __init__(self):
        super().__init__("RPY2PO CLI Interactive Menu", [
            MenuOption("t", "Manage translation files", lambda: TranslationFilesMenu().show()),
            MenuOption("c", "Manage configuration settings", lambda: ConfigurationMenu().show()),
            MenuOption("n", "Manage character names", lambda: CharacterNamesMenu().show()),
            MenuOption("o", "Generate POT file", self.generate_pot_file),
            MenuOption("p", "Generate PO files", lambda: None),
            MenuOption("r", "Export Ren'Py translations", lambda: None),
            MenuOption("m", "Merge old translations with new POT file", lambda: None)
        ])

    def generate_pot_file(self):
        config = load_config()
        check_project_dir(config)
        if len(config.files_included) == 0:
            raise MenuException("No translation files included. You most likely need to define them first.")
        char_names = load_char_names()
        show_instructions = True
        tl_dir = config.get_translation_dir(config.primary_lang)
        if tl_dir.exists():
            choice = prompt_selection(f"Translations for primary language ({config.primary_lang}) have been found. What would you like to do?", [
                ("d", "Delete them and generate new ones"),
                ("u", "Use them to generate a POT file"),
            ])
            if choice == 'd':
                shutil.rmtree(tl_dir)
                print("Primary language translations have been deleted.")
            elif choice == 'u':
                show_instructions = False
            else:
                return
        if show_instructions:
            print("Please follow the instructions below.")
            print("1. Open the Ren'Py Launcher")
            print("2. Under the `Actions` section, click on `Generate Translations`")
            print(f"3. For the language, type `{config.primary_lang}`")
            print("4. Make sure `Generate empty strings for translations` is selected")
            print("5. Click on `Generate translations`")
            print()
            print("Press Enter once translations have finished generating, or type X to cancel.")
            option = input("> ").lower()
            if option == "x":
                return
            if not tl_dir.exists():
                raise MenuException(f"Directory `{tl_dir}` does not exist! Did you follow the instructions correctly?")
        exporter = rpy2po.rpytl.RPY2POExporter(merge_duplicates=config.merge_duplicates, name_map=char_names)
        files = list(map(lambda file: tl_dir / file, config.files_included))
        result = exporter.export(files)
        pot_file_path = f"{config.primary_lang}.pot"
        formats_file_path = f"formats.{config.primary_lang}.json"
        result.pofile.save(pot_file_path)
        print(f"POT file written to {pot_file_path}")
        result.formats.save(formats_file_path)
        print(f"Formats file written to {formats_file_path}")

def show_interactive_menu():
    MainMenu().show()
