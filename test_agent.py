import os
from prompt import system_prompt
from typing import List, Dict, Any
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# Initialize LLMs and embeddings
llm_job_roles = ChatOpenAI(model="gpt-4-turbo-preview")
llm_noc_recommender = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)
llm_crs_score = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)
llm_roadmap = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)
llm_pathways = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)
llm_additional_recommendations = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)

embeddings = OpenAIEmbeddings()

from typing_extensions import TypedDict
class GraphState(TypedDict):
    questionnaire: str
    job_roles: str
    noc_codes: str
    high_demand_nocs: str
    crs_score: str
    roadmap: str
    pathways: str 
    additional_recommendations: str 
    age: int
    education_level: str
    first_language_scores: dict
    second_language_scores: dict
    canadian_work_exp: int
    foreign_work_exp: int
    certificate_qualification: bool
    provincial_nomination: bool
    arranged_employment: bool
    canadian_education: str
    sibling_in_canada: bool
    spouse_factors: dict


# Load NOC codes from PDF
file_path = "nocs (1).pdf"
loader = PyPDFLoader(file_path)
documents = loader.load()

# Create text splitter
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# Create FAISS index
noc_db = FAISS.from_documents(texts, embeddings)

# Define node functions
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

def retrieve_noc_codes(state):
    job_roles = state["job_roles"]
    relevant_docs = noc_db.similarity_search(job_roles, k=5)
    state["noc_codes"] = [doc.page_content for doc in relevant_docs]
    return state

def recommend_high_demand_nocs(state):
    """New node function that recommends high-demand NOCs based on client's profile"""
    questionnaire = state["questionnaire"]
    job_roles = state["job_roles"]
    noc_codes = state["noc_codes"]
    
    noc_recommendation_prompt = """You are a Canadian immigration advisor specializing in NOC (National Occupational Classification) recommendations. Focus specifically on high-demand NOCs that match the client's background or could be accessible with additional training.

INSTRUCTIONS:
1. Analyze the client's educational background, work experience, and skills from the questionnaire
2. Consider the job roles already identified for this client
3. Recommend suitable high-demand NOCs from this SPECIFIC list, focusing on MATCHING the client's qualifications or showing clear TRANSITION paths:

HIGH DEMAND NOC OPTIONS:
* NOC 33109: Other assisting occupations in support of health services
  - Eligible for clients with ANY background
  - No need for educational transition (no PDE or dummy BSc required)
  - Requires 1-year on-the-job training (client will receive training certificate/letter)

* NOC 33102: Nurse aides, orderlies and patient service associates
  - Requires showing educational transition (recommend dummy BSc + PDE in health-related field)
  - Suitable for auxiliary nurses
  - Requires 1-year on-the-job training (client will receive training certificate/letter)

* NOC 33103: Pharmacy technical assistants and pharmacy assistants
  - ONLY for clients with pharmacy background or related pharmacy field
  - Requires 6-month training before employment (client will receive training certificate/letter)

* NOC 33101: Medical laboratory assistants and related technical occupations
  - ONLY for clients with educational background in related fields (Microbiology, Chemistry, Biochemistry, etc.)
  - Requires 6-month training before employment (client will receive training certificate/letter)

  HEALTH NOC (EXPRESS ENTRY)
JOB TITLES
EMPLOYMENT REQUIREMENT AND COMPANIES
NOC 31110- Dentist
* Dentist
* Medical degree in Dentistry or Dental surgery
* COMPANY: Hospital or Dental Clinic
NOC 31121-Dietician and Nutritionist
* Dietitian, Nutritionist 
* Bachelor's degree in dietetics, nutrition or Food Science
* COMPANY: Hospitals, Healthcare agencies, Food, beverage and pharmaceutical industries, education, government and sport organizations
NOC 31102- General practitioners and Family Physicians 
* Family Physician
* General Practitioner
* Medical Doctor
* Resident Doctor
* Bachelor's degree in Medicine and Surgery
* COMPANY: Hospitals and Clinics 
NOC 33101- Medical Laboratory assistant and related technical occupation
* Medical Laboratory assistant
* College Certificate in Medical laboratory Science or Medical Laboratory assistant training certificate before the job. clients are required to have an educational background in a related field such as Microbiology, Chemistry, Biochemistry etc.
* COMPANY: Hospital, Medical Laboratory
NOC 32120-Medical Laboratory Technologist
* Medical Laboratory technologist or Medical Laboratory Scientist
* College certificate in Medical Laboratory Technology or Medical Laboratory Science.
* COMPANY: Hospital, Medical Laboratory
NOC 33102- Nurse Aides, orderlies and patient service associates
* Nurse Assistant
* Nurse Aide
* Secondary school diploma and one year on the job training certificate. To show transitioning, you can recommend dummy BSc and PDE in a health-related field. Auxiliary nurses can also be profiled under this category
* COMPANY: Hospitals and Clinics, nursing homes and Care facilities
NOC 31111- Optometrist
* Optometrist
* Medical Degree in Optometry
* COMPANY: Hospitals, and Optic Care Clinics or facility
NOC 31120- Pharmacist
* Pharmacist
* Bachelor's degree in Pharmacy
* COMPANY: Hospitals, Pharmacy
NOC 33103- Pharmacy technical assistant and pharmacy assistant 
* Pharmacy assistant
* Clients with a pharmacy background or a related pharmacy field can be profiled under this NOC. The process for profiling still remains the same, clients would be getting a training certificate or letter after 6 months of training before the commencement of their employment. 
* COMPANY: Hospitals, Pharmacy
NOC 31301-Registered nurses and registered psychiatric nurses 
* Registered Nurse
* Nurse
* BSc Nursing Science
* COMPANY: Hospitals, Clinics
NOC 31102- Veterinarians
* Veterinarian
* Doctor of Veterinary Medicine
* COMPANY: Vet Hospitals or Clinics 
NOC 42201- Social and Community service workers
* Social Service Worker
* BSc in psychology, social work or Social Science (Sociology)
* COMPANY: Government and mental health agencies, School Boards and correctional Facilities


AGRIC NOC (EXPRESS ENTRY)
JOB TITLES
EMPLOYMENT REQUIREMENT AND COMPANIES
NOC 63201- Butchers - retail and wholesale
* Butcher
* Retail Butcher
* Secondary School Diploma
* On the job training certificate for retail butches in food stores.
* COMPANY: Supermarkets, grocery stores, butcher shops

S/N 
STEM / EDUCATION NOC 
JOB TITLE 
NOC REQUIREMENT/EMPLOYER 
1.  
20011 - Architecture and science managers 
* Architectural manager 
* Architectural service manager 
* Landscape architecture manager 
* Scientific research manager 
NOC Requirement: Clients that have a degree in architecture or Landscape architecture can be profiled under this managerial NOC. Provided that they are able to show at least 2-3 years progression in a related junior role. Clients who haven't evaluated their architectural degree with WES before October 31, 2024 have to evaluate using "The Canadian Architectural Certification Board (CACB)", designated as the professional body for architects provided.  
Recommended Employer: Architectural firms, Real estate companied and scientific research companies.  
2 
21300 - Civil engineers: 
* Civil engineer 
* Construction engineer 
* Consulting civil engineer 
 
NOC Requirement: Clients that have a degree in civil engineering or in a related engineering discipline can be profiled under this NOC.  
Recommended Employer: Engineering consulting companies, construction firms and other related industries.  
4 
21220 - Cybersecurity specialists 
* Cybersecurity analyst 
* Cybersecurity specialist 
* Network security analyst 
* Systems security analyst 
NOC Requirement: Clients that have a degree in computer science, computer security, computer systems engineering, information systems or completion of a college program in information technology, network administration or another computer science related program can be profiled under this NOC.   
Recommended Employer: information technology consulting firms, IT companies, and Data/Network related companies 
5 
21310 - Electrical and electronics engineers 
 
* Electrical engineer 
* Electronics engineer 
NOC Requirement: Clients that have a degree in electrical or electronics engineering or in an appropriate related engineering discipline can be profiled under this NOC.  
Recommended Employer: Electrical utilities, communications companies, manufacturers of electrical and electronic equipment, manufacturing, processing and transportation companies. 
6 
21301 - Mechanical engineers 
* Mechanical engineer 
* Project mechanical engineer 
NOC Requirement: Clients that have a degree in mechanical engineering or in a related engineering discipline can be profiled under this NOC.  
Recommended Employer: consulting firms, by power-generating utilities, manufacturing, processing and transportation companies.  
7 
43100 - Elementary and secondary school teacher assistants 
* Classroom assistant 
* Teacher's assistant 
NOC Requirement: Completion of secondary school. Client would also be required to provide completion of a 10-month on-the-job training certificate in teaching assistance or educational assistance. 
Recommended Employer: Primary, Secondary or Special needs schools.   
8 
42202 - Early childhood educators and assistants 
* Early childhood assistant 
NOC Requirement: Completion of secondary school. Client would also be required to provide an early childhood education assistant certificate program or post-secondary courses in early childhood education. i.e. (PDE). 
Recommended Employer: Child-care centers, day-care centers, kindergartens, and other settings where early childhood education services are provided. i.e., Any primary/secondary schools that have day care, kindergartens class set up.  
9 
41221 - Elementary school and kindergarten teachers 
* Primary school teacher 
* Elementary school teacher 
NOC Requirement: Clients that have a degree in education and child development can be profiled under this NOC. Additional training is required to specialize in special education or second language instruction. 
Recommended Employer: Primary schools. i.e., Any primary schools that also have kindergartens class set up. 
10 
41220 - Secondary school teachers 
* Secondary school teacher 
* Subject Teacher 
NOC Requirement
Recommended Employer: Secondary Schools.            
 

TRADE NOCS AND THEIR REQUIREMENT  
NOCS 
REQUIRMENT  
POSSIBLE EMPLOYERS  
RECOMMENDED JOB TITLE  
70010-Construction Manager  
A university degree in civil engineering or a college diploma in construction technology is usually required and Several years of experience in the construction industry, including experience as a construction supervisor 
 
They are employed by residential, commercial and industrial construction companies  
Construction project manager, Construction site manager 
 
 
63200 - Cooks 
 
Completion of secondary school is usually required and Completion of a three-year apprenticeship program or completion of college or other program in cooking or food safety 
 
They are employed in restaurants, hotels, hospitals and other health care institutions, central food commissaries, educational institutions and other establishments. They are also employed aboard ships and at construction and logging campsites. 
Cook  
22303 - Construction estimators 
 
Completion of secondary school is required and Completion of a three-year college program in civil or construction engineering technology or quantity survey  
 
They are employed by residential, commercial and industrial construction companies and major electrical, mechanical and trade contractors, 
Quantity surveyor  
72320 - Bricklayers 
 
Completion of secondary school is usually required and Completion of a three- to four-year apprenticeship program 
 
They are employed by construction companies and bricklaying contractors 
Bricklayer 
 
72311 - Cabinetmakers 
 
Completion of secondary school is usually required and Completion of a four-year apprenticeship program 
 
They are employed by furniture manufacturing or repair companies, construction companies 
Furniture cabinetmaker, cabinetmaker 
 
72302 - Gas fitters 
 
Completion of secondary school is usually required and Completion of a two- or three-year gas fitter apprenticeship program  
 
They are employed by gas utility companies and gas servicing companies 
Gas servicer, Gas technician 
 
72300 - Plumbers 
 
Completion of secondary school is usually required and Completion of a four- to five-year apprenticeship program  
 
They are employed in maintenance departments of factories 
Plumber 
72201 - Industrial electricians 
 
Completion of secondary school is usually required and Completion of a four- or five-year industrial electrician apprenticeship program 
 
They are employed by electrical contractors and maintenance departments of factories, plants, mines, shipyards and other industrial establishments 
Electrician  
72200 - Electricians (except industrial and power system) 
 
Completion of secondary school is usually required and Completion of a four- to five-year apprenticeship program is usually required. 
 
They are employed by electrical contractors and maintenance departments of buildings and other establishments 
Electrician, Building Electrician, construction electrician  
73113 - Floor covering installers 
 
Completion of secondary school is usually required and Completion of a two- to three-year apprenticeship program  
They are employed by construction companies, floor-covering contractors and carpet outlets 
Floor Tiler, Rug layers for people who brought rugs and carpet companies, wood floor installer  
73112 - Painters and decorators  
 
Completion of secondary school is usually required and Completion of a three- to four-year apprenticeship program 
 
They are employed by construction companies, painting contractors and building maintenance contractors 
Painter, painter and decorator, building Painter  
  
IMPORTANT ELIGIBILITY RULES:
- DO NOT recommend NOCs requiring higher qualifications than the client possesses (e.g., don't recommend positions requiring masters/specialization if client only has bachelors)
- ONLY recommend NOCs the client can qualify for, either directly or through reasonable additional training/certification
- If the client needs additional qualifications, clearly explain what training/diploma they should pursue to become eligible

FORMAT YOUR RESPONSE:
1. Client Profile Summary: Brief overview of relevant education and experience
2. Recommended High-Demand NOCs: List each suitable NOC with:
   - NOC code and title
   - Explanation of why this NOC matches their background
   - Any required transition path or additional training needed
   - Timeline and certification process
3. Conclusion: Best NOC option for fastest immigration pathway

Questionnaire: {questionnaire}
Previously Identified Job Roles: {job_roles}
Retrieved NOC Information: {noc_codes}
"""

    prompt = ChatPromptTemplate.from_template(noc_recommendation_prompt)
    chain = prompt | llm_noc_recommender | StrOutputParser()
    high_demand_nocs = chain.invoke({
        "questionnaire": questionnaire,
        "job_roles": job_roles,
        "noc_codes": noc_codes
    })
    
    state["high_demand_nocs"] = high_demand_nocs
    return state

def calculate_crs_score(state):
    from datetime import datetime
    current_date = datetime.now()
    
    questionnaire = state["questionnaire"]
    
    crs_calculation_prompt = f"""You are a CRS (Comprehensive Ranking System) calculator for Canadian immigration. Your job is to calculate ACCURATE scores and provide MULTIPLE SCENARIOS when information is uncertain.

STEP 1: EXTRACT ALL CLIENT INFORMATION
Carefully analyze the questionnaire and identify ALL of these factors:
- Age (given in MM/DD/YYYY, exact age as of {current_date.strftime('%M %d, %Y')})
- Education level (all credentials mentioned)
- Language proficiency (all test scores or projected scores)
- Work experience (years and type)
- Canadian connections/experience
- Spouse or common-law partner details (if applicable)
- Any provincial nominations, job offers, or Canadian education


STEP 2: IDENTIFY UNCERTAINTIES AND POSSIBILITIES
For any ambiguous information or where multiple interpretations are possible:
- Note each possible scenario (e.g., different education credentials, projected vs. actual language scores)
- Create distinct calculation paths for each scenario

STEP 3: CALCULATE SEPARATE CRS SCORES FOR EACH SCENARIO
For each possibility, calculate a complete score following the official criteria:

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

              CLB 4-5: 6 points per ability

              CLB 6: 9 (without spouse), 8 (with spouse) per ability

              CLB 7: 17 (without spouse), 16 (with spouse) per ability

              CLB 8: 23 (without spouse), 22 (with spouse) per ability

              CLB 9: 31 (without spouse), 29 (with spouse) per ability

              CLB 10+: 34 (without spouse), 32 (with spouse) per ability

              Second Official Language:

              CLB 5-6: 1 point per ability (max 24 without spouse, 22 with spouse)

              CLB 7-8: 3 points per ability

              CLB 9+: 6 points per ability

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
                With good official language proficiency (Canadian Language Benchmark Level [CLB] 7 or higher) and a post-secondary degree
                Secondary school (high school) credential or less: 0 points
                Post-secondary program credential of one year or longer:
                CLB 7 or more on all first official language abilities, with one or more under CLB 9: 13 points
                CLB 9 or more on all four first official language abilities: 25 points
                Two or more post-secondary program credentials, with at least one credential from a program of three years or longer:
                CLB 7 or more: 25 points
                CLB 9 or more: 50 points
                University-level credential at the master's level or an entry-to-practice professional degree requiring provincial licensing (National Occupational Classification Skill Level A):
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
                Two or more post-secondary program credentials, with at least one credential from a program of three years or longer:
                With 1 year of Canadian work experience: 25 points
                With 2 years or more of Canadian work experience: 50 points
                University-level credential at the master's level or an entry-to-practice professional degree requiring provincial licensing (National Occupational Classification Skill Level A):
                With 1 year of Canadian work experience: 25 points
                With 2 years or more of Canadian work experience: 50 points
                University-level credential at the doctoral level:
                With 1 year of Canadian work experience: 25 points
                With 2 years or more of Canadian work experience: 50 points
                Foreign Work Experience
                With good official language proficiency (CLB 7 or higher)
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
                With good official language proficiency (CLB 5 or higher)
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

STEP 4: PRESENT RESULTS CLEARLY
Format your response as follows:
1. CLIENT PROFILE SUMMARY: Summarize the key facts you extracted
2. IDENTIFIED SCENARIOS: Create multiple practical scenarios focused on improving individual factors:
   - Scenario 1 (Base Condition): Use current IELTS scores if available, otherwise use projected IELTS scores (CLB:9, Listening: 8, Reading: 7, Writing: 7, Speaking: 7). Use all details exactly as given in the questionnaire. If any value is listed as "Nil," assume 0 (e.g., "Nil" work experience = 0 years), NEVER pick up extra information or wrong information that is not present in the questionairre..
   
   - Additional Scenarios: Create separate scenarios for each individual improvement opportunity:
     * If client has a Bachelor's degree: create a scenario with a Post-Graduate Diploma
     * If client has a PGD: create a scenario with a Master's degree
     * If client has a Master's: create a scenario with a PhD
     * If client has less than minimum projected IELTS: create a scenario with improved IELTS (8,7,7,7); Whenever recommeding projected CRS score we NEVER recommend more than the  projected IELTS score (i.e. CLB 9, L:8, R:7,W:7,S:7) so don't make a scenario having higher projected IELTS score than this.
     * If client has less than 3 years foreign work experience: create a scenario with 3+ years experience(Use the term '3+ years work experience' only and not terms like 5 years, because every 3+ years all have same points)
     
   - Create one scenario per improvement factor, resulting in multiple focused scenarios rather than limiting to just three scenarios.
 
3. DETAILED CALCULATIONS: For each scenario, show:
   - Scenario name (e.g., "Scenario 1: BSc degree with current IELTS scores")
   - Complete point breakdown by category
   - Clear subtotals for each section
   - Final CRS score
4. SUMMARY OF RESULTS: Show all scenario scores in a comparison table
Remember: Your goal is ACCURACY and COMPLETENESS. Consider every detail from the questionnaire and provide multiple score scenarios when information allows for different interpretations.
    Questionnaire: {questionnaire}
    """

    prompt = ChatPromptTemplate.from_template(crs_calculation_prompt)
    chain = prompt | llm_crs_score | StrOutputParser()
    crs_score = chain.invoke({"questionnaire": questionnaire})
    state["crs_score"] = crs_score
    return state

def recommend_pathways(state):
    """Node function that recommends immigration pathways based on NOC codes and CRS score"""
    questionnaire = state["questionnaire"]
    high_demand_nocs = state["high_demand_nocs"]
    crs_score = state["crs_score"]
    
    pathways_prompt = """You are a Canadian immigration pathways advisor specializing in recommending the most suitable immigration programs.

INSTRUCTIONS:
1. Analyze the client's profile, high-demand NOCs recommended, and CRS score
2. Recommend immigration pathways that match EACH recommended NOC
3. For each pathway, specify the region/province AND the draw type (e.g., HEALTH Draw, TRADE Draw)
4. Ensure the number of pathways recommended equals the number of NOCs recommended
5. Consider the client's CRS score when recommending Express Entry pathways

DRAW TYPES TO PRIORITIZE:
- HEALTH Draw: For healthcare-related NOCs (e.g., 33102, 33101, 33103, 31301)
- TRADE Draw: For skilled trades NOCs (e.g., 72300, 72320, 73200)
- STEM Draw: For science, technology, engineering and math NOCs
- Transport Draw: For transportation-related NOCs
- Agriculture/Agri-Food Draw: For agriculture and food industry NOCs

PATHWAY OPTIONS TO CONSIDER:
1. Express Entry (Federal)
   - Federal Skilled Worker Program (FSWP)
   - Federal Skilled Trades Program (FSTP)
   - Canadian Experience Class (CEC)
   - Category-based selection draws (HEALTH, TRADE, STEM, Transport, Agriculture/Agri-Food)

2. Provincial Nominee Programs (PNPs)
   - Ontario Immigrant Nominee Program (OINP)
   - Alberta Advantage Immigration Program (AAIP)
   - Saskatchewan Immigrant Nominee Program (SINP)


3. Atlantic Immigration Program (AIP)
   - For positions in New Brunswick, Nova Scotia, Prince Edward Island, or Newfoundland and Labrador

EXAMPLES OF PATHWAY RECOMMENDATIONS:
Example 1:
NOC 33102 – Nurse aides, orderlies and patient service associates
Pathway 1: Express Entry (Federal) - HEALTH Draw
Pathway 2: Ontario Immigrant Nominee Program (OINP) - HEALTH Draw

Example 2:
NOC 73200 – Residential and commercial installers and servicers
Pathway 1: Express Entry (Federal) - TRADE Draw
Pathway 2: Alberta Advantage Immigration Program (AAIP) - TRADE Draw

Example 3:
NOC 21220 – Information systems specialists
Pathway 1: Express Entry (Federal) - STEM Draw
Pathway 2: British Columbia Provincial Nominee Program (BC PNP) - STEM Draw

FORMAT YOUR RESPONSE:
1. Client Profile Summary: Brief mention of CRS score range and key qualifications
2. Recommended Pathways: For each NOC recommended, provide:
   - NOC code and title
   - Option A: [Program] - [Region/Province] ([Draw Type] in capital letters)
   - Option B: [Program] - [Region/Province] ([Draw Type] in capital letters)
   - Option C: [Another Program] - [Region/Province] ([Draw Type] in capital letters) (if applicable)
3. Label each pathway as "Option A", "Option B", "Option C" etc.
4. For healthcare NOCs, always specify "HEALTH Draw" in capital letters
5. For trade NOCs, always specify "TRADE Draw" in capital letters
6. Include exact formatting as shown in examples, with parentheses around the draw type

Questionnaire: {questionnaire}
High-Demand NOC Recommendations: {high_demand_nocs}
CRS Score Calculation: {crs_score}
"""

    prompt = ChatPromptTemplate.from_template(pathways_prompt)
    chain = prompt | llm_pathways | StrOutputParser()
    pathways = chain.invoke({
        "questionnaire": questionnaire,
        "high_demand_nocs": high_demand_nocs,
        "crs_score": crs_score
    })
    
    state["pathways"] = pathways
    return state

def generate_additional_recommendations(state):
    """
    Node function that generates detailed and personalized additional recommendations
    based on the client's profile, NOC codes, CRS score, and recommended pathways.
    """
    questionnaire = state["questionnaire"]
    high_demand_nocs = state["high_demand_nocs"]
    crs_score = state["crs_score"]
    pathways = state["pathways"]
    
    additional_recommendations_prompt = """You are a Canadian immigration advisor specializing in providing practical immigration implementation guidance.

TASK: Generate a concise, bullet-point style set of NOTES that outline exactly what the client needs to do to proceed with their application, focusing on document requirements, employer specifications, and practical implementation steps.

INSTRUCTIONS:
1. Format your entire response as "NOTES:" followed by bullet points (●)
2. Use direct, concise language that a client can immediately act upon
3. Specify EXACT requirements for documentation, employment letters, and supporting evidence
4. Include CONCRETE examples of employer types with specific details (e.g., "Medical company such as Hospital and Nursing home that is registered with online presence and active website")
5. Mention SPECIFIC document requirements (e.g., "Offer letter, Reference Letter, Pay slips, Bank Statement, Work ID card")
6. Include any required training periods with specific timeframes (e.g., "12-18 months on-the-job training letter")
7. Clearly state which documents qualify the client for each NOC (e.g., "Your SSCE certificate would be qualifying you for this NOC")

REQUIRED CONTENT SECTIONS:
1. Educational Assessment:
   - Mention ALL relevant degrees (PA and spouse) and if they need to be evaluated
   - Specifically address if PA needs to present PDE or MSc to show "smooth transitioning" for health NOCs
   - Mention any additional educational requirements or evaluations needed

2. Language Testing:
   - Specify IELTS requirements and impact on application
   - Note if higher scores would provide faster selection

3. Current Job Role Analysis:
   - Assess if current job NOC is suitable or problematic for immigration
   - Provide reasoning why current job might not be advisable
   - Mention if documentation requirements would be difficult to meet

4. Pathway-Specific Implementation:
   For EACH recommended NOC:
   - Specify exact employer type needed with concrete examples
   - List ALL required employment documents
   - Detail any progression requirements (e.g., "show progression from Junior role for at least 3 years")
   - Specify qualifying certificates needed
   - Include required training periods with timeframes

5. Important Notes:
   - Add critical implementation details (e.g., "website for companies should be functional throughout application")
   - Include any timing considerations
   - Mention any other practical considerations

IMPORTANT FORMATTING REQUIREMENTS:
- Begin with "NOTES:" followed by bullet points
- Use "●" for all bullet points
- Use terms like "PA" for principal applicant and "SSCE" for secondary school certificate
- Refer to pathways as "PNP Option A:" or "PNP & EEP:" as appropriate
- Use parentheses to highlight NOC codes: "(NOC 33102)"
- Clearly label NOC categories: "which is a HEALTH NOC" or "which is a TRADE NOC"
- Include important information in "NOTE:" sections at the end

Remember, this should be practical, direct implementation guidance rather than general advice.

Questionnaire: {questionnaire}
High-Demand NOC Recommendations: {high_demand_nocs}
CRS Score Calculation: {crs_score}
Recommended Pathways: {pathways}
"""

    prompt = ChatPromptTemplate.from_template(additional_recommendations_prompt)
    chain = prompt | llm_additional_recommendations | StrOutputParser()
    additional_recommendations = chain.invoke({
        "questionnaire": questionnaire,
        "high_demand_nocs": high_demand_nocs,
        "crs_score": crs_score,
        "pathways": pathways
    })
    
    state["additional_recommendations"] = additional_recommendations
    return state

def generate_roadmap(state):
    questionnaire = state["questionnaire"]
    noc_codes = state["noc_codes"]
    high_demand_nocs = state["high_demand_nocs"]  # Include the high demand NOCs
    crs_score = state["crs_score"]
    
    # Update roadmap prompt to include high_demand_nocs
    roadmap_prompt = system_prompt + f"""

HIGH-DEMAND NOC RECOMMENDATIONS:
{high_demand_nocs}

When creating the immigration roadmap, please also consider these high-demand NOC recommendations, prioritizing them when appropriate for the client's profile and immigration goals.
"""
    
    prompt = ChatPromptTemplate.from_template(roadmap_prompt)
    chain = prompt | llm_roadmap | StrOutputParser()
    roadmap = chain.invoke({
        "questionnaire": questionnaire,
        "noc_codes": noc_codes,
        "crs_score": crs_score
    })
   
    state["roadmap"] = roadmap
    return state

# Define workflow graph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("determine_job_roles", determine_job_roles)
workflow.add_node("retrieve_noc_codes", retrieve_noc_codes)
workflow.add_node("recommend_high_demand_nocs", recommend_high_demand_nocs)
workflow.add_node("calculate_crs_score", calculate_crs_score)
workflow.add_node("recommend_pathways", recommend_pathways)
workflow.add_node("generate_additional_recommendations", generate_additional_recommendations)
workflow.add_node("generate_roadmap", generate_roadmap)

# Add edges
workflow.add_edge("determine_job_roles", "retrieve_noc_codes")
workflow.add_edge("retrieve_noc_codes", "recommend_high_demand_nocs")
workflow.add_edge("recommend_high_demand_nocs", "calculate_crs_score")
workflow.add_edge("calculate_crs_score", "recommend_pathways")
workflow.add_edge("recommend_pathways", "generate_additional_recommendations")
workflow.add_edge("generate_additional_recommendations", "generate_roadmap")
workflow.add_edge("generate_roadmap", END)

# Configure and compile
workflow.set_entry_point("determine_job_roles")
graph_app = workflow.compile()