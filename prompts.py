"""Prompt text and legal tests for each analysis step.

The legal tests in this file are paraphrased summaries of WTO jurisprudence,
written for this application. They are NOT quotations. Verbatim excerpts from
the treaty text and Appellate Body / panel reports live in knowledge/treaty and
knowledge/cases (see authorities.py), and only those excerpts may be quoted.
"""

SYSTEM_PROMPT = """You are a careful WTO law analyst assisting a lawyer. You analyse whether a \
measure is inconsistent with Article III:4 of the GATT 1994 (national treatment for internal \
laws, regulations and requirements).

Working rules:
- Apply only the legal test you are given for the current step. Do not merge it with other \
tests (for example, do not apply TBT Agreement Article 2.1 or GATT Article XX).
- Use only the facts in the measure description. Never invent facts, statistics, products or case law.
- If the facts are insufficient, record what is missing in "evidence_gaps" and answer \
"Uncertain" rather than guessing.
- Respond with a single JSON object only, written in English."""


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------

FACT_RULES = """Rules for facts: each "quote" in "supporting_facts" and "contrary_factors" must be \
one continuous passage copied exactly from the MEASURE DESCRIPTION, with no ellipses, no paraphrase \
and no added words. Keep it short (a phrase or one sentence). If a point does not rest on a \
specific passage of the description, put it in "reasoning" or "evidence_gaps" instead."""

QUOTE_RULES = """Rules for authorities: each item in "quotes" must name one SOURCE label from \
AUTHORITIES and copy text that appears under that SOURCE, character-for-character. "quotes" must \
be an empty list if nothing in AUTHORITIES is relevant. When your reasoning relies on an \
authority, cite it by its SOURCE label, for example (Korea – Beef (AB) [137])."""

ELEMENT_OUTPUT_FORMAT = """Return a JSON object with exactly these keys:
{
  "rule_applied": "one or two sentences stating the legal test you applied",
  "supporting_facts": [{"quote": "a passage copied word-for-word from the MEASURE DESCRIPTION", \
"point": "why this fact supports a 'Yes' answer"}],
  "contrary_factors": [{"quote": "a passage copied word-for-word from the MEASURE DESCRIPTION", \
"point": "why this fact points towards 'No'"}],
  "evidence_gaps": ["missing information that would change or firm up the answer"],
  "reasoning": "a short paragraph applying the test to the facts",
  "conclusion": "Yes" or "No" or "Uncertain",
  "quotes": [{"source": "the SOURCE label exactly as written in AUTHORITIES", \
"text": "a sentence copied character-for-character from the TEXT under that SOURCE"}]
}
""" + FACT_RULES + "\n" + QUOTE_RULES + """
Your conclusion must be consistent with the facts you list. Where the description states facts \
relevant to this step, weigh them and answer "Yes" or "No". Answer "Uncertain" only if the \
description contains no relevant facts for this step, or the relevant facts point equally both ways."""

SCOPE_OUTPUT_FORMAT = """Return a JSON object with exactly these keys:
{
  "measure_summary": "one or two sentences describing the measure",
  "imposing_member": "the WTO Member imposing the measure, or 'Not stated'",
  "imported_product": "the imported product affected",
  "domestic_product": "the domestic product it is compared with",
  "differential_treatment": "how the treatment of the imported product differs, in form or in effect",
  "distinction_basis": "origin" or "origin-neutral" or "unclear",
  "measure_type": "internal_regulation" or "internal_tax" or "border_measure" or "unclear" \
(border_measure covers customs duties, other import charges, import bans and quotas),
  "within_article_III_4": "Yes" or "No" or "Uncertain",
  "scope_reasoning": "a short paragraph explaining the characterisation of the measure",
  "evidence_gaps": ["missing information that matters for scope"],
  "quotes": [{"source": "the SOURCE label exactly as written in AUTHORITIES", \
"text": "a sentence copied character-for-character from the TEXT under that SOURCE"}]
}
"distinction_basis" is "origin" only if the measure expressly distinguishes products by their \
national origin.
""" + QUOTE_RULES

CONCLUSION_OUTPUT_FORMAT = """Return a JSON object with exactly these keys:
{
  "executive_summary": "a short paragraph stating the outcome and the main reasons",
  "element_summaries": {
    "like_products": "one or two sentences",
    "affecting": "one or two sentences, or 'Not analysed' if the step was skipped",
    "less_favourable_treatment": "one or two sentences, or 'Not analysed' if the step was skipped"
  },
  "key_uncertainties": ["2 to 4 specific points on which the outcome is most vulnerable, \
each tied to a step and a missing or contested fact"],
  "next_steps": ["2 to 4 concrete actions for a lawyer, such as evidence to gather, arguments \
the other side is likely to raise, or authorities to read"],
  "similar_disputes": [{"case": "a name copied exactly from DISPUTE LIST", \
"why": "two sentences: the main factual similarity, then the main factual difference"}]
}
"similar_disputes" lists up to three disputes from DISPUTE LIST whose facts are most similar to \
the user's measure, most similar first. Compare facts (the kind of measure and how it treats \
imported products), not just the legal issue. In "why", do not repeat the summary; say what is \
similar and what is different. Use only the summaries in DISPUTE LIST. Return an empty list if \
none is genuinely similar."""


# ---------------------------------------------------------------------------
# Legal tests (paraphrased summaries, not quotations)
# ---------------------------------------------------------------------------

SCOPE_RULE = """Article III:4 applies to internal laws, regulations and requirements affecting \
the internal sale, offering for sale, purchase, transportation, distribution or use of products. \
Apply these points in order:
1. Taxes and charges are never 'laws, regulations and requirements' under Article III:4. Internal \
taxes and other internal charges fall under Article III:2. Customs duties and other charges \
imposed on or in connection with importation fall under Article II. If the measure is a tax or \
charge of either kind, the answer is No.
2. To decide whether a charge is a border charge or an internal charge, what matters is when and \
why the obligation to pay arises, not when or where the charge is collected (Appellate Body, \
China – Auto Parts). A charge whose obligation arises at the moment of, and by virtue of, \
importation is a border charge, even if it is collected later or inside the territory, and even \
if the Member calls it an internal tax. A charge triggered by an internal event after importation \
(such as internal sale, use or assembly) is an internal charge.
3. Measures applied only to imported products at the border, with no domestic counterpart \
(for example an import ban or quota), fall under Article XI.
4. Under the Note Ad Article III, a law, regulation or requirement that applies to both the \
imported product and the like domestic product, but is enforced on the imported product at the \
time or point of importation, is still an internal measure subject to Article III. The Note does \
not apply where there is no counterpart measure for like domestic products."""

LIKENESS_GENERAL = """Under Article III:4, 'likeness' is fundamentally a determination about the \
nature and extent of a competitive relationship between the imported and domestic products \
(Appellate Body, EC – Asbestos). It is assessed case by case. Four criteria, drawn from the \
1970 Working Party Report on Border Tax Adjustments, are commonly used as analytical tools: \
(i) physical properties; (ii) end-uses; (iii) consumers' tastes and habits; \
(iv) tariff classification. They are tools, not a closed checklist, and all relevant evidence \
must be weighed together."""

PHYSICAL_RULE = LIKENESS_GENERAL + """

For this step, examine only criterion (i), physical properties: the products' composition, \
nature and quality. Physical differences matter to the extent that they affect the competitive \
relationship. Evidence of health risks associated with a product's physical properties may be \
relevant (Appellate Body, EC – Asbestos). A health risk that results from a product's composition \
(for example, a fibre that is carcinogenic) is a fact about its physical properties and should be \
weighed here."""

END_USES_RULE = LIKENESS_GENERAL + """

For this step, examine only criterion (ii), end-uses: the extent to which the products are \
capable of performing the same or similar functions. Where the products share some end-uses \
but not others, weigh the extent of the overlap."""

CONSUMERS_RULE = LIKENESS_GENERAL + """

For this step, examine only criterion (iii), consumers' tastes and habits: the extent to which \
consumers perceive and treat the products as alternative means of satisfying a particular want \
or demand. Evidence of substitution (for example cross-price elasticity) is relevant. Consumers' \
perceptions of health risks may affect this criterion (Appellate Body, EC – Asbestos). \
Consumers include commercial purchasers and users, such as manufacturers or construction firms, \
not only final consumers. Facts about how these purchasers actually behave, including avoiding a \
product because of health or safety concerns, are relevant and should be weighed. However, the \
regulating Member's own policy objective, or the reasons it gives for the measure, is not by \
itself evidence of consumers' tastes and habits. If the description contains no facts about how \
purchasers or consumers behave, answer "Uncertain"."""

TARIFF_RULE = LIKENESS_GENERAL + """

For this step, examine only criterion (iv), tariff classification: whether the products fall \
under the same tariff classification, ideally at a sufficiently detailed level of the \
Harmonized System. Identical classification may indicate likeness; different classification may \
indicate the opposite. This criterion is not decisive on its own."""

LIKENESS_SYNTHESIS_RULE = LIKENESS_GENERAL + """

For this step, weigh the results of the four criteria together. No single criterion is decisive. \
Where a measure distinguishes between products exclusively on the basis of their origin, panels \
have accepted that likeness may be presumed without a full comparison of the four criteria; \
consider this only if the distinction is expressly origin-based."""

AFFECTING_RULE = """Article III:4 covers 'all laws, regulations and requirements affecting' the \
internal sale, offering for sale, purchase, transportation, distribution or use of products. \
The word 'affecting' has a broad scope. It covers not only measures that directly regulate the \
sale of products but also measures that may modify the conditions of competition between \
imported and domestic products in the internal market (GATT Panel, Italy – Agricultural \
Machinery; Appellate Body, US – FSC (Article 21.5 – EC)). 'Requirements' may include \
commitments that private enterprises accept in exchange for an advantage from the government \
(Panel, Canada – Autos)."""

LFT_RULE = """Imported products must be accorded treatment no less favourable than that accorded \
to like domestic products. Apply these principles:
1. Formally different treatment is neither necessary nor sufficient for a violation. The question \
is whether the measure modifies the conditions of competition in the internal market to the \
detriment of imported products (Appellate Body, Korea – Beef).
2. Compare the group of like imported products with the group of like domestic products. A Member \
may draw distinctions between like products without necessarily according less favourable \
treatment to the group of imported products (Appellate Body, EC – Asbestos).
3. Less favourable treatment in some instances cannot be offset by more favourable treatment in \
others (GATT Panel, US – Section 337).
4. Actual trade effects need not be shown; Article III protects expectations of equal \
competitive opportunities.
5. There must be a genuine relationship between the measure and its adverse impact on competitive \
opportunities for imported products (Appellate Body, Thailand – Cigarettes (Philippines)).
6. Under Article III:4 there is no further inquiry into whether the detrimental impact stems \
exclusively from a legitimate regulatory distinction (Appellate Body, EC – Seal Products). \
That inquiry belongs to TBT Article 2.1, and policy justification belongs to GATT Article XX. \
Do not apply either here.
7. There is no separate requirement to show that the measure is applied 'so as to afford \
protection to domestic production' (Appellate Body, EC – Bananas III)."""


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------
# "question" tells the model what "Yes" means for that step.

STEPS = {
    "scope": {
        "title": "Step 1: Facts and scope of Article III:4",
        "rule": SCOPE_RULE,
        "question": "Extract the key facts and decide whether the measure is an internal law, "
                    "regulation or requirement within the scope of Article III:4.",
    },
    "physical_properties": {
        "title": "Step 2: Like products, criterion 1 (physical properties)",
        "rule": PHYSICAL_RULE,
        "question": "Do the physical properties point towards the imported and domestic products "
                    "being 'like'? Answer Yes if they point towards likeness, No if against.",
    },
    "end_uses": {
        "title": "Step 3: Like products, criterion 2 (end-uses)",
        "rule": END_USES_RULE,
        "question": "Do the end-uses point towards the products being 'like'? "
                    "Answer Yes if they point towards likeness, No if against.",
    },
    "consumers": {
        "title": "Step 4: Like products, criterion 3 (consumers' tastes and habits)",
        "rule": CONSUMERS_RULE,
        "question": "Do consumers' tastes and habits point towards the products being 'like'? "
                    "Answer Yes if they point towards likeness, No if against.",
    },
    "tariff": {
        "title": "Step 5: Like products, criterion 4 (tariff classification)",
        "rule": TARIFF_RULE,
        "question": "Does tariff classification point towards the products being 'like'? "
                    "Answer Yes if it points towards likeness, No if against.",
    },
    "likeness": {
        "title": "Step 6: Like products, overall finding",
        "rule": LIKENESS_SYNTHESIS_RULE,
        "question": "Weighing everything, are the imported and domestic products 'like products' "
                    "under Article III:4? Answer Yes if they are like products.",
    },
    "affecting": {
        "title": "Step 7: Law, regulation or requirement 'affecting' internal sale etc.",
        "rule": AFFECTING_RULE,
        "question": "Is the measure a law, regulation or requirement affecting the internal sale, "
                    "offering for sale, purchase, transportation, distribution or use of the products? "
                    "Answer Yes if it is.",
    },
    "lft": {
        "title": "Step 8: Less favourable treatment",
        "rule": LFT_RULE,
        "question": "Does the measure accord imported products less favourable treatment than like "
                    "domestic products? Answer Yes if it does.",
    },
}

LIKENESS_CRITERIA = ["physical_properties", "end_uses", "consumers", "tariff"]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_step_prompt(step_key, measure_text, authorities, facts_json="", earlier_results=""):
    """Build the user prompt for one analysis step."""
    step = STEPS[step_key]
    output_format = SCOPE_OUTPUT_FORMAT if step_key == "scope" else ELEMENT_OUTPUT_FORMAT
    authorities_block = authorities if authorities.strip() else "[No excerpts loaded.]"
    # Each excerpt is shown as "SOURCE: <short citation>" followed by "TEXT: <verbatim text>".

    parts = [
        f"CURRENT STEP: {step['title']}",
        f"QUESTION: {step['question']}",
        f"LEGAL TEST (apply this test only):\n{step['rule']}",
        f"AUTHORITIES (verbatim excerpts, each with a SOURCE label; only these may be quoted):\n<<<\n{authorities_block}\n>>>",
        f"MEASURE DESCRIPTION PROVIDED BY THE USER:\n<<<\n{measure_text}\n>>>",
    ]
    if facts_json:
        parts.append(f"STRUCTURED FACTS FROM STEP 1:\n{facts_json}")
    if earlier_results:
        parts.append(f"RESULTS OF EARLIER STEPS:\n{earlier_results}")
    parts.append(output_format)
    return "\n\n".join(parts)


def build_conclusion_prompt(measure_text, outcome, all_results_json, dispute_list=""):
    """Build the user prompt for the final conclusion step.

    The outcome is decided by Python (boolean logic over the three elements).
    The model only explains it and must not change it.
    """
    return "\n\n".join([
        "CURRENT STEP: Final conclusion on Article III:4",
        f"OUTCOME (already determined by the application's rules; do not change it):\n{outcome}",
        "Rule used to determine the outcome: a violation of Article III:4 is established only if "
        "all three elements (like products; law, regulation or requirement affecting internal "
        "sale etc.; less favourable treatment) are answered Yes. If any element is No, a violation "
        "is not established. Otherwise the outcome is uncertain.",
        f"MEASURE DESCRIPTION PROVIDED BY THE USER:\n<<<\n{measure_text}\n>>>",
        f"RESULTS OF ALL STEPS:\n{all_results_json}",
        f"DISPUTE LIST (name: facts of the dispute):\n{dispute_list or '[No disputes listed.]'}",
        "Use only the facts stated in the MEASURE DESCRIPTION. Do not add facts or change them "
        "(for example, when, where or by whom something is done).",
        "If the OUTCOME says that Article III:4 does not apply, explain why, based on Step 1, and "
        "name the provision that is more likely to apply (for example Article II or Article III:2). "
        "Describe the findings on the three elements as made in the alternative only. In that "
        "case, key_uncertainties and next_steps should focus on the characterisation of the "
        "measure and on the provision that is more likely to apply (for example, whether a charge "
        "exceeds a bound tariff rate under Article II), not on the alternative element findings.",
        "If like products was not answered Yes, describe any findings on the other elements as "
        "made in the alternative (that is, on the assumption that the products are like products), "
        "not as settled findings.",
        "If a violation is established, note in next_steps that the responding Member may seek to "
        "justify the measure under GATT Article XX, which this tool does not analyse.",
        CONCLUSION_OUTPUT_FORMAT,
    ])
