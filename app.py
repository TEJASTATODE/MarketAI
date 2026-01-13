import streamlit as st
import sqlite3
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# -------- Tavily --------
from tavily import TavilyClient

# -------- PDF --------
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4



conn = sqlite3.connect("companyDB.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT,
    pdf_path TEXT,
    created_at TEXT
)
""")
conn.commit()



llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)




class CompanyReport(BaseModel):
    company_overview: str
    recent_developments: List[str]
    earnings_summary: str
    future_plans: str
    stock_context: str
    sources: List[str]


    risks_and_limitations: str = Field(
        description="Key risks, uncertainties, and data limitations"
    )
    confidence_level: str = Field(
        description="HIGH / MEDIUM / LOW confidence with brief justification"
    )



def limit_text(text, max_chars=2500):
    if not text:
        return ""
    return str(text)[:max_chars]


def tavily_text(result: dict) -> str:
    if not result or "results" not in result:
        return ""
    return " ".join(
        item.get("content", "") for item in result["results"]
    )




analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are an evidence-based market research analyst.

Rules:
- Use ONLY the provided information
- Do NOT invent facts or numbers
- No stock predictions
- Future plans must be explicitly announced
- Be neutral and professional
"""),
    ("human", """
Company Overview:
{overview}

Recent News:
{news}

Earnings:
{earnings}

Future Plans:
{future_plans}

Stock News:
{stock_news}

Generate a structured company research report.

Also include:
- Risks & Limitations (no speculation)
- Confidence Level (HIGH / MEDIUM / LOW with reason)

Sources:
- Each source MUST be a valid https:// URL
""")
])


def generate_report(company: str) -> str:

    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    def safe_tavily(query, depth="advanced"):
        try:
            return limit_text(
                tavily_text(
                    tavily.search(query, search_depth=depth)
                )
            )
        except Exception:
            return ""

    overview = safe_tavily(f"{company} company overview", "basic")
    news = safe_tavily(f"{company} recent news")
    earnings = safe_tavily(f"{company} earnings")
    future_plans = safe_tavily(f"{company} future plans")
    stock_news = safe_tavily(f"{company} stock news")

    if not overview:
        overview = "Company overview information not available."

    messages = analysis_prompt.format_messages(
        overview=overview,
        news=news,
        earnings=earnings,
        future_plans=future_plans,
        stock_news=stock_news
    )

    structured_llm = llm.with_structured_output(CompanyReport)
    report: CompanyReport = structured_llm.invoke(messages)


    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    file_name = f"{company}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    pdf = SimpleDocTemplate(file_name, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    def section(title, content):
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
        story.append(Paragraph(content, styles["Normal"]))

    story.append(Paragraph(f"{company} Research Report", styles["Title"]))
    story.append(Paragraph(f"<i>Created on: {created_at}</i>", styles["Normal"]))

    section("Company Overview", report.company_overview)

    section("Recent Developments", "<br/>".join(f"- {i}" for i in report.recent_developments))
    section("Earnings Summary", report.earnings_summary)
    section("Future Plans", report.future_plans)
    section("Stock Context", report.stock_context)


    section("Risks & Limitations", report.risks_and_limitations)
    section("Confidence Level", report.confidence_level)

    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Sources</b>", styles["Heading2"]))
    for src in report.sources:
        story.append(Paragraph(f'<a href="{src}">{src}</a>', styles["Normal"]))

    pdf.build(story)

    return file_name




st.set_page_config(
    page_title="AI Market Research",
    layout="centered"
)

st.markdown("## 🔍⚙️InsightForge")
st.caption("Evidence-based company research powered by AI")

tab1, tab2 = st.tabs(["📄 Generate Report", "🗂 Report History"])


with tab1:
    st.markdown("### Enter Company Name")
    company = st.text_input("", placeholder="e.g. Apple, Google, NVIDIA")

    if st.button("Generate Research Report", use_container_width=True):
        if not company:
            st.error("Please enter a company name")
        else:
            with st.spinner("Collecting data and generating report..."):
                pdf_path = generate_report(company)

                cursor.execute(
                    "INSERT INTO reports (company, pdf_path, created_at) VALUES (?, ?, ?)",
                    (company, pdf_path, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()

            st.success("Report generated successfully")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    "⬇ Download PDF",
                    f,
                    file_name=pdf_path,
                    mime="application/pdf",
                    use_container_width=True
                )



with tab2:
    cursor.execute(
        "SELECT company, pdf_path, created_at FROM reports ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()

    if not rows:
        st.info("No reports generated yet")
    else:
        for company, pdf, date in rows:
            with st.container(border=True):
                st.markdown(f"**{company}**")
                st.caption(f"Generated on {date}")
                if os.path.exists(pdf):
                    with open(pdf, "rb") as f:
                        st.download_button(
                            "⬇ Download",
                            f,
                            file_name=pdf,
                            mime="application/pdf"
                        )
