"""Stdlib test: routing-table.json is well-formed and covers the golden corpus.

The corpus is the 15 recon signals from the spec (Appendix A). Each corpus
entry names the memory_ref + candidate_repos the table MUST contain. This is the
regression suite that proves institutional memory is encoded as routing power.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

_SKILL = Path(__file__).parent.parent
_REQUIRED_RULE_KEYS = {
    "id", "match", "candidate_repos", "version_branch", "read_via",
    "first_evidence_source", "also_check_and_disprove", "memory_ref",
}


def _load(name: str) -> object:
    return json.loads((_SKILL / name).read_text())


def test_every_rule_well_formed() -> None:
    table = _load("routing-table.json")
    assert isinstance(table, list) and table, "routing-table.json must be a non-empty list"
    for rule in table:
        missing = _REQUIRED_RULE_KEYS - set(rule)
        assert not missing, f"rule {rule.get('id')!r} missing keys: {sorted(missing)}"
        assert isinstance(rule["match"].get("keywords"), list) and rule["match"]["keywords"]
        assert isinstance(rule["candidate_repos"], list) and rule["candidate_repos"]
        assert isinstance(rule["also_check_and_disprove"], list) and rule["also_check_and_disprove"], \
            f"rule {rule.get('id')!r} must have a non-empty also_check_and_disprove list"


def test_corpus_coverage() -> None:
    table = _load("routing-table.json")
    corpus = _load("tests/corpus.json")
    by_ref = {r["memory_ref"]: r for r in table}
    for entry in corpus:
        ref = entry["memory_ref"]
        assert ref in by_ref, f"no routing rule for corpus memory_ref {ref!r}"
        rule = by_ref[ref]
        for repo in entry["expected_candidate_repos"]:
            assert repo in rule["candidate_repos"], \
                f"rule {ref!r} missing candidate repo {repo!r}"


def _keyword_score(symptom: str, rule: dict) -> int:
    """Count how many of the rule's keywords appear as substrings in the lowercased symptom."""
    needle = symptom.lower()
    return sum(1 for kw in rule["match"]["keywords"] if kw.lower() in needle)


def test_symptom_routes_to_expected_rule() -> None:
    """Each corpus symptom must score highest on its intended rule's keywords.

    The matcher is intentionally simple and deterministic: lowercase the symptom,
    count how many of a rule's match.keywords appear as substrings, pick the
    highest-scoring rule. Ties are a test-authoring defect — corpus symptoms must
    be written so there is a unique winner. If a tie is found the test fails and
    names the ambiguous pair so the symptom can be sharpened.
    """
    table = _load("routing-table.json")
    corpus = _load("tests/corpus.json")
    by_ref = {r["memory_ref"]: r for r in table}

    for entry in corpus:
        ref = entry["memory_ref"]
        symptom = entry.get("symptom", "")
        assert symptom, f"corpus entry {ref!r} is missing a 'symptom' field"

        # Score every rule.
        scores = {r["memory_ref"]: _keyword_score(symptom, r) for r in table}
        best_score = max(scores.values())
        winners = [mem for mem, s in scores.items() if s == best_score]

        assert len(winners) == 1, (
            f"corpus entry {ref!r}: symptom routes ambiguously to {winners} "
            f"(all score {best_score}). Sharpen the symptom or keywords."
        )
        winner = winners[0]
        assert winner == ref, (
            f"corpus entry {ref!r}: symptom routed to {winner!r} "
            f"(score {best_score}) instead of the expected rule {ref!r} "
            f"(score {scores[ref]}). Adjust the symptom so its intended rule wins."
        )


def _main() -> int:
    failures = 0
    for fn in (test_every_rule_well_formed, test_corpus_coverage, test_symptom_routes_to_expected_rule):
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
