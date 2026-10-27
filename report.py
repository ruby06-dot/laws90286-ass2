"""Builds downloadable Markdown and Word reports from the analysis output."""

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
    if output.get("in_alternative"):
        lines += ["> Steps 7 and 8 were analysed in the alternative, on the assumption that the "
                  "products are like products.", ""]

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


def build_docx_report(measure_text, output):
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
        for label, field in [("Supporting facts", "supporting_facts"),
                             ("Contrary factors", "contrary_factors"),
                             ("Evidence gaps", "evidence_gaps")]:
            doc.add_paragraph().add_run(label).bold = True
            for item in r.get(field, []) or ["None identified"]:
                doc.add_paragraph(item, style="List Bullet")
        p = doc.add_paragraph()
        p.add_run("Quote check: ").bold = True
        p.add_run(str(r["quote_check"]))
        for quote in r.get("quotes", []):
            doc.add_paragraph(quote, style="Intense Quote")

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()