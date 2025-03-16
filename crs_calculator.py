# def calculate_exact_crs_score(questionnaire_data):
#     """
#     Calculate CRS score based on official criteria
#     Expected questionnaire_data should be a dictionary with these keys:
#     - age: int
#     - education: str
#     - first_language: dict with 'speaking', 'listening', 'reading', 'writing' CLB levels
#     - work_experience: int (years)
#     - canadian_work_experience: int (years)
#     - education_in_canada: bool
#     - arranged_employment: bool
#     - provincial_nomination: bool
#     - spouse: bool
#     - spouse_education: str (if applicable)
#     - spouse_language: dict (if applicable)
#     - spouse_work_experience: int (if applicable)
#     """
#     score = 0
    
#     # Core / Human Capital Factors (max 460 points)
    
#     # Age (max 110 points)
#     age_points = {
#         18: 90, 19: 95, 20: 100, 21: 100, 22: 100, 23: 100, 24: 100, 25: 100, 26: 100, 27: 100, 
#         28: 100, 29: 100, 30: 95, 31: 90, 32: 85, 33: 80, 34: 75, 35: 70, 36: 65, 37: 60, 
#         38: 55, 39: 50, 40: 45, 41: 40, 42: 35, 43: 30, 44: 25, 45: 20, 46: 15, 47: 10, 48: 5, 49: 0
#     }
#     score += age_points.get(questionnaire_data['age'], 0)
#     if questionnaire_data.get('arranged_employment'):
#         score += 50
#     if questionnaire_data.get('education_in_canada'):
#         score += 30

#     # Canadian Work Experience
#     canadian_exp_points = {
#         1: 40, 2: 53, 3: 64, 4: 72, 5: 80
#     }
#     score += canadian_exp_points.get(min(questionnaire_data.get('canadian_work_experience', 0), 5), 0)

#     return score

# def calculate_crs_score(state):
#     questionnaire = state["questionnaire"]
    
#     # Extract detailed information from questionnaire using LLM
#     extract_data_prompt = """
#     Based on the questionnaire, extract the following information in a structured format:
    
#     1. Core/Human Capital Factors:
#     - Exact age
#     - Education level (be specific about years and type)
#     - First official language scores (CLB levels for reading, writing, speaking, listening)
#     - Second official language scores (if applicable)
#     - Canadian work experience (years)
    
#     2. Spouse Factors (if applicable):
#     - Education level
#     - Language scores
#     - Canadian work experience
    
#     3. Skill Transferability:
#     - Foreign work experience
#     - Canadian educational credentials
#     - Certificate of qualification (for trades)
    
#     4. Additional Points:
#     - Provincial nomination
#     - Arranged employment (specify NOC TEER)
#     - Canadian education
#     - French language ability
#     - Sibling in Canada
    
#     Questionnaire: {questionnaire}
    
#     Return the information in a clear, structured format.
#     """
    
#     # Use the existing crs_calculator.py functions
#     from crs_calculator import calculate_exact_crs_score, parse_questionnaire_input
    
#     # Get structured data from LLM
#     chain = ChatPromptTemplate.from_template(extract_data_prompt) | llm_crs_score | StrOutputParser()
#     structured_data = chain.invoke({"questionnaire": questionnaire})
    
#     # Parse the structured data
#     parsed_data = parse_questionnaire_input(structured_data)
    
#     # Calculate final score using the comprehensive criteria
#     final_score = calculate_exact_crs_score(parsed_data)
    
#     state["crs_score"] = str(final_score)
#     return state


# def parse_questionnaire_input():
#     """Helper function to gather and structure questionnaire data from user input"""
#     questionnaire_data = {}
    
#     questionnaire_data['age'] = int(input("Enter your age: "))
    
#     education_map = {
#         '1': 'secondary',
#         '2': 'one_year_degree',
#         '3': 'two_year_degree',
#         '4': 'three_year_degree',
#         '5': 'two_or_more_degrees',
#         '6': 'masters',
#         '7': 'phd'
#     }
#     print("\nSelect your highest level of education:")
#     print("1. Secondary diploma (high school)")
#     print("2. One-year degree/diploma/certificate")
#     print("3. Two-year program")
#     print("4. Bachelor's degree or three year program")
#     print("5. Two or more degrees (one being 3+ years)")
#     print("6. Master's degree")
#     print("7. Doctoral degree (Ph.D.)")
#     edu_choice = input("Enter the number of your choice: ")
#     questionnaire_data['education'] = education_map.get(edu_choice, 'secondary')

#     # Language scores
#     questionnaire_data['first_language'] = {}
#     print("\nEnter your CLB levels for first language (4-10):")
#     for skill in ['speaking', 'listening', 'reading', 'writing']:
#         questionnaire_data['first_language'][skill] = int(input(f"{skill.capitalize()}: "))

#     questionnaire_data['work_experience'] = int(input("\nEnter your years of work experience: "))
#     questionnaire_data['canadian_work_experience'] = int(input("Enter your years of Canadian work experience: "))
    
#     questionnaire_data['education_in_canada'] = input("\nDo you have education from Canada? (yes/no): ").lower() == 'yes'
#     questionnaire_data['arranged_employment'] = input("Do you have arranged employment in Canada? (yes/no): ").lower() == 'yes'
#     questionnaire_data['provincial_nomination'] = input("Do you have a provincial nomination? (yes/no): ").lower() == 'yes'

#     return questionnaire_data


#     print("Welcome to the CRS Calculator")
#     print("-----------------------------")
    
#     questionnaire_data = parse_questionnaire_input()
#     total_score = calculate_exact_crs_score(questionnaire_data)
    
#     print(f"\nYour estimated CRS score is: {total_score}")

# if __name__ == "__main__":
#     main()


from datetime import datetime, date

def calculate_age(birth_date_str):
    """
    Calculate age from birth date string (expected format: YYYY-MM-DD)
    """
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except ValueError:
        return None

def calculate_exact_crs_score(questionnaire_data):
    today = date.today()
    current_date = datetime.now()
    
    # If birth date is provided, calculate exact age
    birth_date = questionnaire_data.get('birth_date')
    if birth_date:
        age = calculate_age(birth_date)
        questionnaire_data['age'] = age
    
    # Add timestamp to the calculation
    questionnaire_data['calculation_date'] = current_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Rest of the CRS calculation logic...
    # [Previous implementation remains the same]

def calculate_crs_score(state):
    questionnaire = state["questionnaire"]
    current_date = datetime.now()
    
    # Update the extract data prompt to include birth date
    extract_data_prompt = ChatPromptTemplate.from_template("""
    Current Date: {current_date}
    
    Extract the following information from the questionnaire in a structured format:
    - Birth date (YYYY-MM-DD format)
    - Education level
    - Language test scores (CLB levels)
    - Years of work experience
    - Canadian work experience
    - Education in Canada (yes/no)
    - Arranged employment (yes/no)
    - Provincial nomination (yes/no)
    
    Also calculate:
    - Age as of {current_date}
    - Work experience duration up to {current_date}
    - Language test validity (tests should be less than 2 years old)
    
    Questionnaire: {questionnaire}
    """)
    
    chain = extract_data_prompt | llm_crs_score | StrOutputParser()
    structured_data = chain.invoke({
        "questionnaire": questionnaire,
        "current_date": current_date.strftime('%Y-%m-%d')
    })
    
    parsed_data = parse_llm_response(structured_data)
    exact_score = calculate_exact_crs_score(parsed_data)
    
    # Add calculation metadata
    state["crs_score"] = str(exact_score)
    state["score_calculation_date"] = current_date.strftime('%Y-%m-%d %H:%M:%S')
    return state

def parse_llm_response(structured_data: str) -> dict:
    """
    Parse the LLM's response and include date-based validations
    """
    current_date = datetime.now()
    parsed_data = {
        'calculation_timestamp': current_date.strftime('%Y-%m-%d %H:%M:%S'),
        'age': 0,
        'birth_date': None,
        'education_level': 'less_than_secondary',
        'first_language_scores': {'reading': 0, 'writing': 0, 'speaking': 0, 'listening': 0},
        'second_language_scores': {'reading': 0, 'writing': 0, 'speaking': 0, 'listening': 0},
        'canadian_work_experience': 0,
        'foreign_work_experience': 0,
        'canadian_education': '',
        'provincial_nomination': False,
        'arranged_employment': '',
        'sibling_in_canada': False,
        'language_test_dates': {
            'first_language': None,
            'second_language': None
        },
        'spouse_factors': {
            'education_level': 'less_than_secondary',
            'language_scores': {'reading': 0, 'writing': 0, 'speaking': 0, 'listening': 0},
            'canadian_work_experience': 0
        }
    }
    
    try:
        # Add date validation for language tests
        def is_test_valid(test_date_str):
            if not test_date_str:
                return False
            test_date = datetime.strptime(test_date_str, '%Y-%m-%d').date()
            today = date.today()
            test_age = (today - test_date).days / 365
            return test_age <= 2  # Tests must be less than 2 years old
        
        # Parse the structured data with date validations
        # [Your existing parsing logic here]
        
        # Validate work experience dates
        def calculate_work_experience(start_date_str, end_date_str=None):
            if not start_date_str:
                return 0
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else date.today()
            experience_years = (end_date - start_date).days / 365
            return min(max(0, round(experience_years)), 5)  # Cap at 5 years
            
        # Additional date-based validations can be added here
        
    except Exception as e:
        print(f"Error parsing questionnaire data: {e}")
        
    return parsed_data
