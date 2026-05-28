import streamlit as st
import pdfplumber
import pandas as pd
import re
import plotly.express as px
import gspread
import json

from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import quote
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="AI Recruiter Dashboard", layout="wide")
st.title("AI Recruiter Dashboard with RAG Resume Chatbot")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1TVOrf9WTaIXKsobNIyM_9wmVMN_xgiAj7vwAEttxtwU/edit?gid=0#gid=0"

def connect_google_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(st.secrets["gcp_service_account"]["json"]),
            scope
        )

        client_sheet = gspread.authorize(credentials)
        return client_sheet.open_by_url(SHEET_URL).sheet1

    except Exception:
        return None

sheet = connect_google_sheet()

skills_database = [
    "Python", "SQL", "Machine Learning", "Deep Learning", "NLP",
    "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch",
    "Streamlit", "Power BI", "Tableau", "Excel", "LangChain",
    "RAG", "OpenAI", "Claude", "Generative AI", "Data Science",
    "Statistics"
]

def rag_resume_chatbot(question, resume_text):
    chunks = re.split(r"\n|\.", resume_text)
    chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 30]

    if not chunks:
        return "No useful resume content found."

    vectorizer = TfidfVectorizer(stop_words="english")
    vectors = vectorizer.fit_transform(chunks + [question])

    similarities = cosine_similarity(vectors[-1], vectors[:-1]).flatten()
    best_index = similarities.argmax()

    return chunks[best_index]

uploaded_files = st.file_uploader(
    "Upload Multiple Resume PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

all_candidates = []
resume_texts = {}

if uploaded_files:

    for uploaded_file in uploaded_files:
        resume_text = ""

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    resume_text += extracted + "\n"

        resume_texts[uploaded_file.name] = resume_text

        found_skills = []

        for skill in skills_database:
            if re.search(r"\b" + re.escape(skill) + r"\b", resume_text, re.IGNORECASE):
                found_skills.append(skill)

        ats_score = round((len(found_skills) / len(skills_database)) * 100, 2)

        ai_keywords = ["Python", "Machine Learning", "NLP", "RAG", "LangChain", "Generative AI"]
        data_keywords = ["SQL", "Excel", "Power BI", "Statistics"]

        ai_count = sum(skill in ai_keywords for skill in found_skills)
        data_count = sum(skill in data_keywords for skill in found_skills)

        category = "AI/ML Candidate" if ai_count >= data_count else "Data Analyst Candidate"

        all_candidates.append({
            "Resume": uploaded_file.name,
            "Skills": ", ".join(found_skills),
            "ATS Score": ats_score,
            "Category": category
        })

        if sheet:
            sheet.append_row([
                uploaded_file.name,
                ats_score,
                category,
                ", ".join(found_skills),
                uploaded_file.name
            ])

    df = pd.DataFrame(all_candidates)

    st.subheader("Candidate Analysis")
    st.dataframe(df)

    top_df = df.sort_values(by="ATS Score", ascending=False)

    st.subheader("Top Candidates")
    st.dataframe(top_df)

    st.subheader("ATS Score Chart")

    fig = px.bar(top_df, x="Resume", y="ATS Score", color="Category")
    st.plotly_chart(fig)

    excel_file = "candidate_analysis.xlsx"
    df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as file:
        st.download_button(
            label="Download Excel Report",
            data=file,
            file_name=excel_file,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.subheader("RAG Resume Chatbot")

    selected_resume_for_chat = st.selectbox(
        "Select Resume for Chatbot",
        df["Resume"]
    )

    question = st.text_input(
        "Ask question about selected resume",
        placeholder="Example: What AI/ML projects has this candidate done?"
    )

    if st.button("Ask Chatbot"):
        selected_resume_text = resume_texts[selected_resume_for_chat]
        answer = rag_resume_chatbot(question, selected_resume_text)

        st.write("Answer from resume:")
        st.success(answer)

    st.subheader("Recruiter Email Automation")

    selected_candidate = st.selectbox(
        "Select Candidate for Email",
        df["Resume"]
    )

    candidate_row = df[df["Resume"] == selected_candidate].iloc[0]

    email_type = st.selectbox(
        "Select Email Type",
        ["Shortlisted", "Interview Invitation", "Rejected"]
    )

    email_subject = f"{email_type} - {candidate_row['Resume']}"

    email_body = f"""
Dear Candidate,

This is an update regarding your resume application.

Status: {email_type}
Category: {candidate_row['Category']}
ATS Score: {candidate_row['ATS Score']}
Detected Skills: {candidate_row['Skills']}

Regards,
Recruitment Team
"""

    st.text_input("Email Subject", value=email_subject)
    st.text_area("Email Body", value=email_body, height=250)

    gmail_url = (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&su={quote(email_subject)}"
        f"&body={quote(email_body)}"
    )

    st.markdown(f"[Open Draft in Gmail]({gmail_url})")

else:
    st.info("Upload resume PDFs to start analysis.")
    
