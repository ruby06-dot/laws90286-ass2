"""Prompt text and legal tests for each analysis step.

The legal tests in this file are paraphrased summaries of WTO jurisprudence,
written for this application. They are NOT quotations. Verbatim excerpts from
the treaty text and Appellate Body / panel reports live in the knowledge/ folder,
and only those excerpts may be quoted by the model.
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

ELEMENT_OUTPUT_FORMAT = """Return a JSON object with exactly these keys:
{
  "rule_applied": "one or two sentences stating the legal test you applied",
  "supporting_facts": ["facts from the description that support a 'Yes' answer"],
  "contrary_factors": ["facts or considerations that point towards 'No'"],
  "evidence_gaps": ["missing information that would change or firm up the answer"],
  "reasoning": "a short paragraph applying the test to the facts",
  "conclusion": "Yes" or "No" or "Uncertain",
  "quotes": ["sentences copied character-for-character from AUTHORITIES that support your reasoning"]
}
"quotes" must be an empty list if AUTHORITIES is empty or nothing there is relevant.
Never put text in "quotes" that does not appear word-for-word in AUTHORITIES.
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
  "measure_type": "internal_regulation" or "internal_tax" or "border_measure" or "unclear",
  "within_article_III_4": "Yes" or "No" or "Uncertain",
  "scope_reasoning": "a short paragraph explaining the characterisation of the measure",
  "evidence_gaps": ["missing information that matters for scope"],
  "quotes": ["sentences copied character-for-character from AUTHORITIES; empty list if none"]
}
"distinction_basis" is "origin" only if the measure expressly distinguishes products by their \
national origin."""

CONCLUSION_OUTPUT_FORMAT = """Return a JSON object with exactly these keys:
{
  "executive_summary": "a short paragraph stating the outcome and the main reasons",
  "element_summaries": {
    "like_products": "one or two sentences",
    "affecting": "one or two sentences, or 'Not analysed' if the step was skipped",
    "less_favourable_treatment": "one or two sentences, or 'Not analysed' if the step was skipped"
  },
  "key_uncertainties": ["the points on which the outcome is most vulnerable"],
  "next_steps": ["what a lawyer should check or argue next"]
}"""


# ---------------------------------------------------------------------------
# Legal tests (paraphrased summaries, not quotations)
# ---------------------------------------------------------------------------

SCOPE_RULE = """Article III:4 applies to internal laws, regulations and requirements affecting \
the internal sale, offering for sale, purchase, transportation, distribution or use of products. \
Internal taxes and other internal charges fall under Article III:2, not Article III:4. \
Measures applied only at the border to imported products, with no domestic counterpart \
(for example an import ban or quota), fall under Article XI. Under the Note Ad Article III, \
a law, regulation or requirement that applies to both the imported product and the like \
domestic product, but is enforced on the imported product at the time or point of importation, \
is still an internal measure subject to Article III."""

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
        "knowledge_file": None,
        "rule": SCOPE_RULE,
        "question": "Extract the key facts and decide whether the measure is an internal law, "
                    "regulation or requirement within the scope of Article III:4.",
    },
    "physical_properties": {
        "title": "Step 2: Like products, criterion 1 (physical properties)",
        "knowledge_file": "like_products.txt",
        "rule": PHYSICAL_RULE,
        "question": "Do the physical properties point towards the imported and domestic products "
                    "being 'like'? Answer Yes if they point towards likeness, No if against.",
    },
    "end_uses": {
        "title": "Step 3: Like products, criterion 2 (end-uses)",
        "knowledge_file": "like_products.txt",
        "rule": END_USES_RULE,
        "question": "Do the end-uses point towards the products being 'like'? "
                    "Answer Yes if they point towards likeness, No if against.",
    },
    "consumers": {
        "title": "Step 4: Like products, criterion 3 (consumers' tastes and habits)",
        "knowledge_file": "like_products.txt",
        "rule": CONSUMERS_RULE,
        "question": "Do consumers' tastes and habits point towards the products being 'like'? "
                    "Answer Yes if they point towards likeness, No if against.",
    },
    "tariff": {
        "title": "Step 5: Like products, criterion 4 (tariff classification)",
        "knowledge_file": "like_products.txt",
        "rule": TARIFF_RULE,
        "question": "Does tariff classification point towards the products being 'like'? "
                    "Answer Yes if it points towards likeness, No if against.",
    },
    "likeness": {
        "title": "Step 6: Like products, overall finding",
        "knowledge_file": "like_products.txt",
        "rule": LIKENESS_SYNTHESIS_RULE,
        "question": "Weighing everything, are the imported and domestic products 'like products' "
                    "under Article III:4? Answer Yes if they are like products.",
    },
    "affecting": {
        "title": "Step 7: Law, regulation or requirement 'affecting' internal sale etc.",
        "knowledge_file": "affecting.txt",
        "rule": AFFECTING_RULE,
        "question": "Is the measure a law, regulation or requirement affecting the internal sale, "
                    "offering for sale, purchase, transportation, distribution or use of the products? "
                    "Answer Yes if it is.",
    },
    "lft": {
        "title": "Step 8: Less favourable treatment",
        "knowledge_file": "less_favourable_treatment.txt",
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

    parts = [
        f"CURRENT STEP: {step['title']}",
        f"QUESTION: {step['question']}",
        f"LEGAL TEST (apply this test only):\n{step['rule']}",
        f"AUTHORITIES (verbatim excerpts; only these may be quoted):\n<<<\n{authorities_block}\n>>>",
        f"MEASURE DESCRIPTION PROVIDED BY THE USER:\n<<<\n{measure_text}\n>>>",
    ]
    if facts_json:
        parts.append(f"STRUCTURED FACTS FROM STEP 1:\n{facts_json}")
    if earlier_results:
        parts.append(f"RESULTS OF EARLIER STEPS:\n{earlier_results}")
    parts.append(output_format)
    return "\n\n".join(parts)


def build_conclusion_prompt(measure_text, outcome, all_results_json):
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
        "If like products was not answered Yes, describe any findings on the other elements as "
        "made in the alternative (that is, on the assumption that the products are like products), "
        "not as settled findings.",
        "If a violation is established, note in next_steps that the responding Member may seek to "
        "justify the measure under GATT Article XX, which this tool does not analyse.",
        CONCLUSION_OUTPUT_FORMAT,
    ])