import unittest
import os

from rpy2po import rpytl

NAMES_MAP = {
    "emi": "Emi",
    "li": "Lilly",
    "ha": "Hanako",
    "aki": "Akira",
    "n": "Narrator (NVL)"
}

class TestRPYTL(unittest.TestCase):
    def test_parse_dialogue(self):
        act = rpytl.parse_dialogue('"She frowns, seemingly annoyed by a passing thought."', NAMES_MAP)
        exp = rpytl.RenPyDialogue(None, "Narrator", "She frowns, seemingly annoyed by a passing thought.", '"[what]"')
        self.assertEqual(act, exp, "Narrator dialogue parsing")

        act = rpytl.parse_dialogue('emi "I\'m surprised to see you again!"', NAMES_MAP)
        exp = rpytl.RenPyDialogue("emi", "Emi", "I'm surprised to see you again!", 'emi "[what]"')
        self.assertEqual(act, exp, "Character dialogue parsing")

        act = rpytl.parse_dialogue('"Iwanako" "Hisao?"', NAMES_MAP)
        exp = rpytl.RenPyDialogue("Iwanako", "Iwanako", "Hisao?", '"[who]" "[what]"', True)
        self.assertEqual(act, exp, "Name-only character dialogue parsing")

        act = rpytl.parse_dialogue('nvl clear\nn "Yesterday was pretty eventful with my parents dropping by at noon and Lilly, Shizune, Misha and Akira visiting in the evening."', NAMES_MAP)
        exp = rpytl.RenPyDialogue("n", "Narrator (NVL)", "Yesterday was pretty eventful with my parents dropping by at noon and Lilly, Shizune, Misha and Akira visiting in the evening.", 'nvl clear\nn "[what]"')
        self.assertEqual(act, exp, "Multiline character dialogue parsing")

        act = rpytl.parse_dialogue('nvl clear\n"I gently sit upright to look at Hanako."', NAMES_MAP)
        exp = rpytl.RenPyDialogue(None, "Narrator", "I gently sit upright to look at Hanako.", 'nvl clear\n"[what]"')
        self.assertEqual(act, exp, "Multiline narrator dialogue parsing")

        act = rpytl.parse_dialogue("nvl clear", NAMES_MAP)
        exp = None
        self.assertEqual(act, exp, "Non-dialogue dialogue parsing")

    def test_read_translation_file(self):
        tlfile = rpytl.read_translation_file("../res/en/definitions.rpy")
        self.assertTrue(len(tlfile) > 0, "Could not read any translations")
        tlfile = rpytl.read_translation_file("../res/en/script-ch1.rpy")
        self.assertTrue(len(tlfile) > 0, "Could not read translations")
        tlfile = rpytl.read_translation_file("../res/es/script-ch1.rpy")
        self.assertTrue(len(tlfile) > 0, "Could not read translations")

    # def test_extract_dialogue(self):
    #     entry = rpytl.RenPyTranslationEntry("a1_friday_exercise_57ae5b74", "en", "\"She frowns, seemingly annoyed by a passing thought.\"", "\"\"", "game/script-a1-friday.rpy", 68)
    #     act = entry.extract_orig_dialogue(NAMES_MAP)
    #     exp = rpytl.RenPyDialogue(None, "Narrator", "She frowns, seemingly annoyed by a passing thought.", '"[what]"')
    #     self.assertEqual(act, exp, "Extracting orig dialogue from narrator")
    #
    #     act = entry.extract_text_dialogue(NAMES_MAP)
    #     exp = rpytl.RenPyDialogue(None, "Narrator", "", '"[what]"')
    #     self.assertEqual(act, exp, "Extracting text dialogue from narrator")
    #
    #     entry = rpytl.RenPyTranslationEntry("a1_friday_exercise_79a3ecef", "en", "emi \"I'm surprised to see you again!\"", "emi \"\"", "game/script-a1-friday.rpy", 56)
    #     act = entry.extract_orig_dialogue(NAMES_MAP)
    #     exp = rpytl.RenPyDialogue("emi", "Emi", "I'm surprised to see you again!", 'emi "[what]"')
    #     self.assertEqual(act, exp, "Extracting orig character dialogue")
    #
    #     entry = rpytl.RenPyTranslationEntry("sisterhood_ch15_sh_ch15_67b1ec9d", "en", '"Dad" "Hello, son. We\'re not late, are we?"', '"Dad" ""', "game/mods/sisterhood/script-ch15.rpy", 454)
    #     act = entry.extract_orig_dialogue(NAMES_MAP)
    #     exp = rpytl.RenPyDialogue("Dad", "Dad", "Hello, son. We're not late, are we?", '"[who]" "[what]"', True)
    #     self.assertEqual(act, exp, "Extracting name-only character dialogue")

    def test_to_po(self):
        name_map = {}
        po_exp = rpytl.RPY2POExporter(name_map=name_map)
        pofile, formats = po_exp.export(["../res/en/definitions.rpy", "../res/en/script-ch1.rpy", "../res/en/script-ch11.rpy"])
        os.makedirs("../testexport", exist_ok=True)
        pofile.save("../testexport/en.po")
        formats.save("../testexport/formats.en.json")

    def test_to_rpy(self):
        import difflib
        self.test_to_po()
        formats = rpytl.DialogueFormats()
        formats.load("../testexport/formats.en.json")
        exporter = rpytl.PO2RPYExporter("en", formats)
        rpyfiles = exporter.export("../testexport/en.po")
        rpyfiles.save_all("../testexport/staging")
        for file in ["definitions.rpy", "script-ch1.rpy", "script-ch11.rpy"]:
            path1 = os.path.join("../res/en", file)
            path2 = os.path.join("../testexport/staging/en/mods/sisterhood", file)
            with open(path1, "r", encoding="utf-8") as file1:
                f1 = file1.readlines()
            with open(path2, "r", encoding="utf-8") as file2:
                f2 = file2.readlines()
            diff = difflib.unified_diff(f1, f2, "Original", "Exported", lineterm="")
            print(f"DIFF REPORT FOR \"{file}\"")
            print("\n".join(list(diff)))


if __name__ == "__main__":
    unittest.main()