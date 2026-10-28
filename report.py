"""Builds the downloadable Markdown and Word reports from the analysis output."""

from datetime import date

STEP_ORDER = ["scope", "physical_properties", "end_uses", "consumers", "tariff",
              "likeness", "affecting", "lft"]


def bullet_list(items):
    return "\n".join(f"- {item}" for item in items) if items else "- None identified"


def fact_line(fact):
    status = "verified in description" if fact["verified"] else "NOT FOUND in description, check"
    quote = f"\u201c{fact['quote']}\u201d" if fact["quote"] else "(no quote given)"
    return f"{quote} ({status}): {fact['point']}"


def quote_line(quote):
    note = f" (pinpoint corrected by the app; the AI cited {quote['cited_as']})" \
        if quote["status"] == "corrected" else ""
    return f"\u201c{quote['text']}\u201d {quote['source']}{note}"


def authority_line(source):
    return f"{source['short']}: {source['citation']}" + (f" <{source['url']}>" if source["url"] else "")


def build_markdown_report(measure_text, output, review=None):
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
    if output.get("in_alternative"):
        lines += ["> Steps 7 and 8 were analysed in the alternative, on the assumption that the "
                  "products are like products.", ""]

    lines += ["| Element | Finding |", "|---|---|"]
    lines += [f"| {name} | {answer} |" for name, answer in outcome["elements"].items()]
    lines += ["", "## Summary", str(conclusion.get("executive_summary", "")), ""]

    lines += ["### Key uncertainties", bullet_list(conclusion.get("key_uncertainties", [])), ""]
    lines += ["### Next steps", bullet_list(conclusion.get("next_steps", [])), ""]

    similar = output.get("similar_cases", [])
    if similar:
        lines += ["## Most similar WTO disputes",
                  "*Chosen by the AI from short summaries of the disputes; check the reports.*", ""]
        for case in similar:
            lines += [f"**{case['short']}**: {case['why']}", f"*Facts: {case['summary']}*", ""]

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
        lines += [f"**Reasoning:** {r['reasoning']}", ""]
        if "supporting_facts" in r:
            lines += [
                "**Supporting facts**", bullet_list([fact_line(f) for f in r["supporting_facts"]]), "",
                "**Contrary factors**", bullet_list([fact_line(f) for f in r["contrary_factors"]]), "",
                f"*Fact check: {r['fact_check']}*", "",
            ]
        lines += [
            "**Evidence gaps**", bullet_list(r.get("evidence_gaps", [])), "",
            f"**Authorities quoted** ({r['quote_check']})",
        ]
        for quote in r.get("quotes", []):
            lines.append(f"> {quote_line(quote)}")
        for quote in r.get("removed_quotes", []):
            lines.append(f"- Removed (not found in any authority): \u201c{quote['text']}\u201d")

    lines += ["", "## Table of authorities", bullet_list(
        [authority_line(s) for s in output.get("authorities", [])])]

    if review:
        lines += ["", "## Human review"]
        if review["changed"]:
            lines += [f"**Outcome after review: {review['outcome']['label']}**", "",
                      f"AI outcome before review: {outcome['label']}", "",
                      "| Element | AI finding | After human review |", "|---|---|---|"]
            lines.append(f"| Within Article III:4 (Step 1) | {results['scope']['conclusion']} | "
                         f"{review['scope']} |")
            lines += [f"| {name} | {outcome['elements'][name]} | {answer} |"
                      for name, answer in review["elements"].items()]
            lines.append("")
        if review["notes"]:
            lines += ["**Review notes**", review["notes"]]
    return "\n".join(lines) + "\n"


def build_docx_report(measure_text, output, review=None):
    """Build the same report as a Word document and return it as bytes."""
    from io import BytesIO

    from docx import Document

    outcome = output["outcome"]
    conclusion = output["conclusion"]
    results = output["results"]

    doc = Document()
    doc.add_heading("GATT Article III:4 Analysis", level=0)
    doc.add_paragraph(
        f"Generated on {date.today().isoformat()} using {output['model']} "
        f"({output['ai_calls']} AI calls). This is not legal advice."
    )

    doc.add_heading("Measure analysed", level=1)
    doc.add_paragraph(measure_text.strip())

    doc.add_heading("Outcome", level=1)
    doc.add_paragraph().add_run(outcome["label"]).bold = True
    if outcome["scope_warning"]:
        doc.add_paragraph(outcome["scope_warning"])
    if output.get("in_alternative"):
        doc.add_paragraph("Steps 7 and 8 were analysed in the alternative, on the assumption "
                          "that the products are like products.")

    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Element"
    table.rows[0].cells[1].text = "Finding"
    for name, answer in outcome["elements"].items():
        row = table.add_row().cells
        row[0].text = name
        row[1].text = answer

    doc.add_heading("Summary", level=1)
    doc.add_paragraph(str(conclusion.get("executive_summary", "")))
    for heading, key in [("Key uncertainties", "key_uncertainties"), ("Next steps", "next_steps")]:
        doc.add_heading(heading, level=2)
        for item in conclusion.get(key, []) or ["None identified"]:
            doc.add_paragraph(str(item), style="List Bullet")

    if output.get("similar_cases"):
        doc.add_heading("Most similar WTO disputes", level=1)
        doc.add_paragraph("Chosen by the AI from short summaries of the disputes; check the reports.").runs[0].italic = True
        for case in output["similar_cases"]:
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(f"{case['short']}: ").bold = True
            p.add_run(case["why"])
            doc.add_paragraph(f"Facts: {case['summary']}").runs[0].italic = True

    doc.add_heading("Step-by-step analysis", level=1)
    for key in STEP_ORDER:
        if key not in results:
            continue
        r = results[key]
        doc.add_heading(f"{r['title']}: {r['conclusion']}", level=2)
        if r.get("rule_applied"):
            p = doc.add_paragraph()
            p.add_run("Rule applied: ").bold = True
            p.add_run(r["rule_applied"])
        p = doc.add_paragraph()
        p.add_run("Reasoning: ").bold = True
        p.add_run(r["reasoning"])
        sections = []
        if "supporting_facts" in r:
            sections += [("Supporting facts", [fact_line(f) for f in r["supporting_facts"]]),
                         ("Contrary factors", [fact_line(f) for f in r["contrary_factors"]])]
        sections.append(("Evidence gaps", r.get("evidence_gaps", [])))
        for label, items in sections:
            doc.add_paragraph().add_run(label).bold = True
            for item in items or ["None identified"]:
                doc.add_paragraph(str(item), style="List Bullet")
        if "fact_check" in r:
            doc.add_paragraph().add_run(f"Fact check: {r['fact_check']}").italic = True
        p = doc.add_paragraph()
        p.add_run("Authorities quoted: ").bold = True
        p.add_run(str(r["quote_check"]))
        for quote in r.get("quotes", []):
            doc.add_paragraph(quote_line(quote), style="Intense Quote")
        for quote in r.get("removed_quotes", []):
            doc.add_paragraph(f"Removed (not found in any authority): \u201c{quote['text']}\u201d")

    doc.add_heading("Table of authorities", level=1)
    for source in output.get("authorities", []) or []:
        doc.add_paragraph(authority_line(source), style="List Bullet")
    if not output.get("authorities"):
        doc.add_paragraph("No authorities were quoted in this analysis.")

    if review:
        doc.add_heading("Human review", level=1)
        if review["changed"]:
            doc.add_paragraph().add_run(f"Outcome after review: {review['outcome']['label']}").bold = True
            doc.add_paragraph(f"AI outcome before review: {outcome['label']}")
            table = doc.add_table(rows=1, cols=3)
            table.style = "Table Grid"
            for cell, text in zip(table.rows[0].cells, ["Element", "AI finding", "After human review"]):
                cell.text = text
            row = table.add_row().cells
            row[0].text, row[1].text, row[2].text = ("Within Article III:4 (Step 1)",
                                                     results["scope"]["conclusion"], review["scope"])
            for name, answer in review["elements"].items():
                row = table.add_row().cells
                row[0].text, row[1].text, row[2].text = name, outcome["elements"][name], answer
        if review["notes"]:
            doc.add_paragraph().add_run("Review notes").bold = True
            doc.add_paragraph(review["notes"])

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
