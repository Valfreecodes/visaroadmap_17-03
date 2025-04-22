import os
from prompt import system_prompt, crs_calculation_prompt, filtering_prompt_template
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
import re
from pydantic import BaseModel
from typing import List, Optional

load_dotenv()

# Initialize LLMs and embeddings
llm_job_roles = ChatOpenAI(model="gpt-4o")
llm_crs_score = ChatOpenAI(model="gpt-4o",temperature=0.2)
llm_roadmap = ChatOpenAI(model="gpt-4o",temperature=0.6)
# Add a new LLM instance for filtering if needed, or reuse one
llm_filter = ChatOpenAI(model="gpt-4o", temperature=0)

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

class NOCRecommendation(BaseModel):
    noc_info: str
    category: str

class NOCRecommendationList(BaseModel):
    recommendations: List[NOCRecommendation]

# Load NOC codes from PDF (adjust file path accordingly)
file_path = "nocs (3).pdf"  # Path to your PDF file
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

# Add a new LLM instance for filtering if needed, or reuse one
llm_filter = ChatOpenAI(model="gpt-4o", temperature=0)
# You might need to import re if not already done globally
import re
import ast # For parsing LLM string output - use JSON/Pydantic parser for production

def filter_feasible_nocs(state):
    """
    Filters the retrieved NOC codes based on client's qualifications,
    potential for upskilling, and defined prioritization rules.
    """
    questionnaire = state["questionnaire"]
    retrieved_nocs = state["noc_codes"] # This is the list of dicts

    if not retrieved_nocs:
        print("DEBUG: No NOCs retrieved, skipping filtering.")
        state["noc_codes"] = []
        return state

    # Prepare NOC information for the prompt
    noc_options_text = ""
    potential_noc_details = [] # Store details for easier access later if needed
    for i, noc_data in enumerate(retrieved_nocs):
        noc_info = noc_data.get("noc_info", "")
        category = noc_data.get('category', 'Unknown Category')
        
        # Try to extract NOC code and title
        noc_title_match = re.search(r"NOC\s*(\d{5})\s*–?\s*(.*)", noc_info, re.IGNORECASE)
        noc_code = noc_title_match.group(1) if noc_title_match else "Unknown"
        # Clean up title extraction if needed
        noc_title = noc_title_match.group(2).strip().split('\n')[0] if noc_title_match else "Unknown Title" 
        
        description_snippet = noc_info[:300] # First 300 chars for context

        noc_options_text += f"Option {i+1}:\n"
        noc_options_text += f"  Code: {noc_code}\n"
        noc_options_text += f"  Title: {noc_title}\n"
        noc_options_text += f"  Category: {category}\n"
        noc_options_text += f"  Description Snippet: {description_snippet}...\n\n"
        
        potential_noc_details.append({
            "code": noc_code,
            "title": noc_title,
            "category": category,
            "full_info": noc_info, # Keep original info for selection
            "original_dict": noc_data # Store the original dictionary
        })

    # Create the prompt for the filtering LLM
    # Current date added for context, if needed by LLM reasoning. Adjust date format as desired.
    from datetime import datetime
    current_date_str = datetime.now().strftime('%Y-%m-%d')

    prompt = ChatPromptTemplate.from_template(filtering_prompt_template)
    # Ensure the correct LLM instance is used
    chain = prompt | llm_filter | StrOutputParser()

    try:
        filtered_nocs_str = chain.invoke({
            "questionnaire": questionnaire,
            "noc_options_text": noc_options_text
        })

        # Clean the response
        filtered_nocs_str = filtered_nocs_str.strip()
        if filtered_nocs_str.startswith('```python'):
            filtered_nocs_str = filtered_nocs_str.replace('```python', '').replace('```', '').strip()
        
        # Try parsing with Pydantic
        try:
            # First parse as Python literal
            parsed_list = ast.literal_eval(filtered_nocs_str)
            # Then validate with Pydantic
            validated_data = NOCRecommendationList(recommendations=[
                NOCRecommendation(**item) for item in parsed_list
            ])
            
            # Extract the validated list
            filtered_nocs_list_of_dicts = [
                dict(rec) for rec in validated_data.recommendations
            ]
            
            print(f"DEBUG: Successfully parsed NOCs: {filtered_nocs_list_of_dicts}")
            state["noc_codes"] = filtered_nocs_list_of_dicts
            
        except (SyntaxError, ValueError, TypeError) as parse_error:
            print(f"ERROR: Could not parse LLM output. Error: {parse_error}\nOutput: {filtered_nocs_str}")
            state["noc_codes"] = retrieved_nocs
            
    except Exception as e:
        print(f"ERROR during NOC filtering: {e}")
        state["noc_codes"] = retrieved_nocs

    return state


def calculate_crs_score(state):
    from datetime import datetime
    current_date = datetime.now()
    
    questionnaire = state["questionnaire"]
    

    
    prompt = ChatPromptTemplate.from_template(crs_calculation_prompt)
    chain = prompt | llm_crs_score | StrOutputParser()
    crs_score = chain.invoke({"questionnaire": questionnaire})
    print("DEBUG: Received CRS score in generate_roadmap:", crs_score)
    state["crs_score"] = crs_score
    return state

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
workflow.add_node("filter_feasible_nocs", filter_feasible_nocs) # Add the new node
workflow.add_node("calculate_crs_score", calculate_crs_score)
workflow.add_node("generate_roadmap", generate_roadmap)

# Define edges
workflow.set_entry_point("determine_job_roles")
workflow.add_edge("determine_job_roles", "retrieve_noc_codes")
workflow.add_edge("retrieve_noc_codes", "filter_feasible_nocs") # Edge to the filter node
workflow.add_edge("filter_feasible_nocs", "calculate_crs_score") # Edge from filter to CRS
workflow.add_edge("calculate_crs_score", "generate_roadmap")
workflow.add_edge("generate_roadmap", END)

# Compile the graph
graph_app = workflow.compile()