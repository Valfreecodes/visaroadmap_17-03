class GraphState:
    def __init__(self, questionnaire: str, job_roles: str, noc_codes: str, crs_score: str, roadmap: str, age: int, education_level: str, first_language_scores: dict, second_language_scores: dict, canadian_work_exp: int, foreign_work_exp: int, certificate_qualification: bool, provincial_nomination: bool, arranged_employment: bool, canadian_education: str, sibling_in_canada: bool, spouse_factors: dict):
        self.questionnaire = questionnaire
        self.job_roles = job_roles
        self.noc_codes = noc_codes
        self.crs_score = crs_score
        self.roadmap = roadmap
        self.age = age
        self.education_level = education_level
        self.first_language_scores = first_language_scores
        self.second_language_scores = second_language_scores
        self.canadian_work_exp = canadian_work_exp
        self.foreign_work_exp = foreign_work_exp
        self.certificate_qualification = certificate_qualification
        self.provincial_nomination = provincial_nomination
        self.arranged_employment = arranged_employment
        self.canadian_education = canadian_education
        self.sibling_in_canada = sibling_in_canada
        self.spouse_factors = spouse_factors

    def update_state(self, feedback: dict):
        # Update the state based on user feedback
        for key, value in feedback.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_summary(self):
        return {
            "questionnaire": self.questionnaire,
            "job_roles": self.job_roles,
            "noc_codes": self.noc_codes,
            "crs_score": self.crs_score,
            "roadmap": self.roadmap,
            "age": self.age,
            "education_level": self.education_level,
            "first_language_scores": self.first_language_scores,
            "second_language_scores": self.second_language_scores,
            "canadian_work_exp": self.canadian_work_exp,
            "foreign_work_exp": self.foreign_work_exp,
            "certificate_qualification": self.certificate_qualification,
            "provincial_nomination": self.provincial_nomination,
            "arranged_employment": self.arranged_employment,
            "canadian_education": self.canadian_education,
            "sibling_in_canada": self.sibling_in_canada,
            "spouse_factors": self.spouse_factors,
        }