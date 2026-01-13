# InsightForge 🔍⚙️

**InsightForge** is an AI-powered market research system that generates **structured, source-verified company reports** using up-to-date web data. It is designed to improve research reliability by grounding outputs in evidence and avoiding speculative predictions.

🔗 **Live Demo:** [https://marketai-cstey32dhwb9csmtshyhwv.streamlit.app)
🔗 **GitHub Repository:** [https://github.com/your-TEJASTATODE/MarketAI](https://github.com/your-TEJASTATODE/MarketAI)


---

## 📌 Problem Statement

AI-generated market research often lacks verifiable sources, overstates conclusions, or produces inconsistent summaries. InsightForge addresses this by enforcing **evidence-based research**, structured outputs, and clear data limitations.

---

## ✨ Key Features

* Generates structured company research reports
* Uses up-to-date web data from multiple sources
* Multi-hop research to improve factual consistency
* Clickable source links in generated PDFs
* Includes risk & limitation notes and confidence levels
* Exports reports as shareable PDF documents

---

## 🛠 Tech Stack

**Frontend / App Layer**

* Streamlit

**AI & Research**

* LangChain
* Tavily Search API
* Groq LLMs

**Backend & Storage**

* SQLite

**Reporting**

* ReportLab (PDF generation)

---

## 🧠 How InsightForge Works

1. Accepts a company name as input
2. Performs multi-hop web research using Tavily
3. Aggregates and limits content for reliability
4. Uses LangChain with structured outputs to generate reports
5. Produces a downloadable PDF with clickable sources

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* Tavily API Key
* Groq API Key

### Installation

```bash
git clone https://github.com/your-username/insightforge.git
cd insightforge
pip install -r requirements.txt
```

### Run Locally

```bash
streamlit run app.py
```

---

## 📈 Impact & Learnings

* Reduced manual market research effort by automating multi-source data collection into structured reports
* Improved factual consistency through multi-hop research and evidence-based constraints
* Learned the importance of system design, validation, and trade-offs in AI reliability

---

## ⚠️ Limitations

* Relies on publicly available web data
* Does not provide investment advice or stock predictions
* Output quality depends on source availability

