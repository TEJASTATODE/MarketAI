import streamlit as st
import sqlite3
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv
load_dotenv()

# -------- LangChain / LLM --------
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

# -------- Tavily --------
from tavily import TavilyClient

# -------- PDF --------
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


# =============================
# DATABASE SETUP
# =============================

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


# =============================
# LLM SETUP
# =============================

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)


# =============================
# STRUCTURED OUTPUT MODEL
# =============================

class CompanyReport(BaseModel):
    company_overview: str = Field(description="What the company does today")
    recent_developments: List[str] = Field(description="Recent developments only")
    earnings_summary: str = Field(description="Recent earnings if available")
    future_plans: str = Field(description="Explicitly announced future plans only")
    stock_context: str = Field(description="Stock-related context without prediction")
    sources: List[str] = Field(description="Sources used")


# =============================
# UTILS
# =============================

def limit_text(text, max_chars=2500):
    if not text:
        return ""
    return str(text)[:max_chars]


def tavily_text(result: dict) -> str:
    """Extract only useful content from Tavily response"""
    if not result or "results" not in result:
        return ""
    return " ".join(
        item.get("content", "") for item in result["results"]
    )


# =============================
# PROMPT
# =============================

analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are an evidence-based market research analyst.

Rules:
- Use ONLY the provided information
- Do NOT invent facts or numbers
- No stock predictions
- Future plans must be explicitly announced
- If information is missing, say so clearly
- Keep a neutral, professional tone
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
Include a list of sources used.
""")
])


# =============================
# REPORT GENERATION
# =============================

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
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{company}_{timestamp}.pdf"

    pdf = SimpleDocTemplate(file_name, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"{company} Research Report", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<i>Created on: {created_at}</i>", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Company Overview</b>", styles["Heading2"]))
    story.append(Paragraph(report.company_overview, styles["Normal"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Recent Developments</b>", styles["Heading2"]))
    for item in report.recent_developments:
        story.append(Paragraph(f"- {item}", styles["Normal"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Earnings Summary</b>", styles["Heading2"]))
    story.append(Paragraph(report.earnings_summary, styles["Normal"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Future Plans</b>", styles["Heading2"]))
    story.append(Paragraph(report.future_plans, styles["Normal"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Stock Context</b>", styles["Heading2"]))
    story.append(Paragraph(report.stock_context, styles["Normal"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Sources</b>", styles["Heading2"]))
    for src in report.sources:
        story.append(Paragraph(f"- {src}", styles["Normal"]))

    pdf.build(story)

    return file_name


# =============================
# STREAMLIT UI
# =============================

st.set_page_config(page_title="AI Market Research", layout="wide")
st.title("AI Market Research System")

tab1, tab2 = st.tabs(["Generate Report", "Report History"])

with tab1:
    company = st.text_input("Company Name")

    if st.button("Generate Report"):
        if not company:
            st.error("Please enter a company name")
        else:
            st.info("Collecting data and generating report...")

            pdf_path = generate_report(company)

            cursor.execute(
                "INSERT INTO reports (company, pdf_path, created_at) VALUES (?, ?, ?)",
                (company, pdf_path, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()

            st.success("Report generated successfully")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download PDF",
                    f,
                    file_name=pdf_path,
                    mime="application/pdf"
                )


with tab2:
    cursor.execute(
        "SELECT company, pdf_path, created_at FROM reports ORDER BY created_at DESC"
    )
    rows = cursor.fetchall()

    if not rows:
        st.warning("No reports generated yet")
    else:
        for company, pdf, date in rows:
            st.write(f"**{company}** — {date}")
            if os.path.exists(pdf):
                with open(pdf, "rb") as f:
                    st.download_button(
                        f"Download {company}",
                        f,
                        file_name=pdf,
                        mime="application/pdf"
                    )
