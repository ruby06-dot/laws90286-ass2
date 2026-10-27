"""Builds a downloadable Markdown report from the analysis output."""

from datetime import date

STEP_ORDER = ["scope", "physical_properties", "end_uses", "consumers", "tariff",
              "likeness", "affecting", "lft"]


def bullet_list(items):
    return "\n".join(f"- {item}" for item in items) if items else "- None identified"


def build_markdown_report(measure_text, output):
    outcome = output["outcome"]
    conclusion = output["conclusion"]
    results = output["results"]

    lines = [
        "# GATT Article III:4 Analysis",
        f"Generated on {date.today().isoformat()} using {output['model']} "
        f"({output['ai_calls']} AI calls). This is not legal advice.",
        "",
        "## Measure analysed",
        measure_text.strip(),
        "",
        "## Outcome",
        f"**{outcome['label']}**",
        "",
    ]
    if outcome["scope_warning"]:
        lines += [f"> {outcome['scope_warning']}", ""]

    lines += ["| Element | Finding |", "|---|---|"]
    lines += [f"| {name} | {answer} |" for name, answer in outcome["elements"].items()]
    lines += ["", "## Summary", str(conclusion.get("executive_summary", "")), ""]

    lines += ["### Key uncertainties", bullet_list(conclusion.get("key_uncertainties", [])), ""]
    lines += ["### Next steps", bullet_list(conclusion.get("next_steps", [])), ""]

    lines.append("## Step-by-step analysis")
    for key in STEP_ORDER:
        if key not in results:
            continue
        r = results[key]
        lines += [
            "",
            f"### {r['title']}",
            f"**Finding:** {r['conclusion']}",
            "",
        ]
        if r.get("rule_applied"):
            lines += [f"**Rule applied:** {r['rule_applied']}", ""]
        lines += [
            f"**Reasoning:** {r['reasoning']}",
            "",
            "**Supporting facts**", bullet_list(r.get("supporting_facts", [])), "",
            "**Contrary factors**", bullet_list(r.get("contrary_factors", [])), "",
            "**Evidence gaps**", bullet_list(r.get("evidence_gaps", [])), "",
            f"**Quote check:** {r['quote_check']}",
        ]
        for quote in r.get("quotes", []):
            lines.append(f"> {quote}")
    return "\n".join(lines) + "\n"