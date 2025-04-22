import unittest
from src.agents.crs_agent import calculate_crs_score
from src.agents.interrupts.human_feedback import HumanFeedback

class TestCRSAgent(unittest.TestCase):

    def setUp(self):
        self.state = {
            "questionnaire": {
                "age": 30,
                "education_level": "Bachelor's",
                "first_language_scores": {"Listening": 8, "Reading": 7, "Writing": 7, "Speaking": 7},
                "canadian_work_exp": 2,
                "foreign_work_exp": 3,
                "spouse_factors": {"education_level": "Bachelor's", "language_scores": {"Listening": 8, "Reading": 7, "Writing": 7, "Speaking": 7}}
            }
        }
        self.human_feedback = HumanFeedback()

    def test_calculate_crs_score(self):
        score = calculate_crs_score(self.state)
        self.assertIsInstance(score, dict)
        self.assertIn("CRS Score", score)
        self.assertGreaterEqual(score["CRS Score"], 0)

    def test_human_feedback_interaction(self):
        score = calculate_crs_score(self.state)
        feedback = self.human_feedback.collect_feedback(score)
        self.assertIn("feedback", feedback)
        if feedback["feedback"] == "recalculate":
            new_score = self.human_feedback.recalculate_crs_score(self.state)
            self.assertIsInstance(new_score, dict)
            self.assertIn("CRS Score", new_score)

if __name__ == '__main__':
    unittest.main()