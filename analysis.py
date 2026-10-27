"""Analysis pipeline for the GATT Article III:4 tool.

Each step is a separate AI call. Python (not the AI) controls the order of the
steps, decides whether to stop early, and decides the final outcome from the
three element findings. Quotes returned by the AI are checked against the
knowledge files with ordinary, deterministic string matching.
"""

import json
import re
from pathlib import Path

from openai import BadRequestError

from prompts import (
    LIKENESS_CRITERIA,
    STEPS,
    SYSTEM_PROMPT,
    build_conclusion_prompt,
    build_step_prompt,
)

MODEL = "gpt-4o"
TEMPERATURE = 0          # low randomness for more consistent legal analysis
MAX_QUOTE_RETRIES = 2    # extra attempts if a quote fails the verbatim check

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
TREATY_FILE = "article_III.txt"   # treaty text, loaded for every step

VALID_ANSWERS = {"Yes", "No", "Uncertain"}


# ---------------------------------------------------------------------------
# Knowledge files and quote verification
# ---------------------------------------------------------------------------

def load_knowledge_file(filename):
    """Read a knowledge file, ignoring comment lines that start with '#'."""
    if not filename:
        return ""
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#")).strip()


def load_authorities(step_key):
    """Treaty text plus the excerpts relevant to this step only."""
    treaty = load_knowledge_file(TREATY_FILE)
    excerpts = load_knowledge_file(STEPS[step_key]["knowledge_file"])
    return "\n\n".join(text for text in [treaty, excerpts] if text)


def normalise_text(text):
    """Make matching robust to curly quotes, dashes and line breaks."""
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip().lower()


def find_unverified_quotes(quotes, authorities):
    """Return the quotes that do NOT appear word-for-word in the authorities."""
    source = normalise_text(authorities)
    failed = []
    for quote in quotes:
        cleaned = normalise_text(quote).strip(" \"'.")
        if cleaned and cleaned not in source:
            failed.append(quote)
    return failed


# ---------------------------------------------------------------------------
# Result clean-up
# ---------------------------------------------------------------------------

def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def as_answer(value):
    value = str(value).strip().capitalize()
    return value if value in VALID_ANSWERS else "Uncertain"


def clean_element_result(raw):
    return {
        "rule_applied": str(raw.get("rule_applied", "")),
        "supporting_facts": as_list(raw.get("supporting_facts")),
        "contrary_factors": as_list(raw.get("contrary_factors")),
        "evidence_gaps": as_list(raw.get("evidence_gaps")),
        "reasoning": str(raw.get("reasoning", "")),
        "conclusion": as_answer(raw.get("conclusion", "Uncertain")),
        "quotes": as_list(raw.get("quotes")),
    }


def clean_scope_result(raw):
    distinction = str(raw.get("distinction_basis", "unclear")).strip().lower()
    measure_type = str(raw.get("measure_type", "unclear")).strip().lower()
    return {
        "measure_summary": str(raw.get("measure_summary", "")),
        "imposing_member": str(raw.get("imposing_member", "Not stated")),
        "imported_product": str(raw.get("imported_product", "")),
        "domestic_product": str(raw.get("domestic_product", "")),
        "differential_treatment": str(raw.get("differential_treatment", "")),
        "distinction_basis": distinction if distinction in {"origin", "origin-neutral"} else "unclear",
        "measure_type": measure_type if measure_type in {
            "internal_regulation", "internal_tax", "border_measure"} else "unclear",
        "conclusion": as_answer(raw.get("within_article_III_4", "Uncertain")),
        "reasoning": str(raw.get("scope_reasoning", "")),
        "evidence_gaps": as_list(raw.get("evidence_gaps")),
        "quotes": as_list(raw.get("quotes")),
    }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Article3_4Analysis:
    """Runs the step-by-step analysis and counts every AI call."""

    def __init__(self, client, model=MODEL):
        self.client = client
        self.model = model
        self.ai_calls = 0
        self.use_temperature = True   # switched off if the model rejects temperature

    def call_ai_json(self, user_prompt):
        """One AI call that must return a JSON object."""
        self.ai_calls += 1
        request = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.use_temperature:
            request["temperature"] = TEMPERATURE

        try:
            response = self.client.chat.completions.create(**request)
        except BadRequestError as error:
            # Some newer (reasoning) models do not accept a custom temperature.
            # Retry once without it and remember this for the rest of the run.
            if self.use_temperature and "temperature" in str(error).lower():
                self.use_temperature = False
                request.pop("temperature")
                response = self.client.chat.completions.create(**request)
            else:
                raise

        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {"reasoning": "The model did not return valid JSON.", "conclusion": "Uncertain"}

    def run_step(self, step_key, measure_text, facts_json="", earlier_results=""):
        """Run one step, then verify its quotes. Retry if a quote is not verbatim."""
        authorities = load_authorities(step_key)
        base_prompt = build_step_prompt(step_key, measure_text, authorities, facts_json, earlier_results)
        cleaner = clean_scope_result if step_key == "scope" else clean_element_result

        feedback = ""
        attempts = 0
        while True:
            attempts += 1
            result = cleaner(self.call_ai_json(base_prompt + feedback))
            failed = find_unverified_quotes(result["quotes"], authorities)

            if not failed:
                result["quote_check"] = "verified" if result["quotes"] else "no quotes given"
                break

            if attempts > MAX_QUOTE_RETRIES:
                # Give up: remove the quotes that could not be verified.
                result["quotes"] = [q for q in result["quotes"] if q not in failed]
                result["quote_check"] = (
                    f"{len(failed)} quote(s) failed the verbatim check and were removed"
                )
                result["removed_quotes"] = failed
                break

            feedback = (
                "\n\nIMPORTANT: Your previous answer contained quotes that do not appear "
                "word-for-word in AUTHORITIES:\n"
                + "\n".join(f"- {q}" for q in failed)
                + "\nRepeat the task. Copy quotes exactly from AUTHORITIES, or leave 'quotes' empty."
            )

        result["attempts"] = attempts
        result["title"] = STEPS[step_key]["title"]
        return result

    def run(self, measure_text, continue_in_alternative=True, progress=None):
        """Run the full analysis. `progress` is an optional callback taking a message."""

        def report(message):
            if progress:
                progress(message)

        results = {}

        # Step 1: facts and scope (never stops the analysis; it only raises a flag).
        report(STEPS["scope"]["title"])
        results["scope"] = self.run_step("scope", measure_text)
        facts = {k: v for k, v in results["scope"].items()
                 if k not in {"quotes", "quote_check", "attempts", "title"}}
        facts_json = json.dumps(facts, indent=2)

        # Steps 2-5: the four likeness criteria, one AI call each.
        for key in LIKENESS_CRITERIA:
            report(STEPS[key]["title"])
            results[key] = self.run_step(key, measure_text, facts_json)

        # Step 6: overall likeness finding.
        criteria_summary = json.dumps(
            {key: {"conclusion": results[key]["conclusion"], "reasoning": results[key]["reasoning"]}
             for key in LIKENESS_CRITERIA},
            indent=2,
        )
        report(STEPS["likeness"]["title"])
        results["likeness"] = self.run_step("likeness", measure_text, facts_json, criteria_summary)

        # Control flow: stop after likeness if the products are not like and the
        # user did not ask for an alternative analysis.
        stop_early = results["likeness"]["conclusion"] == "No" and not continue_in_alternative

        # If likeness was not established, Steps 7 and 8 are analysed in the alternative.
        in_alternative = results["likeness"]["conclusion"] != "Yes"
        alternative_note = ""
        if in_alternative:
            alternative_note = (
                f"NOTE: Step 6 did not find that the products are like products "
                f"(finding: {results['likeness']['conclusion']}). Analyse this step in the "
                "alternative, on the assumption that the products are like products, and say so "
                "at the start of your reasoning."
            )

        if not stop_early:
            report(STEPS["affecting"]["title"])
            results["affecting"] = self.run_step("affecting", measure_text, facts_json, alternative_note)

            earlier = json.dumps(
                {"likeness": results["likeness"]["reasoning"],
                 "affecting": results["affecting"]["reasoning"]},
                indent=2,
            )
            if alternative_note:
                earlier = alternative_note + "\n\n" + earlier
            report(STEPS["lft"]["title"])
            results["lft"] = self.run_step("lft", measure_text, facts_json, earlier)

        # Final outcome is decided by boolean logic, not by the AI.
        outcome = decide_outcome(results)

        report("Step 9: Final conclusion")
        summary_for_conclusion = json.dumps(
            {key: {"conclusion": value["conclusion"], "reasoning": value["reasoning"],
                   "evidence_gaps": value["evidence_gaps"]}
             for key, value in results.items()},
            indent=2,
        )
        conclusion = self.call_ai_json(
            build_conclusion_prompt(measure_text, outcome["label"], summary_for_conclusion)
        )

        return {
            "results": results,
            "outcome": outcome,
            "conclusion": conclusion,
            "stopped_early": stop_early,
            "in_alternative": in_alternative and not stop_early,
            "ai_calls": self.ai_calls,
            "model": self.model,
            "temperature": TEMPERATURE if self.use_temperature else "model default",
        }


def decide_outcome(results):
    """Boolean logic over the three elements of Article III:4."""
    elements = {
        "Like products": results["likeness"]["conclusion"],
        "Measure affecting internal sale etc.": results.get("affecting", {}).get("conclusion", "Not analysed"),
        "Less favourable treatment": results.get("lft", {}).get("conclusion", "Not analysed"),
    }
    answers = list(elements.values())

    if "No" in answers:
        failed = [name for name, answer in elements.items() if answer == "No"]
        label = "Violation of Article III:4 NOT established (element not met: " + ", ".join(failed) + ")"
        status = "not_established"
    elif all(answer == "Yes" for answer in answers):
        label = "Measure is INCONSISTENT with Article III:4 (all three elements met)"
        status = "inconsistent"
    else:
        label = "UNCERTAIN: at least one element could not be decided on the facts given"
        status = "uncertain"

    scope_warning = None
    if results["scope"]["conclusion"] != "Yes":
        scope_warning = (
            "The scope check suggests Article III:4 may not apply to this measure "
            f"(characterised as: {results['scope']['measure_type']}). "
            "The element analysis is provided in the alternative."
        )
        label += ". Note: Article III:4 may not apply (see Step 1)"

    return {"label": label, "status": status, "elements": elements, "scope_warning": scope_warning}