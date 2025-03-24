import os
from prompt import system_prompt
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader  # Change to PDF loader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# Initialize LLMs and embeddings
llm_job_roles = ChatOpenAI(model="gpt-4o")
llm_crs_score = ChatOpenAI(model="gpt-4o",temperature=0.3)
llm_roadmap = ChatOpenAI(model="gpt-4o",temperature=0.6)
embeddings = OpenAIEmbeddings()

from typing_extensions import TypedDict
class GraphState(TypedDict):
    questionnaire: str
    job_roles: str
    noc_codes: str
    crs_score: str
    roadmap: str
    # Add new fields for detailed CRS calculation
    age: int
    education_level: str
    first_language_scores: dict  # CLB scores for first language
    second_language_scores: dict  # CLB scores for second language
    canadian_work_exp: int
    foreign_work_exp: int
    certificate_qualification: bool
    provincial_nomination: bool
    arranged_employment: bool
    canadian_education: str
    sibling_in_canada: bool
    spouse_factors: dict  # If applicable


# Load NOC codes from PDF (adjust file path accordingly)
file_path = "nocs (2).pdf"  # Path to your PDF file
loader = PyPDFLoader(file_path)  # Use PyPDFLoader instead of CSVLoader
documents = loader.load()

# Create a text splitter (adjust chunk size as needed)
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# Create the FAISS index
noc_db = FAISS.from_documents(texts, embeddings)

# Define node functions (same as before)
def determine_job_roles(state):
    questionnaire = state["questionnaire"]
    prompt = ChatPromptTemplate.from_template(
        """Based on the following client questionnaire, consider the educational background and work experience to determine the most relevant
         job roles, we would use these job roles roles to find NOC codes, these job roles don't necessarily have to be related 
         to degree or work experience, we can also recommend job roles which are in high demand.:\n\n{questionnaire}, return JUST the job roles titles with their pathways separated by comma, you should have a proper reasoning for recommending those roles""")

    chain = prompt | llm_job_roles | StrOutputParser()
    job_roles = chain.invoke({"questionnaire": questionnaire})
    state["job_roles"] = job_roles
    return state

# def retrieve_noc_codes(state):
#     job_roles = state["job_roles"]
#     relevant_docs = noc_db.similarity_search(job_roles, k=5)
#     state["noc_codes"] = [doc.page_content for doc in relevant_docs]
#     return state


def retrieve_noc_codes(state):
    import re
    job_roles = state["job_roles"]
    relevant_docs = noc_db.similarity_search(job_roles, k=5)
    noc_list = []
    # Define a regex to match header lines that indicate a category.
    # For example, lines that end with "Occupations" (case-insensitive)
    header_regex = re.compile(r'^[A-Za-z\s]+Occupations$', re.IGNORECASE)
    for doc in relevant_docs:
        text = doc.page_content
        lines = text.splitlines()
        category = "Unknown Category"
        # Look for a header line in the first few lines
        for line in lines:
            line_clean = line.strip()
            if header_regex.match(line_clean):
                category = line_clean
                break
        # Append a dictionary with the full NOC text and its category.
        noc_list.append({"noc_info": text.strip(), "category": category})
    print("DEBUG: Retrieved NOC codes in retrieve_noc_codes:", noc_list)
    state["noc_codes"] = noc_list
    return state

def calculate_crs_score(state):
    from datetime import datetime
    current_date = datetime.now()
    
    questionnaire = state["questionnaire"]
    
    crs_calculation_prompt = f"""You are a CRS (Comprehensive Ranking System) calculator for Canadian immigration. Your job is to calculate ACCURATE scores and provide MULTIPLE SCENARIOS when information is uncertain.

Current Date: {current_date.strftime('%M %d, %Y')}

### **STEP 1: EXTRACT ALL CLIENT INFORMATION**
Extract the following details **accurately** from the questionnaire:

#### **Primary Applicant (PA)**
- **Age** (calculate exact age using the given birthdate)
- **Education level** (all credentials mentioned)
- **Language proficiency** (all test scores or projected scores)
- **Work experience** (years and type; if "Nil", assume 0)
- **Canadian experience, job offers, provincial nominations**

#### **Spouse (If client is married)**
- **Spouse’s education level**
- **Spouse’s IELTS scores** (If not provided, assume **projected IELTS: Listening: 8, Reading: 7, Writing: 7, Speaking: 7** which corresponds to CLB 9)
- **Spouse’s work experience**

### **STEP 2: IDENTIFY UNCERTAINTIES AND GENERATE SCENARIOS**
- If **IELTS scores** are missing, assume projected scores:  
  **(Listening: 8, Reading: 7, Writing: 7, Speaking: 7)**  
  Note: These scores correspond to CLB 9, which should yield 31 points per ability (without spouse) and 29 points per ability (with spouse).
- If **work experience** is "Nil", assume **0 years**.
- For married clients, always factor in spouse’s details (education, work experience, IELTS).

### **STEP 3: CALCULATE SEPARATE CRS SCORES FOR EACH SCENARIO**
For each possibility, calculate a complete CRS score following the official criteria provided below:

          1. CORE/HUMAN CAPITAL FACTORS:

              Maximum 460 points with a spouse or common-law partner  
              Maximum 500 points without a spouse or common-law partner

              Age (Max 110 points without a spouse, 100 with a spouse)  
              17 or younger: 0  
              18: 99 (without spouse), 90 (with spouse)  
              19: 105 (without spouse), 95 (with spouse)  
              20-29: 110 (without spouse), 100 (with spouse)  
              30: 105 (without spouse), 95 (with spouse)  
              31: 99 (without spouse), 90 (with spouse)  
              32: 94 (without spouse), 85 (with spouse)  
              33: 88 (without spouse), 80 (with spouse)  
              34: 83 (without spouse), 75 (with spouse)  
              35: 77 (without spouse), 70 (with spouse)  
              36: 72 (without spouse), 65 (with spouse)  
              37: 66 (without spouse), 60 (with spouse)  
              38: 61 (without spouse), 55 (with spouse)  
              39: 55 (without spouse), 50 (with spouse)  
              40: 50 (without spouse), 45 (with spouse)  
              41: 39 (without spouse), 35 (with spouse)  
              42: 28 (without spouse), 25 (with spouse)  
              43: 17 (without spouse), 15 (with spouse)  
              44: 6 (without spouse), 5 (with spouse)  
              45 or older: 0

              Education (Max 150 points without a spouse, 140 with a spouse)  
              Less than secondary school: 0  
              High school diploma: 30 (without spouse), 28 (with spouse)  
              One-year post-secondary: 90 (without spouse), 84 (with spouse)  
              Two-year post-secondary: 98 (without spouse), 91 (with spouse)  
              Bachelor's or three-year degree: 120 (without spouse), 112 (with spouse)  
              Two or more degrees (one 3+ years): 128 (without spouse), 119 (with spouse)  
              Master's degree/professional degree: 135 (without spouse), 126 (with spouse)  
              PhD: 150 (without spouse), 140 (with spouse)

              Language Proficiency (Max 160 points without a spouse, 150 with a spouse)  

              First Official Language:  
              - CLB 4-5: 6 points per ability  
              - CLB 6: 9 (without spouse), 8 (with spouse) per ability  
              - CLB 7: 17 (without spouse), 16 (with spouse) per ability  
              - CLB 8: 23 (without spouse), 22 (with spouse) per ability  
              - **CLB 9: 31 (without spouse), 29 (with spouse) per ability**  
              - CLB 10+: 34 (without spouse), 32 (with spouse) per ability

              Second Official Language:  
              - CLB 5-6: 1 point per ability (max 24 without spouse, 22 with spouse)  
              - CLB 7-8: 3 points per ability  
              - CLB 9+: 6 points per ability

              Work Experience (Max 80 points without a spouse, 70 with a spouse)  
              1 year: 40 (without spouse), 35 (with spouse)  
              2 years: 53 (without spouse), 46 (with spouse)  
              3 years: 64 (without spouse), 56 (with spouse)  
              4 years: 72 (without spouse), 63 (with spouse)  
              5+ years: 80 (without spouse), 70 (with spouse)

          2. SPOUSE OR COMMON-LAW PARTNER FACTORS (if applicable, Max 40 points):  
              Education: 10 points max  
              Official language proficiency: 20 points max  
              Canadian work experience: 10 points max

          3. SKILL TRANSFERABILITY FACTORS (Max 100 points):  
              With strong language proficiency and post-secondary education: 50 points max  
              With Canadian work experience and post-secondary education: 50 points max  
              With strong language proficiency and foreign work experience: 50 points max  
              With Canadian work experience and foreign work experience: 50 points max  
              With certificate of qualification in trade occupations: 50 points max  

              Education  
                With good official language proficiency (CLB 7 or higher) and a post-secondary degree  
                Secondary school (high school) credential or less: 0 points  
                Post-secondary program credential of one year or longer:  
                CLB 7 or more on all first official language abilities, with one or more under CLB 9: 13 points  
                CLB 9 or more on all four first official language abilities: 25 points  
                Two or more post-secondary program credentials, with at least one credential from a program of three years or longer:  
                CLB 7 or more: 25 points  
                CLB 9 or more: 50 points  
                University-level credential at the master's level or an entry-to-practice professional degree:  
                CLB 7 or more: 25 points  
                CLB 9 or more: 50 points  
                University-level credential at the doctoral level:  
                CLB 7 or more: 25 points  
                CLB 9 or more: 50 points  
                With Canadian work experience and a post-secondary degree  
                Secondary school (high school) credential or less: 0 points  
                Post-secondary program credential of one year or longer:  
                With 1 year of Canadian work experience: 13 points  
                With 2 years or more of Canadian work experience: 25 points  
                Two or more post-secondary program credentials, with at least one from a program of three years or longer:  
                With 1 year of Canadian work experience: 25 points  
                With 2 years or more of Canadian work experience: 50 points  
                University-level credential at the master's level or an entry-to-practice professional degree:  
                With 1 year of Canadian work experience: 25 points  
                With 2 years or more of Canadian work experience: 50 points  
                University-level credential at the doctoral level:  
                With 1 year of Canadian work experience: 25 points  
                With 2 years or more of Canadian work experience: 50 points  
                Foreign Work Experience  
                With good official language proficiency (CLB 7 or higher):  
                No foreign work experience: 0 points  
                1 or 2 years of foreign work experience:  
                CLB 7 or more, with one or more under CLB 9: 13 points  
                CLB 9 or more on all four language abilities: 25 points  
                3 years or more of foreign work experience:  
                CLB 7 or more: 25 points  
                CLB 9 or more: 50 points  
                With Canadian work experience  
                No foreign work experience: 0 points  
                1 or 2 years of foreign work experience:  
                With 1 year of Canadian work experience: 13 points  
                With 2 years or more of Canadian work experience: 25 points  
                3 years or more of foreign work experience:  
                With 1 year of Canadian work experience: 25 points  
                With 2 years or more of Canadian work experience: 50 points  
                Certificate of Qualification (Trade Occupations)  
                With good official language proficiency (CLB 5 or higher):  
                With a certificate of qualification:  
                CLB 5 or more, with one or more under CLB 7: 25 points  
                CLB 7 or more on all four language abilities: 50 points

          4. ADDITIONAL POINTS (Max 600 points):

              Provincial Nomination: 600 points  
              Arranged Employment:  
              NOC TEER 0 Major Group 00: 200 points  
              Other NOC TEER 0, 1, 2, 3: 50 points  
              Post-secondary education in Canada:  
              1-2 years: 15 points  
              3+ years: 30 points  
              French language skills (CLB 7+ in French and CLB 4 or lower in English): 25 points  
              French language skills (CLB 7+ in French and CLB 5+ in English): 50 points  
              Sibling in Canada (citizen/PR): 15 points

### **STEP 4: PRESENT RESULTS CLEARLY**
Format your response exactly as follows:
1. **CLIENT PROFILE SUMMARY:** Summarize the key facts extracted from the questionnaire.
2. **IDENTIFIED SCENARIOS:** List all possible interpretations of the client's profile. Follow these specific rules:
   - **For all clients (Base Scenario):**
     - Use the current IELTS score if available; if not, assume the projected IELTS scores. Note: For language proficiency, the projected IELTS scores of Listening: 8, Reading: 7, Writing: 7, Speaking: 7 correspond to CLB 9. This means each ability will score 31 points (without spouse) or 29 points (with spouse).
     - Use the questionnaire details exactly as provided (if “Nil” is given, assume 0 for work experience).
   - **For scenarios with improvements:**
     - Improve one factor at a time. For example:
         - If the client has a bachelor's degree, assume a scenario with a higher qualification (e.g., PGD or Master's) while keeping other factors the same.
         - If the current IELTS score is below the projected, assume the projected IELTS (CLB 9).
         - If foreign work experience is less than 3 years, assume 3 years.
   - **For married clients:**
     - In addition to the above, include spouse factors:
         - Extract spouse’s education, IELTS scores, and work experience.
         - Generate scenarios for the principal applicant along with spouse scenarios in parallel. For example, possible scenarios for a married client could be:
             - Scenario 1: Principal applicant with BSc (using current or projected IELTS) and spouse with BSc (using projected IELTS) – (Projected CRS score: 414)
             - Scenario 2: Principal applicant with Two or more degrees (using projected IELTS) and spouse with BSc (using projected IELTS) – (Projected CRS score: 446)
             - Scenario 3: Principal applicant with MSc (using projected IELTS) and spouse with Two or more degrees (using projected IELTS) – (Projected CRS score: 453)
   - **Additional Scenarios:** If more than one factor can be improved, create separate scenarios by changing only one factor at a time.
3. **DETAILED CALCULATIONS:** For each scenario, provide:
   - Scenario name (e.g., "Scenario 1: Base - BSc with projected IELTS" or "Scenario 2: BSc with 3 years foreign work experience")
   - A complete point breakdown by category with clear subtotals for each section
   - The final CRS score.
4. **SUMMARY OF RESULTS:** Present a comparison table listing all scenario scores.

---
**IMPORTANT:**  
🔹 For the BASE scenario, use only the information given in the questionnaire without inventing extra details. If any field is "Nil" or unspecified, assume the default values as described (e.g., 0 for work experience, and the projected IELTS scores which correspond to CLB 9).  
🔹 **Always factor in spouse’s details if the applicant is married.**  
🔹 **Spouse should always get projected IELTS scores (8,7,7,7) if missing.**  
🔹 **Points from spouse’s education & work experience should be counted in every scenario. For example:**
  - Projected CRS score:414 (PA's BSc, Projected IELTS, Spouse BSc, Projected IELTS)  
  - Projected CRS score:446 (PA's Two or more degree, Projected IELTS, Spouse BSc, Projected IELTS)  
  - Projected CRS score:453 (PA's MSc, Projected IELTS, Spouse Two or more degree, Projected IELTS)

---
Questionnaire: {{questionnaire}}

Return the roadmap using the provided information in proper markdown formatting with all sections filled out and aligned.
"""
    
    prompt = ChatPromptTemplate.from_template(crs_calculation_prompt)
    chain = prompt | llm_crs_score | StrOutputParser()
    crs_score = chain.invoke({"questionnaire": questionnaire})
    print("DEBUG: Received CRS score in generate_roadmap:", crs_score)
    state["crs_score"] = crs_score
    return state

# def generate_roadmap(state):
#     questionnaire=state["questionnaire"]
#     noc_codes = state["noc_codes"]
#     crs_score = state["crs_score"]
#     crs_score = state.get("crs_score", "")
#     print("DEBUG: Received CRS score in generate_roadmap:", crs_score)
#     # print(f"Crs score is {crs_score}")
#     roadmap_prompt = system_prompt
#     prompt = ChatPromptTemplate.from_template(roadmap_prompt)
#     chain = prompt | llm_roadmap | StrOutputParser()
#     roadmap = chain.invoke({"questionnaire":questionnaire,"noc_codes": noc_codes, "crs_score": crs_score})
   
#     state["roadmap"] = roadmap
#     return state

def generate_roadmap(state):
    questionnaire = state["questionnaire"]
    noc_codes_list = state["noc_codes"]
    # Convert list of NOC dictionaries into a formatted string
    noc_codes_str = ""
    option_letter = ord('A')
    for entry in noc_codes_list:
        # Here, we assume entry["noc_info"] contains the NOC code and title,
        # and we append the extracted category in parentheses.
        category = entry.get("category", "Unknown Category")
        noc_codes_str += f"Option {chr(option_letter)}: {entry['noc_info']} (Category: {category})\n"
        option_letter += 1

    crs_score = state.get("crs_score", "")
    roadmap_prompt = system_prompt
    prompt = ChatPromptTemplate.from_template(roadmap_prompt)
    chain = prompt | llm_roadmap | StrOutputParser()
    roadmap = chain.invoke({"questionnaire": questionnaire, "noc_codes": noc_codes_str, "crs_score": crs_score})
   
    state["roadmap"] = roadmap
    return state


# Define the graph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("determine_job_roles", determine_job_roles)
workflow.add_node("retrieve_noc_codes", retrieve_noc_codes)
workflow.add_node("calculate_crs_score", calculate_crs_score)
workflow.add_node("generate_roadmap", generate_roadmap)

# Define edges
workflow.add_edge("determine_job_roles", "retrieve_noc_codes")
workflow.add_edge("retrieve_noc_codes", "calculate_crs_score")
workflow.add_edge("calculate_crs_score", "generate_roadmap")
workflow.add_edge("generate_roadmap", END)

# Set the entrypoint
workflow.set_entry_point("determine_job_roles")

# Compile the graph
graph_app = workflow.compile()