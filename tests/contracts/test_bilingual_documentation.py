from __future__ import annotations

import re
import unittest
from pathlib import Path

from orchestrator.documentation import broken_local_links
from orchestrator.language_policy import classify_path, load_policy


ROOT = Path(__file__).resolve().parents[2]
PAIRS = (
    ("README.md", "README.ru.md"),
    ("docs/guides/deployment-to-target-project.md", "docs/guides/deployment-to-target-project-ru.md"),
    ("docs/guides/development-environment.md", "docs/guides/development-environment-ru.md"),
    ("docs/guides/memory-and-knowledge.md", "docs/guides/memory-and-knowledge-ru.md"),
    ("docs/migrations/1.0.md", "docs/migrations/1.0.ru.md"),
    ("docs/migrations/1.1.md", "docs/migrations/1.1.ru.md"),
    ("docs/migrations/1.2.md", "docs/migrations/1.2.ru.md"),
    ("docs/migrations/cli-contract.md", "docs/migrations/cli-contract.ru.md"),
    ("skills/optional/python-code-review/README.md", "skills/optional/python-code-review/README.ru.md"),
)


def _metadata(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    end = lines.index("---", 1)
    result: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


class BilingualDocumentationContractTests(unittest.TestCase):
    def test_every_pair_has_reciprocal_metadata_and_valid_links(self) -> None:
        policy = load_policy(ROOT)
        for english_relative, russian_relative in PAIRS:
            english = ROOT / english_relative
            russian = ROOT / russian_relative
            self.assertTrue(english.is_file(), english_relative)
            self.assertTrue(russian.is_file(), russian_relative)
            self.assertEqual(_metadata(english).get("language"), "en", english_relative)
            self.assertEqual(_metadata(english).get("translation_of"), russian_relative)
            self.assertEqual(_metadata(russian).get("language"), "ru", russian_relative)
            self.assertEqual(_metadata(russian).get("translation_of"), english_relative)
            self.assertEqual(broken_local_links(english, root=ROOT), [], english_relative)
            self.assertEqual(broken_local_links(russian, root=ROOT), [], russian_relative)
            self.assertEqual(classify_path(ROOT, english, policy=policy).language, "en")
            self.assertFalse(classify_path(ROOT, russian, policy=policy).graph_eligible)

    def test_code_fence_counts_match(self) -> None:
        for english_relative, russian_relative in PAIRS:
            english_count = len(re.findall(r"^```", (ROOT / english_relative).read_text(encoding="utf-8"), re.MULTILINE))
            russian_count = len(re.findall(r"^```", (ROOT / russian_relative).read_text(encoding="utf-8"), re.MULTILINE))
            self.assertEqual(english_count, russian_count, english_relative)
