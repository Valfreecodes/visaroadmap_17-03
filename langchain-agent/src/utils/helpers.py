def validate_crs_score(score):
    if not isinstance(score, (int, float)):
        raise ValueError("CRS score must be a number.")
    if score < 0:
        raise ValueError("CRS score cannot be negative.")
    return True

def format_crs_score(score):
    return f"CRS Score: {score:.2f}"

def log_feedback(feedback):
    with open("feedback_log.txt", "a") as log_file:
        log_file.write(f"{feedback}\n")