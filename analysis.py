"""Analysis pipeline for the GATT Article III:4 tool.

Each step is a separate AI call. Python (not the AI) controls the order of the
steps, decides whether to stop early, and decides the final outcome from the
three element findings. Two checks use ordinary, deterministic string matching:
- every quote from an authority must appear in the paragraph it cites;
- every fact the AI relies on must appear word-for-word in the user's description.
"""

import json

from openai import BadRequestError

from authorities import (
    check_facts,
    check_quotes,
    cited_sources,
    dispute_list,
    excerpts_for_step,
    format_authorities,
    load_library,
    match_similar_cases,
)

from prompts import (
    LIKENESS_CRITERIA,
    STEPS,
    SYSTEM_PROMPT,
    build_conclusion_prompt,
    build_step_prompt,
)

MODEL = "gpt-4o"
TEMPERATURE = 0          # low randomness for more consistent legal analysis
MAX_RETRIES = 2          # extra attempts if a quote from an authority fails its check
MAX_FACT_RETRIES = 1     # extra attempts if only fact quotes fail (they are flagged, not removed)

VALID_ANSWERS = {"Yes", "No", "Uncertain"}
FACT_FIELDS = ["supporting_facts", "contrary_factors"]


# ---------------------------------------------------------------------------
# Result clean-up
# ---------------------------------------------------------------------------

def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def as_quote_list(value):
    """Quotes from authorities: a list of {"source", "text"}."""
    quotes = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            quotes.append({"source": str(item.get("source", "")), "text": str(item.get("text", ""))})
        elif str(item).strip():
            quotes.append({"source": "", "text": str(item)})
    return quotes


def as_fact_list(value):
    """Facts: a list of {"quote", "point"}, where quote comes from the user's description."""
    facts = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            facts.append({"quote": str(item.get("quote", "")), "point": str(item.get("point", ""))})
        elif str(item).strip():
            facts.append({"quote": "", "point": str(item)})
    return facts


def as_answer(value):
    value = str(value).strip().capitalize()
    return value if value in VALID_ANSWERS else "Uncertain"


def clean_element_result(raw):
    return {
        "rule_applied": str(raw.get("rule_applied", "")),
        "supporting_facts": as_fact_list(raw.get("supporting_facts")),
        "contrary_factors": as_fact_list(raw.get("contrary_factors")),
        "evidence_gaps": as_list(raw.get("evidence_gaps")),
        "reasoning": str(raw.get("reasoning", "")),
        "conclusion": as_answer(raw.get("conclusion", "Uncertain")),
        "quotes": as_quote_list(raw.get("quotes")),
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
        "quotes": as_quote_list(raw.get("quotes")),
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
        self.library = load_library()  # treaty text and case excerpts

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
        """Run one step, then check its quotes and facts. Retry if a check fails."""
        excerpts = excerpts_for_step(step_key, self.library)
        base_prompt = build_step_prompt(step_key, measure_text, format_authorities(excerpts),
                                        facts_json, earlier_results)
        cleaner = clean_scope_result if step_key == "scope" else clean_element_result
        fact_fields = [] if step_key == "scope" else FACT_FIELDS

        feedback = ""
        attempts = 0
        while True:
            attempts += 1
            result = cleaner(self.call_ai_json(base_prompt + feedback))

            verified, failed = check_quotes(result["quotes"], excerpts)
            for field in fact_fields:
                result[field] = check_facts(result[field], measure_text)
            failed_facts = [f for field in fact_fields for f in result[field] if not f["verified"]]

            quotes_done = not failed or attempts > MAX_RETRIES
            facts_done = not failed_facts or attempts > MAX_FACT_RETRIES
            if quotes_done and facts_done:
                break

            feedback = "\n\nIMPORTANT: your previous answer failed the app's checks."
            if failed:
                feedback += "\nThese quotes are not in the SOURCE they cite:\n" + "\n".join(
                    f'- [{q["source"]}] "{q["text"]}" ({q["reason"]})' for q in failed)
            if failed_facts:
                feedback += ("\nThese fact quotes do not appear word-for-word in the MEASURE "
                             "DESCRIPTION:\n" + "\n".join(f'- "{f["quote"]}"' for f in failed_facts))
            feedback += ("\nRepeat the task. Copy every quote exactly from where you say it comes "
                         "from, or leave it out.")

        # After the last attempt: correct pinpoints where the text was found elsewhere,
        # and remove quotes that appear in no authority at all.
        corrected = [{"source": q["found_in"]["cite"], "text": q["text"], "cited_as": q["source"],
                      "source_id": q["found_in"]["source_id"], "status": "corrected"}
                     for q in failed if q["found_in"]]
        removed = [q for q in failed if not q["found_in"]]
        result["quotes"] = verified + corrected
        result["removed_quotes"] = [{"source": q["source"], "text": q["text"]} for q in removed]
        result["quote_check"] = describe_quote_check(verified, corrected, removed)
        if fact_fields:
            total = sum(len(result[field]) for field in fact_fields)
            result["fact_check"] = (
                f"all {total} facts found in the description" if not failed_facts
                else f"{len(failed_facts)} of {total} facts not found word-for-word in the description"
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
                 if k not in {"quotes", "removed_quotes", "quote_check", "attempts", "title"}}
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
            build_conclusion_prompt(measure_text, outcome["label"], summary_for_conclusion,
                                    dispute_list(self.library))
        )
        # Keep only disputes that really are in the knowledge base (deterministic check).
        similar = match_similar_cases(conclusion.get("similar_disputes"), self.library)

        return {
            "results": results,
            "outcome": outcome,
            "conclusion": conclusion,
            "stopped_early": stop_early,
            "in_alternative": in_alternative and not stop_early,
            "authorities": cited_sources(results, self.library),
            "similar_cases": similar,
            "ai_calls": self.ai_calls,
            "model": self.model,
            "temperature": TEMPERATURE if self.use_temperature else "model default",
        }


def describe_quote_check(verified, corrected, removed):
    if not (verified or corrected or removed):
        return "no quotes given"
    parts = [f"{len(verified)} verified"]
    if corrected:
        parts.append(f"{len(corrected)} pinpoint(s) corrected by the app")
    if removed:
        parts.append(f"{len(removed)} removed (not found in any authority)")
    return ", ".join(parts)


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
