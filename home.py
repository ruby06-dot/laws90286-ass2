"""GATT Article III:4 National Treatment Analyser (LAWS90286 Assignment 2).

Run locally with:  streamlit run home.py
"""

import hmac
import time
from html import escape
from pathlib import Path

import streamlit as st

from analysis import Article3_4Analysis
from authorities import load_library
from credentials import get_openai_client, select_model
from report import (STEP_ORDER, build_docx_report, build_markdown_report, comparison_rows,
                    run_label)

APP_PASSWORD = "12436"   # repository is private; move to Streamlit secrets before making it public
APP_TITLE = "National Treatment Analyser"
APP_SUBTITLE = "Step-by-step analysis under GATT 1994 Article III:4"
TEST_CASE_DIR = Path(__file__).parent / "test_cases"            # the 3 official test cases
EXTRA_CASE_DIR = Path(__file__).parent / "additional_cases"     # optional extra cases
TAB_OVERVIEW, TAB_STEPS, TAB_REVIEW = "📋 Overview", "🔍 Step-by-step", "✏️ Revise & re-run"

st.set_page_config(page_title=APP_TITLE, page_icon="⚖️", layout="wide")

# ---------------------------------------------------------------------------
# Styles (header banner, verdict card, step flow diagram)
# ---------------------------------------------------------------------------

st.markdown("""
<style>
.nt-banner {background: #F4F7FB; border: 1px solid #DCE4EE; border-left: 6px solid #1F3A5F;
  padding: 0.9rem 1.3rem 0.75rem; border-radius: 12px; margin: 0 0 1rem;}
.nt-banner .nt-title {font-size: 1.6rem; font-weight: 700; line-height: 1.2; color: #1F3A5F;}
.nt-banner .nt-sub {color: #5A6675; font-size: 0.95rem; margin: 0.2rem 0 0.55rem;}
.nt-chip {display: inline-block; background: #FFFFFF; border: 1px solid #C9D4E2; border-radius: 999px;
  padding: 0.08rem 0.6rem; margin: 0.15rem 0.3rem 0.15rem 0; font-size: 0.78rem; color: #1F3A5F;
  white-space: nowrap;}
.nt-login {text-align: center; border-left: 1px solid #DCE4EE; border-top: 5px solid #1F3A5F;}
.nt-login .nt-title {font-size: 1.7rem;}
.nt-elements {display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.2rem 0 0.4rem;}
.nt-el {border: 1px solid #D9E0E8; border-radius: 8px; padding: 0.3rem 0.7rem; font-size: 0.88rem;
  background: #FAFBFD;}
.nt-el b {margin-left: 0.35rem;}
.nt-stats {font-size: 0.78rem; color: #7A8594; margin: 0.1rem 0 1rem;}
.nt-stats span {margin-right: 1.1rem; white-space: nowrap;}
.nt-verdict {border-radius: 14px; padding: 1.1rem 1.4rem; margin: 0.4rem 0 1rem;
  border-left: 8px solid var(--nt-c); background: var(--nt-bg);}
.nt-verdict .nt-v-title {font-size: 1.45rem; font-weight: 700; color: var(--nt-c);}
.nt-verdict .nt-v-text {margin-top: 0.3rem; color: #333;}
.nt-flow {display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin: 0.6rem 0 0.2rem;}
.nt-node {display: flex; flex-direction: column; align-items: center; min-width: 74px;}
.nt-dot {width: 40px; height: 40px; border-radius: 50%; color: #FFFFFF; font-weight: 700;
  display: flex; align-items: center; justify-content: center; font-size: 1rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);}
.nt-lbl {font-size: 0.78rem; margin-top: 0.3rem; text-align: center; line-height: 1.15;}
.nt-arrow {color: #9AA5B1; font-size: 1.2rem; margin-bottom: 1.1rem;}
.nt-group {border: 1.5px dashed #9AA5B1; border-radius: 12px; padding: 0.35rem 0.4rem 0.2rem;}
.nt-group-title {font-size: 0.72rem; color: #6B7785; text-align: center; margin-bottom: 0.2rem;}
.nt-group-row {display: flex; gap: 0.2rem;}
.nt-outcome {border-radius: 999px; padding: 0.45rem 1rem; color: #FFFFFF; font-weight: 700;
  font-size: 0.9rem; margin-bottom: 1.1rem;}
.nt-legend {font-size: 0.78rem; color: #6B7785; margin-bottom: 0.6rem;}
.nt-legend span {display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  margin: 0 0.25rem 0 0.7rem; vertical-align: middle;}
</style>
""", unsafe_allow_html=True)


def banner(chips=True, login=False):
    """The navy header banner shown on the login page and the main page."""
    chip_html = ""
    if chips:
        chip_html = "<div>" + "".join(f"<span class='nt-chip'>{c}</span>" for c in [
            "⚖️ GATT 1994 Art III:4", "🧭 9 guided steps", "🧮 Outcome decided by fixed rules",
            "🔎 Quotes and facts checked by code", "✏️ Human review", "🔁 Model comparison",
        ]) + "</div>"
    extra = " nt-login" if login else ""
    st.markdown(f"<div class='nt-banner{extra}'><div class='nt-title'>⚖️ {APP_TITLE}</div>"
                f"<div class='nt-sub'>{APP_SUBTITLE}</div>{chip_html}</div>", unsafe_allow_html=True)


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
        banner(chips=False, login=True)
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

banner()
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
        "- Every quote must appear word-for-word in the provision it cites. The knowledge base "
        "currently holds the text of GATT Article III:1, III:4 and the Note Ad Article III. A "
        "quote found in a different provision has its pinpoint corrected; a quote found nowhere "
        "is removed.\n"
        "- Every fact the AI relies on must appear word-for-word in your description. Facts that "
        "fail are marked ⚠️ for you to check.\n\n"
        "Failed checks are first sent back to the AI for another attempt.\n\n"
        "The WTO case law behind each legal test is summarised in the tool's instructions to the "
        "AI. The reports themselves are not stored, so the AI cannot quote them; the most similar "
        "disputes are linked to their WTO pages so that you can read the reports."
    )

# Warn about formatting problems in the knowledge files (shown only if there are any).
for source in load_library():
    for problem in source["problems"]:
        st.warning(f"knowledge file {source['id']}.txt: {problem}")


def case_files():
    """Dropdown label -> file. Official test cases first, then the extra ones marked (extra)."""
    files = {}
    for folder, prefix in [(TEST_CASE_DIR, ""), (EXTRA_CASE_DIR, "(extra) ")]:
        if folder.exists():
            for path in sorted(folder.glob("*.txt")):
                files[prefix + path.name] = path
    return files


CASE_FILES = case_files()


def load_test_case():
    name = st.session_state.get("selected_case")
    if name in CASE_FILES:
        st.session_state["measure_text"] = CASE_FILES[name].read_text(encoding="utf-8")


if CASE_FILES:
    col_a, col_b = st.columns([5, 1], vertical_alignment="bottom")
    with col_a:
        st.selectbox("Load a test case (optional)", list(CASE_FILES), key="selected_case")
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
    started = time.perf_counter()
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
    output["seconds"] = round(time.perf_counter() - started)
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
                        if str(k).startswith(("revise_", "notes_", "satisfied_", "shown_run",
                                              "saved_widgets"))]:
                del st.session_state[key]
            st.session_state["runs"] = [new_output]
            st.session_state["tab_request"] = TAB_OVERVIEW


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

BADGES = {"Yes": "🟢 Yes", "No": "🔴 No", "Uncertain": "🟡 Uncertain", "Not analysed": "⚪ Not analysed"}
OUTCOME_SHORT = {"inconsistent": "🔴 Inconsistent", "not_established": "🔵 Not established",
                 "not_applicable": "🔵 III:4 does not apply",
                 "uncertain": "🟡 Uncertain"}


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


def ask_if_satisfied(index):
    st.subheader("Are you satisfied with this analysis?")
    key = remember(f"satisfied_{index}", None)
    return st.radio("Are you satisfied with this analysis?", ["Yes", "No"], horizontal=True,
                    key=key, on_change=satisfied_changed, args=(key,), label_visibility="collapsed")


def show_revise_and_rerun(index, output, runs):
    """Let the user correct or add to the facts, choose a model, and run the analysis again."""
    st.markdown("#### ✏️ Revise the facts and run again")
    st.caption("Correct or add to the facts, or point out what the analysis should take into account. "
               "Then choose a model and run the analysis again. The new run is kept next to the "
               "earlier ones so that you can compare them.")
    key_text = remember(f"revise_text_{index}", output.get("base_text", output["measure_text"]))
    new_text = st.text_area("Measure description (edit as needed)", key=key_text, height=200,
                            on_change=save, args=(key_text,))
    key_clar = remember(f"revise_clar_{index}", "")
    clarification = st.text_area(
        "Points to emphasise or clarify (optional)", key=key_clar, height=90, on_change=save,
        args=(key_clar,),
        placeholder="For example: construction firms, not households, are the main buyers of these products.")
    st.caption("These points are added to the description as additional facts, so every fact the AI "
               "relies on is still checked against your text.")

    if client is None:
        st.warning("Enter your API key in the sidebar to run the analysis again.")
        return
    models = st.session_state.get("available_models") or [output["model"]]
    if output["model"] not in models:
        models = [output["model"]] + models
    col_model, col_button = st.columns([3, 2], vertical_alignment="bottom")
    with col_model:
        key_model = remember(f"revise_model_{index}", output["model"])
        chosen = st.selectbox("Model for the new run", models, key=key_model, on_change=save,
                              args=(key_model,))
    with col_button:
        clicked = st.button("🔁 Run the analysis again", type="primary", key=f"revise_run_{index}")
    st.caption("A new run makes about the same number of AI calls again, billed to your API key.")

    if not clicked:
        return
    if not new_text.strip():
        st.warning("The measure description is empty.")
        return
    text = new_text.strip()
    if clarification.strip():
        text += "\n\nAdditional facts and clarifications from the user:\n" + clarification.strip()
    if text == output["measure_text"].strip() and chosen == output["model"]:
        st.info("Nothing has changed. The same facts and the same model give almost the same result. "
                "Edit the facts, add a point to emphasise, or choose another model.")
        return
    new_output = run_analysis(text, chosen, runs[0]["continue_in_alternative"])
    if new_output:
        new_output["base_text"] = new_text.strip()
        new_output["clarification"] = clarification.strip()
        new_output["revised"] = text != runs[0]["measure_text"].strip()
        runs.append(new_output)
        st.session_state["show_run_request"] = len(runs) - 1
        st.session_state["tab_request"] = TAB_OVERVIEW
        st.rerun()


def show_notes(index):
    key = remember(f"notes_{index}", "")
    notes = st.text_area("📝 Your notes (optional, added to the report)", key=key, height=90,
                         on_change=save, args=(key,),
                         placeholder="Your own comments on this analysis.")
    # A text box only saves its text when the user presses Ctrl+Enter or clicks outside it.
    # The download button is prepared before that, so show clearly whether the notes are saved.
    if notes.strip():
        st.markdown("<span style='color:#2E7D32; font-size:0.85rem;'>✓ Notes saved. They are "
                    "included in the report below.</span>", unsafe_allow_html=True)
    else:
        st.caption("After typing, press **Ctrl+Enter** (Mac: **⌘+Enter**) or click outside the box "
                   "to save your notes, then download.")
    return {"notes": notes.strip()} if notes.strip() else None


def show_downloads(index, output, review, where, runs):
    """The single download box, in the Overview tab of the run being viewed."""
    with st.container(border=True):
        st.markdown("#### 📥 Download the report")
        parts = ["the outcome", "every step", "the facts and quotes with their check results",
                 "the table of authorities"]
        if len(runs) > 1:
            parts.append("a comparison with the other run" if len(runs) == 2
                         else f"a comparison of all {len(runs)} runs of this description")
        if review:
            parts.append("your notes")
        st.caption(f"The report covers {run_label(index, output)}: " + ", ".join(parts[:-1])
                   + f" and {parts[-1]}.")
        col_word, col_md, _ = st.columns([1, 1, 1])
        with col_word:
            st.download_button(
                "⬇️ Word report (.docx)", type="primary", use_container_width=True,
                data=build_docx_report(output["measure_text"], output, review, runs),
                file_name="article_III_4_analysis.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"docx_{where}_{index}",
            )
        with col_md:
            st.download_button(
                "⬇️ Markdown report (.md)", use_container_width=True,
                data=build_markdown_report(output["measure_text"], output, review, runs),
                file_name="article_III_4_analysis.md", mime="text/markdown",
                key=f"md_{where}_{index}",
            )


def show_comparison(runs, index):
    """Compare all runs of this description. The comparison is done by code, not by the AI."""
    st.subheader("⚖️ Comparison of runs")
    st.caption(f"You are viewing {run_label(index, runs[index])}. Rows marked ⚠️ are where the runs "
               "reached different findings. The last rows are statistics and are not compared.")
    rows = comparison_rows(runs)
    lines = ["| | " + " | ".join(run_label(i, r) for i, r in enumerate(runs)) + " | |",
             "|---" * (len(runs) + 2) + "|"]
    for row in rows:
        if row["kind"] == "outcome":
            values = [OUTCOME_SHORT[v] for v in row["values"]]
        elif row["kind"] == "step":
            values = [BADGES[v] for v in row["values"]]
        else:
            values = row["values"]
        flag = "" if row["differs"] is None else ("⚠️ differs" if row["differs"] else "same")
        name = f"**{row['name']}**" if row["kind"] == "outcome" else row["name"]
        lines.append(f"| {name} | " + " | ".join(values) + f" | {flag} |")
    st.markdown("\n".join(lines))

    for row in rows:
        if row["kind"] != "step" or not row["differs"]:
            continue
        with st.expander(f"Why the runs differ on {row['name']}"):
            for column, (i, run) in zip(st.columns(len(runs)), enumerate(runs)):
                with column:
                    st.markdown(f"**{run_label(i, run)}**")
                    if row["key"] in run["results"]:
                        result = run["results"][row["key"]]
                        st.markdown(f"{BADGES[result['conclusion']]}  \n{md(result['reasoning'])}")
                    else:
                        st.caption("Not analysed in this run.")


FINDING_COLOURS = {"Yes": "#2E7D32", "No": "#C62828", "Uncertain": "#E0A100", "Not analysed": "#9AA5B1"}
# Red = violation found, blue = no violation / not applicable, yellow = cannot decide.
# Blue (not green) because the tool does not take either party's side.
OUTCOME_STYLE = {   # title, main colour, background
    "inconsistent": ("Inconsistent with Article III:4", "#C62828", "#FDECEC"),
    "not_established": ("Violation of Article III:4 not established", "#1565C0", "#E8F0FB"),
    "not_applicable": ("Article III:4 does not apply", "#1565C0", "#E8F0FB"),
    "uncertain": ("Uncertain", "#B7791F", "#FFF6E0"),
}
FLOW_LABELS = {"scope": "Scope", "physical_properties": "Physical", "end_uses": "End-uses",
               "consumers": "Consumers", "tariff": "Tariff", "likeness": "Like products",
               "affecting": "Affecting", "lft": "Less favourable"}


def show_verdict(outcome):
    title, colour, background = OUTCOME_STYLE[outcome["status"]]
    st.markdown(f"<div class='nt-verdict' style='--nt-c: {colour}; --nt-bg: {background};'>"
                f"<div class='nt-v-title'>{escape(title)}</div>"
                f"<div class='nt-v-text'>{escape(outcome['label'])}</div></div>", unsafe_allow_html=True)


def show_step_flow(output):
    """A pipeline diagram of the steps, each coloured by its finding."""
    results = output["results"]

    def node(key, number):
        answer = results[key]["conclusion"] if key in results else "Not analysed"
        return (f"<div class='nt-node' title='{escape(FLOW_LABELS[key])}: {answer}'>"
                f"<div class='nt-dot' style='background: {FINDING_COLOURS[answer]};'>{number}</div>"
                f"<div class='nt-lbl'>{FLOW_LABELS[key]}<br>{answer}</div></div>")

    arrow = "<div class='nt-arrow'>➜</div>"
    criteria = "".join(node(key, n) for n, key in
                       enumerate(["physical_properties", "end_uses", "consumers", "tariff"], start=2))
    _, colour, _ = OUTCOME_STYLE[output["outcome"]["status"]]
    title = OUTCOME_STYLE[output["outcome"]["status"]][0]
    parts = [node("scope", 1), arrow,
             f"<div class='nt-group'><div class='nt-group-title'>Like products criteria</div>"
             f"<div class='nt-group-row'>{criteria}</div></div>", arrow,
             node("likeness", 6), arrow, node("affecting", 7), arrow, node("lft", 8), arrow,
             f"<div class='nt-outcome' style='background: {colour};'>{escape(title)}</div>"]
    legend = "".join(f"<span style='background: {c};'></span>{a}" for a, c in FINDING_COLOURS.items())
    st.markdown(f"<div class='nt-flow'>{''.join(parts)}</div>"
                f"<div class='nt-legend'>{legend}</div>", unsafe_allow_html=True)


def show_elements_and_stats(output):
    """Compact element findings, then a small grey line of run statistics."""
    marks = {"Yes": "✔ Yes", "No": "✖ No", "Uncertain": "? Uncertain", "Not analysed": "– Not analysed"}
    boxes = "".join(f"<div class='nt-el'>{escape(name)}<b>{marks.get(answer, answer)}</b></div>"
                    for name, answer in output["outcome"]["elements"].items())
    results = output["results"].values()
    facts = [f for r in results for field in ("supporting_facts", "contrary_factors") for f in r.get(field, [])]
    quotes = [q for r in results for q in r.get("quotes", [])]
    seconds = output.get("seconds")
    stats = [f"Model {escape(output['model'])}", f"AI calls {output['ai_calls']}",
             f"Facts found in your text {sum(f['verified'] for f in facts)}/{len(facts)}",
             f"Quotes verified {len(quotes)}"]
    if seconds is not None:
        stats.append(f"Time {seconds} s")
    st.markdown(f"<div class='nt-elements'>{boxes}</div><div class='nt-stats'>"
                + "".join(f"<span>{x}</span>" for x in stats) + "</div>", unsafe_allow_html=True)


def go_to_tab(name):
    """Button callback: switch the result tab and scroll back up to the tabs."""
    st.session_state["result_tab"] = name
    st.session_state["scroll_to_tabs"] = True


def satisfied_changed(key):
    save(key)
    if st.session_state[key] == "No":
        go_to_tab(TAB_REVIEW)


def scroll_to_tabs_if_needed():
    """After a jump button is used, scroll the page back up to the tabs."""
    if not st.session_state.pop("scroll_to_tabs", False):
        return
    script = ("<script>const t = window.parent.document.querySelector('[data-baseweb=\"tab-list\"]');"
              "if (t) {t.scrollIntoView({behavior: 'smooth', block: 'start'});}</script>")
    if hasattr(st, "iframe"):          # newer Streamlit
        st.iframe(script, height=1)
    else:                              # older Streamlit
        import streamlit.components.v1 as components
        components.html(script, height=0)


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
    tab_names = [TAB_OVERVIEW, TAB_STEPS, TAB_REVIEW]
    if "tab_request" in st.session_state:          # e.g. open Overview after a new run
        st.session_state["result_tab"] = st.session_state.pop("tab_request")
    if st.session_state.get("result_tab") not in tab_names:
        st.session_state["result_tab"] = tab_names[0]
    try:
        # Remember the selected tab when a button or box inside it is used.
        tabs = st.tabs(tab_names, key="result_tab", on_change="rerun")
    except TypeError:   # older Streamlit without stateful tabs
        tabs = st.tabs(tab_names)
    scroll_to_tabs_if_needed()

    # --- Overview -----------------------------------------------------------
    with tabs[0]:
        show_verdict(outcome)
        if output.get("revised"):
            with st.expander("ℹ️ This run used revised facts. Show the facts used"):
                st.text(output["measure_text"])
        if outcome["scope_warning"]:
            st.info(outcome["scope_warning"])
        if output["stopped_early"]:
            st.caption("Analysis stopped after the like products step, as selected.")
        if output.get("in_alternative"):
            st.info("Like products was not established. Steps 7 and 8 were analysed in the "
                    "alternative, on the assumption that the products are like products.")

        show_step_flow(output)

        show_elements_and_stats(output)

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
        if len(runs) > 1:
            st.divider()
            show_comparison(runs, index)

        st.divider()
        # Notes and download first, then ask for feedback. Satisfied: offer the reasoning.
        # Not satisfied: the Revise & re-run tab opens automatically.
        notes = show_notes(index)
        show_downloads(index, output, notes, "overview", runs)
        satisfied = ask_if_satisfied(index)
        if satisfied == "Yes":
            st.success("Thank you. If you would like to see how the tool reached this result:")
            col_a, col_b, _ = st.columns([1, 1, 1])
            with col_a:
                st.button("🔍 Read the step-by-step reasoning", on_click=go_to_tab, args=(TAB_STEPS,),
                          use_container_width=True, key=f"jump_steps_{index}")
            with col_b:
                st.button("📚 See the authorities quoted", on_click=go_to_tab, args=(TAB_STEPS,),
                          use_container_width=True, key=f"jump_auth_{index}")
        elif satisfied == "No":
            st.info("The **Revise & re-run** tab has opened: correct or add to the facts, choose a "
                    "model and run the analysis again. The new result, a comparison with this run "
                    "and the download will then appear here in the Overview tab.")
            st.button("✏️ Go to Revise & re-run", on_click=go_to_tab, args=(TAB_REVIEW,),
                      key=f"jump_review_{index}")

    # --- Step-by-step -------------------------------------------------------
    with tabs[1]:
        for key in STEP_ORDER:
            if key in output["results"]:
                show_step(output["results"][key])
        show_table_of_authorities(output.get("authorities", []))
        st.caption(f"Model: {output['model']} | Temperature: {output['temperature']} | "
                   f"AI calls in this run: {output['ai_calls']}")

    # --- Revise & re-run ---------------------------------------------------
    with tabs[2]:
        with st.container(border=True):
            show_revise_and_rerun(index, output, runs)
        st.caption("After the new run, its result, a comparison with the earlier run(s), your notes "
                   "and the download appear in the **Overview** tab.")
