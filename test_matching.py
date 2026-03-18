
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'skill-mind-ai', 'backend')))
# Also add app directory
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'skill-mind-ai', 'backend', 'app')))

from app.services.ai_service import local_calculate_job_fit, local_extract_skills

resume = "I am a Python developer with experience in React and SQL."
jd = "Looking for a Python developer who knows React."

print("--- Testing local_extract_skills ---")
res_skills = local_extract_skills(resume)
jd_skills = local_extract_skills(jd)
print(f"Resume Skills: {res_skills}")
print(f"JD Skills: {jd_skills}")

print("\n--- Testing local_calculate_job_fit ---")
result = local_calculate_job_fit(resume, jd)
print(f"Result: {result}")


jd_no_skills = "Looking for a person who is hardworking and has great leadership."
print("\n--- Testing local_calculate_job_fit (JD No Skills) ---")
result_no_skills = local_calculate_job_fit(resume, jd_no_skills)
jd_python = "Looking for a Python expert."
print("\n--- Testing local_calculate_job_fit (JD Python) ---")
result_python = local_calculate_job_fit(resume, jd_python)
print(f"Result Python: {result_python}")
