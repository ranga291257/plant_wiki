from __future__ import annotations

import unittest

from app.llm_ingest import _ensure_raw_citation, _extract_json_objects


class TestExtractJsonObjects(unittest.TestCase):
    def test_standard_jsonl(self) -> None:
        text = '{"name": "A", "slug": "a", "relevance": "r"}\n'
        objs = _extract_json_objects(text)
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0]["name"], "A")

    def test_doubled_braces_from_prompt_echo(self) -> None:
        text = '{{"name": "B", "slug": "b", "relevance": "r"}}'
        objs = _extract_json_objects(text)
        self.assertEqual(objs[0]["slug"], "b")

    def test_single_quoted_python_dict(self) -> None:
        text = "{'name': 'C', 'slug': 'c', 'relevance': 'r'}"
        objs = _extract_json_objects(text)
        self.assertEqual(objs[0]["name"], "C")

    def test_bullet_prefix(self) -> None:
        text = '- {"name": "D", "slug": "d", "relevance": "r"}'
        objs = _extract_json_objects(text)
        self.assertEqual(objs[0]["slug"], "d")

    def test_ignores_lone_brace_lines(self) -> None:
        text = "{\n{\"name\": \"E\", \"slug\": \"e\", \"relevance\": \"r\"}\n"
        objs = _extract_json_objects(text)
        self.assertEqual(len(objs), 1)


class TestEnsureRawCitation(unittest.TestCase):
    def test_fixes_broken_link_and_adds_backticks(self) -> None:
        md = "## Sources\n- [startup-sop-excerpt.md](raw/startup-sop-excerpt.md)\n"
        raw_rel = "raw/thermal-plant/procedures/startup-sop-excerpt.md"
        out = _ensure_raw_citation(md, raw_rel)
        self.assertIn(f"`{raw_rel}`", out)
        self.assertNotIn("](raw/", out)

    def test_fixes_plain_raw_path(self) -> None:
        md = "## Sources\n- raw/startup-sop-excerpt.md (note)\n"
        raw_rel = "raw/thermal-plant/procedures/startup-sop-excerpt.md"
        out = _ensure_raw_citation(md, raw_rel)
        self.assertIn(f"`{raw_rel}`", out)


if __name__ == "__main__":
    unittest.main()
