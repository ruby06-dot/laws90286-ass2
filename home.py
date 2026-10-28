"""GATT Article III:4 National Treatment Analyser (LAWS90286 Assignment 2).

Run locally with:  streamlit run home.py
"""

import hmac
from pathlib import Path

import streamlit as st

from analysis import Article3_4Analysis, outcome_from_elements
from authorities import load_library
from credentials import get_openai_client, select_model
from report import STEP_ORDER, build_docx_report, build_markdown_report

APP_PASSWORD = "12436"   # repository is private; move to Streamlit secrets before making it public
APP_TITLE = "National Treatment Analyser"
APP_SUBTITLE = "Step-by-step analysis under GATT 1994 Article III:4"
TEST_CASE_DIR = Path(__file__).parent / "test_cases"

st.set_page_config(page_title=APP_TITLE, page_icon="⚖️", layout="wide")


# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------

def password_ok():
    if st.session_state.get("authenticated"):
        return True

    # Centre a narrow login box on the page.
    _, middle, _ = st.columns([1, 1.6, 1])
    with middle:
        st.write("")
        st.write("")
        st.markdown(f"<h1 style='text-align: center; font-size: 1.85rem;'>⚖️ {APP_TITLE}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: grey;'>{APP_SUBTITLE}</p>",
                    unsafe_allow_html=True)
        # Centre the Enter button inside the login form.
        st.markdown(
            "<style>"
            "div[data-testid='stElementContainer']:has(div[data-testid='stFormSubmitButton']),"
            "div:has(> div[data-testid='stFormSubmitButton']),"
            "div[data-testid='stFormSubmitButton'] {width: 100%; display: flex; justify-content: center;}"
            "div[data-testid='stFormSubmitButton'] button {width: auto; padding: 0 2rem;}"
            "</style>",
            unsafe_allow_html=True,
        )
        with st.form("login"):
            entered = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Enter", type="primary")
        if submitted:
            if hmac.compare_digest(entered, APP_PASSWORD):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.markdown("<p style='text-align: center; color: grey; font-size: 0.85rem;'>"
                    "LAWS90286 Legal AI, Assignment 2. This tool does not provide legal advice.</p>",
                    unsafe_allow_html=True)
    return False


if not password_ok():
    st.stop()


# ---------------------------------------------------------------------------
# Sidebar: API credentials
# ---------------------------------------------------------------------------

client = get_openai_client()
model = select_model(client)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

st.title(f"⚖️ {APP_TITLE}")
st.caption(APP_SUBTITLE)
st.write(
    "Describe the measure at issue and the relevant facts. The tool analyses, step by step, whether it is "
    "inconsistent with the national treatment obligation in Article III:4 of the GATT 1994 "
    "(internal laws, regulations and requirements). It does not analyse internal taxes "
    "(Article III:2) or justification under Article XX. This is not legal advice."
)

with st.expander("How the analysis works"):
    st.markdown(
        "1. **Facts and scope.** Extract the facts and check that the measure is an internal "
        "law, regulation or requirement, rather than a tax, a customs duty or another border "
        "measure. If it is not, Article III:4 does not apply and the later steps are only an "
        "alternative analysis.\n"
        "2. **Like products.** Four separate steps for physical properties, end-uses, consumers' "
        "tastes and habits, and tariff classification, then an overall finding.\n"
        "3. **'Affecting' internal sale etc.** Is the measure a law, regulation or requirement "
        "affecting the internal sale, purchase, distribution or use of the products?\n"
        "4. **Less favourable treatment.** Does the measure modify the conditions of competition "
        "to the detriment of imported products?\n"
        "5. **Conclusion.** The outcome is decided by fixed rules: a violation is established "
        "only if all three elements are met. The AI then explains the outcome.\n\n"
        "**Two checks by ordinary code (no AI):**\n"
        "- Every quote from a WTO report or the GATT must appear word-for-word in the paragraph "
        "it cites. A quote found in a different paragraph has its pinpoint corrected; a quote "
        "found nowhere is removed.\n"
        "- Every fact the AI relies on must appear word-for-word in your description. Facts that "
        "fail are marked ⚠️ for you to check.\n\n"
        "Failed checks are first sent back to the AI for another attempt."
    )

# Warn about formatting problems in the knowledge files (shown only if there are any).
for source in load_library():
    for problem in source["problems"]:
        st.warning(f"knowledge file {source['id']}.txt: {problem}")


def load_test_case():
    name = st.session_state.get("selected_case")
    if name:
        st.session_state["measure_text"] = (TEST_CASE_DIR / name).read_text(encoding="utf-8")


test_cases = sorted(p.name for p in TEST_CASE_DIR.glob("*.txt")) if TEST_CASE_DIR.exists() else []
if test_cases:
    col_a, col_b = st.columns([5, 1], vertical_alignment="bottom")
    with col_a:
        st.selectbox("Load a test case (optional)", test_cases, key="selected_case")
    with col_b:
        st.button("Load", on_click=load_test_case)

measure_text = st.text_area(
    "Measure description",
    key="measure_text",
    height=220,
    placeholder="Describe the measure, the imported and domestic products, and how each is treated.",
)


def load_uploaded_file():
    """Copy an uploaded .txt file into the measure description box."""
    uploaded = st.session_state.get("uploaded_file")
    if uploaded is not None:
        st.session_state["measure_text"] = uploaded.getvalue().decode("utf-8", errors="ignore")


st.file_uploader(
    "Or upload a .txt file describing the measure",
    type=["txt"],
    key="uploaded_file",
    on_change=load_uploaded_file,
)

continue_in_alternative = st.checkbox(
    "If the products are found not to be 'like', continue the analysis in the alternative",
    value=True,
)

run_clicked = st.button("Run analysis", type="primary")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
# Every analysis of the current description is kept in st.session_state["runs"],
# so the same description can be re-run with another model and the runs compared.

def run_analysis(text, chosen_model, continue_alt):
    """Run the analysis with a progress box. Returns the output, or None on error."""
    analysis = Article3_4Analysis(client, model=chosen_model)
    with st.status(f"Running analysis with {chosen_model}...", expanded=True) as status:
        try:
            output = analysis.run(text, continue_in_alternative=continue_alt,
                                  progress=lambda message: st.write(message))
        except Exception as error:  # show API errors (e.g. invalid key) to the user
            status.update(label="Analysis failed", state="error")
            st.error(f"Error: {error}")
            return None
        status.update(label=f"Analysis complete ({output['ai_calls']} AI calls)",
                      state="complete", expanded=False)
    output["measure_text"] = text
    output["continue_in_alternative"] = continue_alt
    return output


if run_clicked:
    if client is None:
        st.warning("Please enter your OpenAI API key in the sidebar and click 'Update API Key'.")
    elif not measure_text.strip():
        st.warning("Please describe a measure first.")
    else:
        new_output = run_analysis(measure_text, model, continue_in_alternative)
        if new_output:
            # A new description starts a new set of runs: clear the old review and feedback.
            for key in [k for k in st.session_state
                        if str(k).startswith(("review_", "satisfied_", "rerun_model_", "shown_run",
                                              "saved_widgets"))]:
                del st.session_state[key]
            st.session_state["runs"] = [new_output]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

BADGES = {"Yes": "🟢 Yes", "No": "🔴 No", "Uncertain": "🟡 Uncertain", "Not analysed": "⚪ Not analysed"}
# The element cards use ticks and crosses, so colour is used only for the overall outcome.
CARD_MARKS = {"Yes": "✔️ Yes", "No": "✖️ No", "Uncertain": "❓ Uncertain", "Not analysed": "– Not analysed"}
OUTCOME_SHORT = {"inconsistent": "🔴 Inconsistent", "not_established": "🔵 Not established",
                 "not_applicable": "🔵 III:4 does not apply",
                 "uncertain": "🟡 Uncertain"}
# Red = violation found, blue = violation not established, yellow = cannot decide.
# Blue (not green) because the tool does not take either party's side.
OUTCOME_BOX = {"inconsistent": st.error, "not_established": st.info, "not_applicable": st.info,
               "uncertain": st.warning}


def md(text):
    """Stop '$' signs in AI text from being read as maths formatting."""
    return str(text).replace("$", "\\$")


def remember(key, default):
    """Keep a widget's value when it is hidden (e.g. while another run is shown).

    Streamlit forgets the value of a widget that is not drawn, so the value is
    also stored in st.session_state["saved_widgets"] and restored from there.
    """
    saved = st.session_state.setdefault("saved_widgets", {})
    if key not in st.session_state:
        st.session_state[key] = saved.get(key, default)
    return key


def save(key):
    st.session_state["saved_widgets"][key] = st.session_state[key]


def run_label(index, run):
    return f"Run {index + 1} · {run['model']}"


def show_list(heading, items):
    st.markdown(f"**{heading}**")
    if items:
        st.markdown("\n".join(f"- {md(item)}" for item in items))
    else:
        st.caption("None identified")


def show_facts(heading, facts):
    st.markdown(f"**{heading}**")
    if not facts:
        st.caption("None identified")
    for fact in facts:
        icon = "✅" if fact["verified"] else "⚠️"
        quote = f"“{md(fact['quote'])}”" if fact["quote"] else "(no quote given)"
        st.markdown(f"{icon} *{quote}*  \n{md(fact['point'])}")
        if not fact["verified"]:
            st.caption("Not found word-for-word in the measure description. Please check this fact.")


def show_step(result):
    with st.expander(f"{result['title']}: {BADGES[result['conclusion']]}"):
        if result.get("rule_applied"):
            st.markdown(f"**Rule applied:** {md(result['rule_applied'])}")
        st.markdown(f"**Reasoning:** {md(result['reasoning'])}")
        if "supporting_facts" in result:
            col1, col2 = st.columns(2)
            with col1:
                show_facts("Supporting facts", result["supporting_facts"])
            with col2:
                show_facts("Contrary factors", result["contrary_factors"])
            st.caption(f"Fact check: {result['fact_check']}")
        show_list("Evidence gaps", result.get("evidence_gaps", []))

        st.markdown(f"**Authorities quoted** ({result['quote_check']}; attempts: {result['attempts']})")
        for quote in result.get("quotes", []):
            st.markdown(f"> {md(quote['text'])}\n>\n> *{quote['source']}*")
            if quote["status"] == "corrected":
                st.caption(f"Pinpoint corrected by the app. The AI cited “{quote['cited_as']}”.")
        for quote in result.get("removed_quotes", []):
            st.caption(f"Removed (not found in any authority): “{quote['text']}” [{quote['source']}]")


def show_table_of_authorities(sources):
    st.subheader("Table of authorities")
    if not sources:
        st.caption("No authorities were quoted in this analysis.")
    for source in sources:
        line = f"- **{source['short']}**: {source['citation']}"
        if source["url"]:
            line += f" ([WTO page]({source['url']}))"
        st.markdown(line)


SCOPE_NAME = "Within Article III:4 (Step 1)"


def show_human_review(index, output):
    """Let the user change element findings. The outcome is recalculated by the same rules."""
    st.markdown("#### ✏️ Change the findings yourself")
    st.caption("If you disagree with a finding, change it here. The overall outcome is recalculated "
               "by the same fixed rules. No AI call is made.")
    scope = output["results"]["scope"]
    ai_elements = output["outcome"]["elements"]
    ai_findings = {SCOPE_NAME: scope["conclusion"], **ai_elements}
    reviewed = {}
    for column, (name, answer) in zip(st.columns(len(ai_findings)), ai_findings.items()):
        options = ["Yes", "No", "Uncertain"] + (["Not analysed"] if answer == "Not analysed" else [])
        with column:
            key = remember(f"review_{index}_{name}", answer)
            reviewed[name] = st.selectbox(name, options, key=key, on_change=save, args=(key,))
    key = remember(f"review_notes_{index}", "")
    notes = st.text_area("Your notes (included in the report)", key=key, on_change=save, args=(key,))

    changed = [name for name in ai_findings if reviewed[name] != ai_findings[name]]
    if not changed and not notes.strip():
        return None
    reviewed_scope = reviewed.pop(SCOPE_NAME)
    measure_type = scope["measure_type"] if SCOPE_NAME not in changed else "as decided in human review"
    reviewed_outcome = outcome_from_elements(reviewed, reviewed_scope, measure_type)
    if changed:
        OUTCOME_BOX[reviewed_outcome["status"]](f"Outcome after review: {reviewed_outcome['label']}")
        st.caption(f"Changed in your review: {', '.join(changed)}. "
                   f"AI outcome: {output['outcome']['label']}")
    return {"scope": reviewed_scope, "elements": reviewed, "changed": changed,
            "outcome": reviewed_outcome, "notes": notes.strip()}


def ask_if_satisfied(index):
    st.subheader("Are you satisfied with this analysis?")
    key = remember(f"satisfied_{index}", None)
    return st.radio("Are you satisfied with this analysis?", ["Yes", "No"], horizontal=True,
                    key=key, on_change=save, args=(key,), label_visibility="collapsed")


def show_rerun_option(runs):
    """Offer to run the same description again with another model."""
    st.markdown("#### 🔁 Run the analysis again with another model")
    used = {run["model"] for run in runs}
    others = [m for m in st.session_state.get("available_models", []) if m not in used]
    if client is None:
        st.warning("Enter your API key in the sidebar to run the analysis again.")
        return
    if not others:
        st.info("Every available model has already been tried for this description.")
        return
    col_model, col_button = st.columns([3, 2], vertical_alignment="bottom")
    with col_model:
        other_model = st.selectbox("Model for the new run", others, key=f"rerun_model_{len(runs)}")
    with col_button:
        clicked = st.button(f"Run again with {other_model}")
    st.caption("A new run makes about the same number of AI calls again, billed to your API key. "
               "The runs can then be compared below.")
    if clicked:
        first = runs[0]
        new_output = run_analysis(first["measure_text"], other_model, first["continue_in_alternative"])
        if new_output:
            runs.append(new_output)
            st.session_state["show_run_request"] = len(runs) - 1
            st.rerun()


def show_downloads(index, output, review):
    st.subheader("Download")
    col_word, col_md, _ = st.columns([1, 1, 2])
    with col_word:
        st.download_button(
            "Download report (Word)",
            data=build_docx_report(output["measure_text"], output, review),
            file_name="article_III_4_analysis.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with col_md:
        st.download_button(
            "Download report (Markdown)",
            data=build_markdown_report(output["measure_text"], output, review),
            file_name="article_III_4_analysis.md",
            mime="text/markdown",
        )
    note = " and your review" if review else ""
    st.caption(f"The report covers the run shown above ({run_label(index, output)}){note}.")


def run_stats(run):
    results = run["results"].values()
    facts = [f for r in results for field in ("supporting_facts", "contrary_factors") for f in r.get(field, [])]
    quotes = [q for r in results for q in r.get("quotes", [])]
    removed = sum(len(r.get("removed_quotes", [])) for r in results)
    corrected = sum(q["status"] == "corrected" for q in quotes)
    return {
        "Most similar dispute": run.get("similar_cases", [{}])[0].get("short", "None") if run.get("similar_cases") else "None",
        "AI calls": str(run["ai_calls"]),
        "Facts not found in description": f"{sum(not f['verified'] for f in facts)} of {len(facts)}",
        "Quotes kept / pinpoints corrected / removed": f"{len(quotes)} / {corrected} / {removed}",
    }


def show_model_comparison(runs):
    """Compare the runs step by step. The comparison is done by code, not by the AI."""
    st.subheader("Compare models")
    st.caption("Rows marked ⚠️ are where the models reached different findings.")
    header = "| | " + " | ".join(run_label(i, r) for i, r in enumerate(runs)) + " | |"
    lines = [header, "|---" * (len(runs) + 2) + "|"]

    def row(name, values):
        flag = "⚠️ differs" if len(set(values)) > 1 else "same"
        lines.append(f"| {name} | " + " | ".join(values) + f" | {flag} |")

    row("**Outcome**", [OUTCOME_SHORT[r["outcome"]["status"]] for r in runs])
    differing_steps = []
    for key in STEP_ORDER:
        values = [BADGES[r["results"][key]["conclusion"]] if key in r["results"] else BADGES["Not analysed"]
                  for r in runs]
        title = next(r["results"][key]["title"] for r in runs if key in r["results"]) \
            if any(key in r["results"] for r in runs) else key
        row(title, values)
        if len(set(values)) > 1:
            differing_steps.append((key, title))
    stats = [run_stats(r) for r in runs]
    for name in stats[0]:
        row(name, [s[name] for s in stats])
    st.markdown("\n".join(lines))

    for key, title in differing_steps:
        with st.expander(f"Why the models differ on {title}"):
            for column, (i, run) in zip(st.columns(len(runs)), enumerate(runs)):
                with column:
                    st.markdown(f"**{run_label(i, run)}**")
                    if key in run["results"]:
                        result = run["results"][key]
                        st.markdown(f"{BADGES[result['conclusion']]}  \n{md(result['reasoning'])}")
                    else:
                        st.caption("Not analysed in this run.")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

runs = st.session_state.get("runs", [])
if runs:
    st.divider()
    st.header("Result")

    index = len(runs) - 1
    if len(runs) > 1:
        if "show_run_request" in st.session_state:
            st.session_state["shown_run"] = st.session_state.pop("show_run_request")
        index = st.radio("Show the result of", list(range(len(runs))), horizontal=True,
                         format_func=lambda i: run_label(i, runs[i]), key="shown_run")
    st.session_state.pop("show_run_request", None)
    output = runs[index]

    outcome = output["outcome"]
    OUTCOME_BOX[outcome["status"]](outcome["label"])
    if outcome["scope_warning"]:
        st.info(outcome["scope_warning"])
    if output["stopped_early"]:
        st.caption("Analysis stopped after the like products step, as selected.")
    if output.get("in_alternative"):
        st.info("Like products was not established. Steps 7 and 8 were analysed in the "
                "alternative, on the assumption that the products are like products.")

    element_columns = st.columns(len(outcome["elements"]))
    for column, (name, answer) in zip(element_columns, outcome["elements"].items()):
        with column:
            with st.container(border=True):
                st.caption(name)
                st.markdown(f"**{CARD_MARKS.get(answer, answer)}**")

    conclusion = output["conclusion"]
    st.subheader("Summary")
    st.write(md(conclusion.get("executive_summary", "")))
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            show_list("⚠️ Key uncertainties", conclusion.get("key_uncertainties", []))
    with col2:
        with st.container(border=True):
            show_list("➡️ Next steps", conclusion.get("next_steps", []))

    similar = output.get("similar_cases", [])
    if similar:
        st.subheader("Most similar WTO disputes")
        st.caption("Chosen by the AI by comparing your facts with short summaries of the disputes "
                   "in the knowledge base. Read the reports before relying on the comparison.")
        for case in similar:
            with st.container(border=True):
                title = f"**{case['short']}**"
                if case["url"]:
                    title += f" ([WTO page]({case['url']}))"
                st.markdown(title)
                st.caption(md(case["summary"]))
                st.markdown(md(case["why"]))

    st.subheader("Step-by-step analysis")
    for key in STEP_ORDER:
        if key in output["results"]:
            show_step(output["results"][key])

    show_table_of_authorities(output.get("authorities", []))
    st.caption(f"Model: {output['model']} | Temperature: {output['temperature']} | "
               f"AI calls in this run: {output['ai_calls']}")

    # Satisfied: go straight to the download. Not satisfied: review the findings,
    # or run again with another model, then download.
    satisfied = ask_if_satisfied(index)
    review = None
    if satisfied == "No":
        st.write("You can change the findings yourself, run the analysis again with another "
                 "model, or both.")
        with st.container(border=True):
            review = show_human_review(index, output)
        with st.container(border=True):
            show_rerun_option(runs)

    if len(runs) > 1:
        show_model_comparison(runs)

    if satisfied:
        show_downloads(index, output, review)
