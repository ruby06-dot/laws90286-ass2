"""GATT Article III:4 National Treatment Analyser (LAWS90286 Assignment 2).

Run locally with:  streamlit run home.py
"""

import hmac
from pathlib import Path

import streamlit as st

from analysis import Article3_4Analysis
from credentials import get_openai_client
from report import STEP_ORDER, build_docx_report, build_markdown_report

APP_PASSWORD = "12436"   # shared with the marker in the README
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
        "regulation rather than a tax or a border measure.\n"
        "2. **Like products.** Four separate steps for physical properties, end-uses, consumers' "
        "tastes and habits, and tariff classification, then an overall finding.\n"
        "3. **'Affecting' internal sale etc.** Is the measure a law, regulation or requirement "
        "affecting the internal sale, purchase, distribution or use of the products?\n"
        "4. **Less favourable treatment.** Does the measure modify the conditions of competition "
        "to the detriment of imported products?\n"
        "5. **Conclusion.** The outcome is decided by fixed rules: a violation is established "
        "only if all three elements are met. The AI then explains the outcome.\n\n"
        "Every quote the AI gives is checked word-for-word against the source texts by "
        "ordinary code. Quotes that fail the check are retried and then removed."
    )


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

if run_clicked:
    if client is None:
        st.warning("Please enter your OpenAI API key in the sidebar and click 'Update API Key'.")
    elif not measure_text.strip():
        st.warning("Please describe a measure first.")
    else:
        analysis = Article3_4Analysis(client)
        with st.status("Running analysis...", expanded=True) as status:
            try:
                output = analysis.run(
                    measure_text,
                    continue_in_alternative=continue_in_alternative,
                    progress=lambda message: st.write(message),
                )
                st.session_state["output"] = output
                st.session_state["analysed_text"] = measure_text
                status.update(label=f"Analysis complete ({output['ai_calls']} AI calls)",
                              state="complete", expanded=False)
            except Exception as error:  # show API errors (e.g. invalid key) to the user
                status.update(label="Analysis failed", state="error")
                st.error(f"Error: {error}")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def show_list(heading, items):
    st.markdown(f"**{heading}**")
    if items:
        st.markdown("\n".join(f"- {item}" for item in items))
    else:
        st.caption("None identified")


def show_step(result):
    badge = {"Yes": "🟢 Yes", "No": "🔴 No", "Uncertain": "🟡 Uncertain"}[result["conclusion"]]
    with st.expander(f"{result['title']}: {badge}"):
        if result.get("rule_applied"):
            st.markdown(f"**Rule applied:** {result['rule_applied']}")
        st.markdown(f"**Reasoning:** {result['reasoning']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            show_list("Supporting facts", result.get("supporting_facts", []))
        with col2:
            show_list("Contrary factors", result.get("contrary_factors", []))
        with col3:
            show_list("Evidence gaps", result.get("evidence_gaps", []))
        st.markdown(f"**Quote check:** {result['quote_check']} (attempts: {result['attempts']})")
        for quote in result.get("quotes", []):
            st.markdown(f"> {quote}")
        for quote in result.get("removed_quotes", []):
            st.caption(f"Removed (not found in sources): {quote}")


output = st.session_state.get("output")
if output:
    st.divider()
    st.header("Result")

    outcome = output["outcome"]
    box = {"inconsistent": st.error, "not_established": st.success, "uncertain": st.warning}
    box[outcome["status"]](outcome["label"])
    if outcome["scope_warning"]:
        st.info(outcome["scope_warning"])
    if output["stopped_early"]:
        st.caption("Analysis stopped after the like products step, as selected.")
    if output.get("in_alternative"):
        st.info("Like products was not established. Steps 7 and 8 were analysed in the "
                "alternative, on the assumption that the products are like products.")

    badges = {"Yes": "🟢 Yes", "No": "🔴 No", "Uncertain": "🟡 Uncertain", "Not analysed": "⚪ Not analysed"}
    element_columns = st.columns(len(outcome["elements"]))
    for column, (name, answer) in zip(element_columns, outcome["elements"].items()):
        with column:
            with st.container(border=True):
                st.caption(name)
                st.markdown(f"**{badges.get(answer, answer)}**")

    conclusion = output["conclusion"]
    st.subheader("Summary")
    st.write(conclusion.get("executive_summary", ""))
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            show_list("⚠️ Key uncertainties", conclusion.get("key_uncertainties", []))
    with col2:
        with st.container(border=True):
            show_list("➡️ Next steps", conclusion.get("next_steps", []))

    st.subheader("Step-by-step analysis")
    for key in STEP_ORDER:
        if key in output["results"]:
            show_step(output["results"][key])

    st.caption(f"Model: {output['model']} | Temperature: {output['temperature']} | "
               f"AI calls in this run: {output['ai_calls']}")

    col_word, col_md, _ = st.columns([1, 1, 2])
    with col_word:
        st.download_button(
            "Download report (Word)",
            data=build_docx_report(st.session_state["analysed_text"], output),
            file_name="article_III_4_analysis.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with col_md:
        st.download_button(
            "Download report (Markdown)",
            data=build_markdown_report(st.session_state["analysed_text"], output),
            file_name="article_III_4_analysis.md",
            mime="text/markdown",
        )