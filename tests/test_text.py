import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app  # noqa: E402


class PunctuationTests(unittest.TestCase):
    def check(self, src, expected):
        self.assertEqual(app.normalize_punctuation(src), expected)

    def test_chinese_gets_fullwidth(self):
        self.check("你好, 世界. 好吗? 对!", "你好，世界。好吗？对！")
        self.check("他说: 好的; 走吧", "他说：好的；走吧")

    def test_japanese_comma_becomes_touten(self):
        self.check("今日は, 話があります.", "今日は、話があります。")

    def test_english_only_gets_halfwidth(self):
        self.check("Hello，world。 This is ok？", "Hello, world. This is ok? ")

    def test_ambiguous_cases_untouched(self):
        for s in ["我们用 API, 然后 deploy.", "等一下... 好的", "第3.5章，版本v2.0 和 foo.py"]:
            self.check(s, s)


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self._old = app.cfg["chinese_script"]

    def tearDown(self):
        app.cfg["chinese_script"] = self._old

    def test_to_simplified(self):
        app.cfg["chinese_script"] = "simplified"
        self.assertEqual(app.convert_script("我們今天討論 API，會議"), "我们今天讨论 API，会议")

    def test_japanese_kanji_kept(self):
        app.cfg["chinese_script"] = "simplified"
        self.assertEqual(app.convert_script("今日は話があります"), "今日は話があります")

    def test_to_traditional_and_none(self):
        app.cfg["chinese_script"] = "traditional"
        self.assertEqual(app.convert_script("我们今天讨论"), "我們今天討論")
        app.cfg["chinese_script"] = "none"
        self.assertEqual(app.convert_script("我們"), "我們")


if __name__ == "__main__":
    unittest.main()
