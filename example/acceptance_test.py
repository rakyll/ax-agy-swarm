# Hidden acceptance tests: never in the workspace, so agents cannot tailor
# their changes to them. mkverify inlines this file into the verify task as
# tests/test_acceptance.py.
import unittest

from textkit.csvlite import parse_line
from textkit.roman import from_roman, to_roman
from textkit.wrap import wrap


class AcceptWrap(unittest.TestCase):
    def test_exact_fit(self):
        self.assertEqual(wrap("aaaa bbbb", 9), ["aaaa bbbb"])
        self.assertEqual(wrap("aaaa bbbb", 8), ["aaaa", "bbbb"])

    def test_whitespace(self):
        self.assertEqual(wrap("  one\ttwo \n three  ", 80), ["one two three"])
        self.assertEqual(wrap(" \n\t ", 10), [])
        self.assertEqual(wrap("", 10), [])

    def test_paragraphs(self):
        text = "\n\nfirst para here\n \n\n  second  para\n\n"
        self.assertEqual(wrap(text, 10), ["first para", "here", "", "second", "para"])


class AcceptRoman(unittest.TestCase):
    def test_round_trip(self):
        for n in range(1, 4000):
            self.assertEqual(from_roman(to_roman(n)), n)

    def test_rejects_non_canonical(self):
        for bad in ("", "IIII", "IC", "VX", "IIV", "MMMM", "XM", "iv", "IVI", "VV", "CDC", " X", "X1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                from_roman(bad)


class AcceptCsv(unittest.TestCase):
    def test_empty_fields(self):
        self.assertEqual(parse_line(""), [""])
        self.assertEqual(parse_line("a,b,"), ["a", "b", ""])
        self.assertEqual(parse_line(",,"), ["", "", ""])
        self.assertEqual(parse_line('""'), [""])

    def test_escaped_quotes(self):
        self.assertEqual(parse_line('"say ""hi""",x'), ['say "hi"', "x"])
        self.assertEqual(parse_line('""""'), ['"'])

    def test_unterminated(self):
        for bad in ('"abc', 'a,"b,c', '"a""'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_line(bad)


if __name__ == "__main__":
    unittest.main()
