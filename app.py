import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px
import gspread

from oauth2client.service_account import ServiceAccountCredentials

# -----------------------------
# GOOGLE SHEETS CONNECTION
# -----------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    dict(st.secrets),
    scope
)

client_sheet = gspread.authorize(credentials)

sheet = client_sheet.open_by_url(
    "https://docs.google.com/spreadsheets/d/1TVOrf9WTaIXKsobNIyM_9wmVMN_xgiAj7vwAEttxtwU/edit?gid=0#gid=0"
).sheet1

# -----------------------------
# STREAMLIT PAGE
# -----------------------------

st.set_page_config(
    page_title="AI Recruiter Dashboard",
    layout="wide"
)

st.title("AI Recruiter Dashboard")

# -----------------------------
# SKILLS DATABASE
# -----------------------------

skills_database = [
    "Python",
    "SQL",
    "Machine Learning",
    "Deep Learning",
    "NLP",
    "Pandas",
    "NumPy",
    "Scikit-learn",
    "TensorFlow",
    "PyTorch",
    "Streamlit",
    "Power BI",
    "Tableau",
    "Excel",
    "LangChain",
    "RAG",
    "OpenAI",
    "Claude",
    "Generative AI",
    "Data Science",
    "Statistics"
]

# -----------------------------
# FILE UPLOAD
# -----------------------------

uploaded_files = st.file_uploader(
    "Upload Multiple Resume PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

all_candidates = []

# -----------------------------
# PROCESS FILES
# -----------------------------

if uploaded_files:

    for uploaded_file in uploaded_files:

        resume_text = ""

        with pdfplumber.open(uploaded_file) as pdf:

            for page in pdf.pages:

                extracted = page.extract_text()

                if extracted:
                    resume_text += extracted

        # -----------------------------
        # SKILL EXTRACTION
        # -----------------------------

        found_skills = []

        for skill in skills_database:

            if re.search(
                r"\b" + re.escape(skill) + r"\b",
                resume_text,
                re.IGNORECASE
            ):
                found_skills.append(skill)

        # -----------------------------
        # ATS SCORE
        # -----------------------------

        ats_score = round(
            (len(found_skills) / len(skills_database)) * 100,
            2
        )

        # -----------------------------
        # CATEGORY PREDICTION
        # -----------------------------

        ai_keywords = [
            "Python",
            "Machine Learning",
            "NLP",
            "RAG",
            "LangChain",
            "Generative AI"
        ]

        data_keywords = [
            "SQL",
            "Excel",
            "Power BI",
            "Statistics"
        ]

        ai_count = sum(
            skill in ai_keywords
            for skill in found_skills
        )

        data_count = sum(
            skill in data_keywords
            for skill in found_skills
        )

        if ai_count >= data_count:
            category = "AI/ML Candidate"
        else:
            category = "Data Analyst Candidate"

        # -----------------------------
        # STORE IN PYTHON LIST
        # -----------------------------

        all_candidates.append({
            "Resume": uploaded_file.name,
            "Skills": ", ".join(found_skills),
            "ATS Score": ats_score,
            "Category": category
        })

        # -----------------------------
        # SAVE TO GOOGLE SHEETS
        # -----------------------------

        sheet.append_row([
            uploaded_file.name,
            ats_score,
            category,
            ", ".join(found_skills),
            uploaded_file.name
        ])

    # -----------------------------
    # CREATE DATAFRAME
    # -----------------------------

    df = pd.DataFrame(all_candidates)

    # -----------------------------
    # SHOW TABLE
    # -----------------------------

    st.subheader("Candidate Analysis")

    st.dataframe(df)

    # -----------------------------
    # TOP CANDIDATES
    # -----------------------------

    top_df = df.sort_values(
        by="ATS Score",
        ascending=False
    )

    st.subheader("Top Candidates")

    st.dataframe(top_df)

    # -----------------------------
    # CHART
    # -----------------------------

    st.subheader("ATS Score Chart")

    fig = px.bar(
        top_df,
        x="Resume",
        y="ATS Score",
        color="Category"
    )

    st.plotly_chart(fig)

    # -----------------------------
    # EXCEL EXPORT
    # -----------------------------

    excel_file = "candidate_analysis.xlsx"

    df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as file:

        st.download_button(
            label="Download Excel Report",
            data=file,
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
