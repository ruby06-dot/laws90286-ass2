# National Treatment Analyser

LAWS90286 Legal AI, Assignment 2.

A Streamlit application that analyses, step by step, whether a government measure is inconsistent with the national treatment obligation in Article III:4 of the GATT 1994.

| | |
|---|---|
| Deployed application | https://d8mmc7kapwafftjm7vhgnw.streamlit.app/ |
| Password | Provided with the submission |
| API key | Enter your own OpenAI API key in the sidebar and click "Update API Key" |
| Recommended model | `gpt-4o` (the test cases were checked with this model) |

This tool does not provide legal advice.

---

## 1. The legal task

Article III:4 requires that imported products be accorded treatment no less favourable than that accorded to like domestic products in respect of all laws, regulations and requirements affecting their internal sale, offering for sale, purchase, transportation, distribution or use. A violation is established only if three elements are met.

1. The imported and domestic products are **like products**.
2. The measure is a **law, regulation or requirement affecting** their internal sale or use.
3. The imported products are accorded **less favourable treatment**.

Before these elements, the measure must fall within the **scope** of Article III:4. Taxes and charges fall under Article III:2 (internal taxes) or Article II (customs duties and import charges). Import bans and quotas that apply only to imported products fall under Article XI.

Each stage of this analysis turns on factors that are easy to overlook, such as when the obligation to pay a charge arises, how health risks bear on likeness, and whether a measure changes the conditions of competition. I built this tool to test whether an AI can apply this structure reliably and reach reasonably accurate answers.

The tool does not analyse Article III:2, Article II or justification under Article XX. Where Article III:2 or Article II is more likely to apply, Step 1 says so.

## 2. How the task is broken down

| Step | Sub-process | AI calls |
|---|---|---|
| 1 | Extract the facts and decide whether the measure is within the scope of Article III:4 | 1 |
| 2 to 5 | Like products, one criterion per step (physical properties, end-uses, consumers' tastes and habits, tariff classification) | 4 |
| 6 | Like products, overall finding | 1 |
| 7 | Law, regulation or requirement "affecting" internal sale etc. | 1 |
| 8 | Less favourable treatment | 1 |
| 9 | Conclusion, similar WTO disputes, key uncertainties and next steps | 1 |

A full run makes **9 AI calls**. More calls are made when a check fails and the step is retried (see section 3). If the user unticks "continue the analysis in the alternative" and the products are found not to be like, the run stops after Step 6 and makes 7 AI calls.

## 3. Design

**Control flow and outcome in Python.** Python, not the AI, sets the order of the steps, decides whether to stop early and fixes the outcome by boolean rules.

| Findings | Outcome |
|---|---|
| Step 1 is "No" | Article III:4 does not apply. The element findings are given in the alternative only |
| Any element is "No" | Violation not established |
| All three elements are "Yes" | Inconsistent with Article III:4 |
| Otherwise | Uncertain |

The AI in Step 9 explains this outcome but cannot change it.

**Narrow context.** Each step receives only its own legal test, the treaty text and the user's description. The legal tests in `prompts.py` summarise the relevant WTO case law.

**Structured output.** Steps 2 to 8 each return, as JSON, the rule applied, supporting facts, contrary factors, evidence gaps, quotes from the authorities, reasoning and a Yes, No or Uncertain finding. Step 1 returns the facts of the measure and a scope finding in the same way.

**Two deterministic checks (looping and reflection).** After each step, ordinary code checks the AI's answer.

- Every quote from the GATT text (Article III:1, III:4 and the Note Ad Article III) must appear word for word in the provision it cites. A quote found in another provision has its pinpoint corrected. A quote found nowhere is removed.
- Every fact the AI relies on must be a passage copied word for word from the user's description. Facts that fail are marked ⚠️ and kept for the user to check.

If a check fails, the failed items are sent back to the AI with an instruction to try again (up to 2 retries for quotes and 1 for facts). This loop lets the AI correct its own answer before the result is shown.

**Alternative analysis.** If an earlier finding is not "Yes" (for example, like products is not established, or Step 1 finds that Article III:4 does not apply), the later steps are analysed on the assumption that it is met, and the result says so.

**Human in the loop.** After each run the user is asked whether they are satisfied. If not, the "Revise & re-run" tab lets the user correct or add to the facts, choose another model and run the analysis again. All runs of the same description are compared step by step in a table. The comparison is made by code, not by the AI.

**Output.** The result page shows the outcome, a diagram of the steps, a summary, key uncertainties, next steps, the most similar WTO disputes with links to their WTO pages, the reasoning for each step and a table of authorities.

The user can add their own notes below the result. Press Ctrl+Enter (Mac ⌘+Enter) or click outside the box to save them before downloading.

The report can be downloaded straight away as a Word (.docx) or Markdown (.md) file. If the user is not satisfied, they can revise the facts or choose another model, run the analysis again and download the new report. That report also compares the runs.

## 4. Test cases

The three test cases are in `test_cases/`. Select one from the "Load a test case" menu and click **Load**, or upload the `.txt` file with the **Upload** button. Then click **Run analysis**.

The cases were chosen so that each one tests a different path through the tool.

| Test case | Expected outcome | Why it was chosen |
|---|---|---|
| 1. Separate retail channels for imported beef | 🔴 Inconsistent | A clear violation. It shows the full analysis when all three elements are met |
| 2. An import charge collected inside the country | 🔵 Article III:4 does not apply | A scope trap. It tests whether Step 1 recognises a measure that belongs under Article II or Article III:2, and shows how the tool was improved after it first failed |
| 3. Incomplete facts, then revise and re-run | 🟡 Uncertain, then 🔴 Inconsistent | Missing facts. It tests whether the tool avoids inventing facts, and shows the revise and re-run feature and the comparison of runs |

### Test case 1. Separate retail channels for imported beef

File `test_cases/case_1_separate_retail.txt`

Westland allows imported beef to be sold only in specialist stores, while domestic beef may be sold anywhere. 

| Step | Expected |
|---|---|
| 1 Scope | Yes (internal regulation on retail sale) |
| 2 to 6 Like products | Yes |
| 7 Affecting | Yes |
| 8 Less favourable treatment | Yes (conditions of competition modified to the detriment of imported beef) |
| **Outcome** | 🔴 **Inconsistent with Article III:4** |
| Most similar dispute | *Korea – Beef* |

Observed with gpt-4o. The expected outcome, with *Korea – Beef* as the most similar dispute. This case shows the tool working well on a clear case of origin-based differential treatment.

### Test case 2. An import charge collected inside the country

File `test_cases/case_2_deferred_import_charge.txt`

Northvale charges 12 per cent on imported scooters. The obligation to pay arises at customs clearance, but the charge is collected 60 days later by the domestic revenue agency. Northvale calls it an internal tax. The bound tariff rate is 5 per cent.

| Step | Expected |
|---|---|
| 1 Scope | **No** (a border charge under Article II, because the obligation arises at importation) |
| 7 and 8 | Analysed in the alternative only |
| **Outcome** | 🔵 **Article III:4 does not apply** |
| Most similar dispute | *China – Auto Parts* |

Observed with gpt-4o. The expected outcome. The summary and next steps point to Article II and the 5 per cent bound rate.

This case shows where the tool performed poorly and how it was improved. In the first version, Step 1 classified the charge as an internal tax, the summary misstated when the charge is collected, and Step 8 answered "No" because it carried the scope finding into the analysis of less favourable treatment. The scope test was then revised to ask when and why the obligation to pay arises (*China – Auto Parts*), a "does not apply" outcome was added, and Step 8 now states the assumptions of the alternative analysis.

### Test case 3. Incomplete facts, then revise and re-run

File `test_cases/case_3_honey_revise_and_rerun.txt`

Southvale requires a purity certificate for imported honey. The description deliberately leaves out key facts. This case has two parts.

**Part A. First run.** Load and run the case.

| | Expected |
|---|---|
| Like products | Uncertain (no facts about the products) |
| **Outcome** | 🟡 **Uncertain** |

**Part B. Revise and re-run.** Answer **No** to "Are you satisfied with this analysis?". The "Revise & re-run" tab opens. Paste the text below into **Points to emphasise or clarify** and click **Run the analysis again**.

```
Domestic honey does not need a purity certificate. Each certificate costs 600 Southvale dollars per batch. Only two laboratories are approved, both in Southvale, and the waiting time for a certificate is about six weeks. Imported and domestic honey are physically the same product, are used in the same ways, are sold side by side on supermarket shelves at similar prices, and fall under the same tariff heading (0409).
```

| | Expected |
|---|---|
| Like products, affecting, less favourable treatment | Yes |
| **Outcome** | 🔴 **Inconsistent with Article III:4** |
| Comparison of runs | Steps 2 to 6 and the outcome marked "differs". "Facts used" shows Original and Revised |

Observed with gpt-4o. Part A gave Uncertain and Part B gave Inconsistent, as expected. The case shows that the tool does not fill gaps with invented facts, and that a user can supply the missing facts and see their effect.

It also shows a limitation. In two runs of Part A with the same model and the same facts, Step 8 was answered "Yes" once and "Uncertain" once. A temperature of 0 does not make the model fully deterministic.

### Additional case (optional). An origin-neutral packaging rule

Why it was chosen. Test case 3 is uncertain because facts are missing and can be supplied. This case is uncertain because the evidence on less favourable treatment is unsupported, so it tests whether the tool treats an unproven claim as proof.

File `additional_cases/extra_uncertain_recycled_bottles.txt`, shown in the menu as "(extra)".

Lowland requires all bottled water to be sold in bottles made from at least 50 per cent recycled plastic. The rule applies equally to domestic and imported water and does not mention origin. There is no information on how many suppliers already meet the standard or on the cost of switching. Exporters claim the rule will cost them more but provide no figures.

| Step | Expected |
|---|---|
| 2 to 6 Like products | Yes |
| 7 Affecting | Yes |
| 8 Less favourable treatment | Uncertain (no evidence of a detrimental effect on imported products) |
| **Outcome** | 🟡 **Uncertain** |

Observed with gpt-4o. The expected outcome. The tool did not treat the exporters' unsupported claim as proof of less favourable treatment.

## 5. Artefacts for the tests

All test descriptions are plain text files in `test_cases/` and `additional_cases/`. They can be loaded from the menu or uploaded with the Upload button. The text to paste in test case 3, Part B, is set out above. No other files are needed.

## 6. API credentials module

`credentials.py` is based on the course module at https://github.com/stoneman-mls/openai_credentials. The changes are as follows.

- The key is entered in a masked field and is not displayed on the page.
- The session state is set up inside the function, so that it works for every user session.
- After the key is saved, the app lists the chat models that the key can use (this does not use tokens) and the user can choose one. `gpt-4o` is the default.
- A "Remove API key (log out)" button clears the key.

No API key is stored in this repository.

## 7. Limitations

- **Only the most important authorities are included.** Many WTO and GATT reports bear on Article III:4. The tool draws on a selection of the most important ones (section 8), so its analysis may miss points that other reports would raise and may be less accurate in less common situations.
- **Case law is summarised rather than quoted.** The key principles from WTO case law are summarised in the legal test for each step. The full reports are not stored in the tool, so quotes are checked against the GATT text only. Adding the full reports would let the AI quote them directly, but finding the right passages in so large a body of material would bring its own risk of error. The tool is built so that excerpts from the reports can be added later, and they would then be checked in the same way.
- **Likeness is assessed through a fixed set of criteria.** The tool assesses likeness through the four criteria drawn from the Border Tax Adjustments report, one step each, and then weighs them in Step 6. In WTO law these criteria are analytical tools rather than a closed list. Likeness is a case-by-case judgment about the competitive relationship between the products, and other evidence may be relevant. Because each criterion is analysed in a separate step, the tool may treat the test more like a checklist than a panel would, and may give too little weight to evidence that falls outside the four criteria or that bears on several of them at once.
- **The checks test sources, not reasoning.** The fact check confirms that a fact appears in the user's text. It cannot confirm that the AI used the fact correctly. It is also strict, so a quote that drops a few words is flagged even when its meaning is unchanged.
- **Model and run variation.** Different models, and sometimes repeated runs of the same model, reach different findings on borderline steps. The comparison table makes this visible.
- **Scope of the tool.** The tool does not analyse Article III:2, Article II or Article XX.

## 8. Key authorities

Many reports are relevant to Article III:4. The tool relies on the most important of them, listed below. A wider list of disputes, used only to find similar cases, is in `knowledge/cases/`.

- Appellate Body Report, *Korea – Measures Affecting Imports of Fresh, Chilled and Frozen Beef*, WTO Doc WT/DS161/AB/R, WT/DS169/AB/R (11 December 2000)
- Appellate Body Report, *European Communities – Measures Affecting Asbestos and Asbestos-Containing Products*, WTO Doc WT/DS135/AB/R (12 March 2001)
- Appellate Body Report, *China – Measures Affecting Imports of Automobile Parts*, WTO Doc WT/DS339/AB/R, WT/DS340/AB/R, WT/DS342/AB/R (15 December 2008)
- Appellate Body Report, *Thailand – Customs and Fiscal Measures on Cigarettes from the Philippines*, WTO Doc WT/DS371/AB/R (17 June 2011)
- Appellate Body Report, *European Communities – Measures Prohibiting the Importation and Marketing of Seal Products*, WTO Doc WT/DS400/AB/R, WT/DS401/AB/R (22 May 2014)

## 9. Running locally

```bash
pip install -r requirements.txt
mkdir -p .streamlit
echo 'APP_PASSWORD = "<the password provided with the submission>"' > .streamlit/secrets.toml
streamlit run home.py
```

The app password is read from Streamlit secrets and is not stored in the repository. On Streamlit Cloud it is set in the app's Settings under Secrets. Locally it is read from `.streamlit/secrets.toml`, which is excluded from Git.

## 10. Repository structure

```
home.py              Streamlit interface, password gate, results, revise and re-run, comparison
analysis.py          Step-by-step pipeline, control flow, retries and outcome rules
prompts.py           Legal tests and prompt templates for each step
authorities.py       Knowledge files, quote and fact checks, similar disputes
report.py            Word and Markdown reports
credentials.py       API credentials sidebar (based on the course module)
knowledge/treaty/    Text of GATT Article III:1, III:4 and the Note Ad Article III
knowledge/cases/     WTO disputes (citation, link and a one-line summary of the facts)
test_cases/          The three test cases
additional_cases/    The optional additional case
.streamlit/          Theme settings
requirements.txt     Python packages
```
## 11. Technologies used

- **Python and Streamlit.** Application logic, the interface, session state and the password gate. Deployed on Streamlit Community Cloud.
- **OpenAI Python SDK.** One Chat Completions call per step, with JSON output and a temperature of 0 where the model allows it. The model list is read from the user's API key. `gpt-4o` is the default.
- **python-docx.** The downloadable Word report.
- **Python standard library.** The quote and fact checks use ordinary string matching, so they do not depend on the AI.
The tool does not use embeddings or a vector database. Each step receives a short, fixed legal test and the relevant treaty text, which is small enough to send in full.


## 12. Acknowledgements

The legal task, the choice of steps, the legal tests and the test cases were designed by the author. Claude assisted with coding, debugging, modifying the test cases and this README. All test cases are fictional, and the tool's output requires human review.

The API credentials sidebar is based on the course module.