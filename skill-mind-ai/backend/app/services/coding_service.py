import ast
import subprocess
import sys
import tempfile
import os
import json
import random
from .ai_service import generate_coding_challenge_llm, generate_coding_challenges_batch_llm, HAS_AI
from ..models.models import AIChallenge, db

# ─────────────────────────────────────────────────────────────────────────────
# Dynamic Coding Challenges (100% AI Generated)
# ─────────────────────────────────────────────────────────────────────────────

PROBLEMS_BANK = [] # Legacy compatibility; now effectively disabled

# ─────────────────────────────────────────────────────────────────────────────
# Language Support
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES = {
    "python": {"name": "Python 3", "ext": "py", "comment": "#"},
    "javascript": {"name": "JavaScript", "ext": "js", "comment": "//"},
    "java": {"name": "Java", "ext": "java", "comment": "//"},
    "cpp": {"name": "C++", "ext": "cpp", "comment": "//"},
    "c": {"name": "C", "ext": "c", "comment": "/* */"},
    "sql": {"name": "SQL Query", "ext": "sql", "comment": "--"},
    "go": {"name": "Go", "ext": "go", "comment": "//"},
}

def detect_languages_from_skills(skills):
    """Detect programming languages from a list of skills."""
    skill_str = " ".join(skills).lower()
    detected = []
    
    mapping = {
        "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", "pytorch", "tensorflow"],
        "javascript": ["javascript", "js", "react", "node", "vue", "angular", "express", "nextjs", "typescript"],
        "java": ["java", "spring", "maven", "gradle", "android", "kotlin"],
        "cpp": ["c++", "cpp", "qt", "arduino"],
        "c": [" c ", "embedded c"],
        "sql": ["sql", "mysql", "postgres", "database", "oracle", "postgresql"],
        "go": ["go ", "golang"],
    }
    
    for lang, keywords in mapping.items():
        if any(kw in skill_str for kw in keywords):
            detected.append(lang)
            
    # Always include at least some defaults if none detected
    if not detected:
        detected = ["python", "javascript", "java"]
        
    # Standardize order and remove duplicates
    return list(dict.fromkeys(detected))

def get_starter_code(problem, language="python"):
    """Generate boilerplate starter code for a specific language."""
    title_snake = problem["title"].lower().replace(' ', '_')
    
    if language == "python":
        return problem.get("starter_code", f"def {title_snake}(*args):\n    # Write your solution here\n    pass\n")
    
    if language == "javascript":
        return f"function {title_snake}(...args) {{\n    // Write your solution here\n    return null;\n}}\n"
    
    if language == "java":
        return f"public class Solution {{\n    public Object {title_snake}(Object... args) {{\n        // Write your solution here\n        return null;\n    }}\n}}\n"
        
    if language == "cpp":
        return f"#include <iostream>\n#include <vector>\n\nclass Solution {{\npublic:\n    void {title_snake}() {{\n        // Write your solution here\n    }}\n}};\n"

    if language == "go":
        return f"package main\n\nfunc {title_snake}() {{\n    // Write your solution here\n}}\n"

    return problem.get("starter_code", "# Write your code here")


def get_all_problems(jd_text=None):
    """Return the list of all coding problems. Filter by JD and optionally generate one with AI."""
    problems = []
    jd_skills = []
    if jd_text:
        try:
            from ..services.resume_service import analyze_resume
            jd_analysis = analyze_resume(jd_text)
            jd_skills = jd_analysis.get('skills', [])
        except Exception:
            jd_skills = []

    # 1. Add static problems
    for p in PROBLEMS_BANK:
        match = False
        if jd_skills:
            for skill in jd_skills:
                if any(skill.lower() in t.lower() for t in p["tags"]):
                    match = True
                    break
        
        problems.append({
            "id": p["id"],
            "title": p["title"],
            "difficulty": p["difficulty"],
            "description": p["description"],
            "examples": p["examples"],
            "hints": p["hints"],
            "language": p.get("language", "python"),
            "starter_code": p["starter_code"],
            "is_recommended": match if jd_skills else False
        })
    
    # 2. Optionally generate a new AI challenge if Gemini is active
    if HAS_AI and jd_skills:
        try:
            ai_p = generate_coding_challenge_llm(jd_skills, jd_text)
            if ai_p:
                ai_p["id"] = 999  # Special ID for AI-generated problems
                ai_p["is_recommended"] = True
                problems.append(ai_p)
                PROBLEMS_BANK.append(ai_p)
        except Exception:
            pass
    
    # Sort: Recommended first
    if jd_skills:
        problems.sort(key=lambda x: x['is_recommended'], reverse=True)
    
    return problems


def get_challenge_set(jd_text=None, resume_data=None):
    """Return exactly 6 problems: 2 easy, 2 medium, 2 hard.
    Strictly prioritizes dynamic AI generation based on resume/JD.
    Persists AI problems to the database for future grading lookup."""
    selected_challenges = []
    user_id = resume_data.get('user_id') if resume_data else None
    
    # 1. Prepare context
    resume_text = resume_data.get('extracted_text', '') if resume_data else ''
    skills = resume_data.get('skills', []) if resume_data else []
    
    # 2. Try to get AI-generated challenges (Batch)
    if HAS_AI:
        difficulties = [("easy", 2), ("medium", 2), ("hard", 2)]
        
        for diff, target_count in difficulties:
            current_count = 0
            retries = 0
            max_retries = 2
            
            while current_count < target_count and retries < max_retries:
                try:
                    needed = target_count - current_count
                    
                    # Select languages for this batch
                    detected_langs = detect_languages_from_skills(skills)
                    batch_langs = []
                    for i in range(needed):
                        # Rotate through detected languages
                        batch_langs.append(detected_langs[(len(selected_challenges) + i) % len(detected_langs)])

                    ai_batch = generate_coding_challenges_batch_llm(
                        skills=skills, 
                        jd_text=jd_text, 
                        resume_text=resume_text, 
                        count=needed, 
                        difficulty=diff,
                        assigned_languages=batch_langs
                    )
                    
                    if not ai_batch:
                        retries += 1
                        continue

                    for p in ai_batch:
                        if current_count >= target_count:
                            break
                            
                        # Persist to database
                        new_challenge = AIChallenge(
                            user_id=user_id,
                            title=p.get('title', f'{diff.capitalize()} Coding Challenge'),
                            difficulty=p.get('difficulty', diff),
                            description=p.get('description', ''),
                            language=p.get('language', 'python'),
                            tags=p.get('tags', []),
                            starter_code=p.get('starter_code', ''),
                            test_cases=p.get('test_cases', []),
                            test_wrapper=p.get('test_wrapper', '')
                        )
                        db.session.add(new_challenge)
                        db.session.flush()
                        
                        p["id"] = new_challenge.id
                        p["is_ai"] = True
                        selected_challenges.append(p)
                        current_count += 1
                    
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"AI Generation failed for {diff} (Attempt {retries}): {e}")
                    retries += 1
        
        print(f"DEBUG: Successfully generated and persisted {len(selected_challenges)} AI challenges.")

    # 3. Handle Failure: No fallback to static bank allowed
    if len(selected_challenges) < 6:
        print("WARNING: AI Generation did not return 6 challenges. Attempting a single-question retry...")
        # (Optional: implement a final effort single-call retry if needed, 
        # but the logic below simply returns what was successfully made)

    # Detect appropriate languages for the UI
    detected_langs = detect_languages_from_skills(skills) if skills else ["python", "javascript"]
    
    return {
        "challenges": selected_challenges[:6],
        "languages": detected_langs
    }



def get_problem_by_id(problem_id):
    """Lookup challenge from dynamic database repository."""
    # 1. Try to find in the dynamic AI repository
    dynamic = AIChallenge.query.get(problem_id)
    if dynamic:
        return {
            "id": dynamic.id,
            "title": dynamic.title,
            "difficulty": dynamic.difficulty,
            "description": dynamic.description,
            "language": dynamic.language,
            "tags": dynamic.tags,
            "starter_code": dynamic.starter_code,
            "test_cases": dynamic.test_cases,
            "test_wrapper": dynamic.test_wrapper
        }
    
    # 2. Legacy fallback – but bank is now empty
    for p in PROBLEMS_BANK:
        if p["id"] == problem_id:
            return p
            
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Syntax & Quality Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_syntax(code, language='python'):
    """Check syntax for various languages using their respective parsers."""
    if language == 'python':
        try:
            ast.parse(code)
            return True, "Syntax is valid."
        except SyntaxError as e:
            return False, f"Syntax Error at line {e.lineno}: {e.msg}"
    
    # For others, use CLI check if available
    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{SUPPORTED_LANGUAGES.get(language, {}).get("ext", "txt")}', delete=False, encoding='utf-8') as f:
        f.write(code)
        tmp_path = f.name

    try:
        if language == 'javascript':
            proc = subprocess.run(['node', '--check', tmp_path], capture_output=True, text=True)
            if proc.returncode != 0:
                return False, proc.stderr.strip().split('\n')[0]
        elif language == 'java':
            # javac check is overkill but standard
            proc = subprocess.run(['javac', tmp_path], capture_output=True, text=True)
            if proc.returncode != 0:
                # Cleanup class file if generated
                if os.path.exists(tmp_path.replace('.java', '.class')):
                    os.unlink(tmp_path.replace('.java', '.class'))
                return False, proc.stderr.strip().split('\n')[0]
        elif language == 'go':
            # Go needs a package header even for syntax check
            check_script = f"package main\n{code}"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(check_script)
            proc = subprocess.run(['go', 'fmt', tmp_path], capture_output=True, text=True)
            if proc.returncode != 0:
                return False, proc.stderr.strip().split('\n')[0]
        elif language in ['c', 'cpp']:
            compiler = 'gcc' if language == 'c' else 'g++'
            proc = subprocess.run([compiler, '-fsyntax-only', tmp_path], capture_output=True, text=True)
            if proc.returncode != 0:
                return False, proc.stderr.strip().split('\n')[0]
        elif language == 'sql':
            import sqlite3
            try:
                conn = sqlite3.connect(":memory:")
                conn.execute(f"EXPLAIN {code}")
            except sqlite3.Error as e:
                return False, f"SQL Syntax Error: {str(e)}"
            finally:
                conn.close()
        
        return True, "Syntax is valid."
    except Exception as e:
        # Fallback heuristic: check for common keywords if tooling is missing
        keywords = {
            "python": ["def ", "import ", "print("],
            "javascript": ["function ", "const ", "let ", "console.log"],
            "java": ["public class ", "static void main", "System.out.print"],
            "cpp": ["#include", "int main(", "std::"],
            "c": ["#include", "int main("],
            "go": ["package ", "func "],
            "sql": ["SELECT ", "FROM ", "WHERE "]
        }
        
        target_keys = keywords.get(language, [])
        if any(k in code for k in target_keys):
            return True, "Syntax is valid (heuristic check)."
            
        return False, f"Syntax verification failed: Code does not appear to be valid {language}."
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def evaluate_code_quality(code, language='python', problem_title=None):
    """Evaluate code quality using language-specific analysis with a fair, flexible scoring system."""
    
    # 0. Language Identity Check
    if language in ['java', 'cpp', 'c', 'go', 'javascript']:
        python_telltales = ['def ', 'elif ', 'import pandas', 'print("'] 
        if any(tt in code for tt in python_telltales) and ':' in code:
            return {"score": 0, "feedback": f"Language mismatch detected.", "details": {"readability": 0, "efficiency": 0, "best_practices": 0}}
            
    # Heuristic metrics (0-100 scales)
    readability = 40
    efficiency = 50
    best_practices = 45
    
    # Check for keywords
    code_lower = code.lower()
    if 'import ' in code or 'include' in code: best_practices += 10
    if ('for ' in code or 'while ' in code) and ('if ' in code): efficiency += 10
    if len(code.split('\n')) > 15: readability += 10
    if '"""' in code or '/*' in code or '//' in code: readability += 15
    
    # Penalty for short code
    if len(code) < 50:
        readability = max(10, readability - 30)
        efficiency = max(10, efficiency - 30)
        
    score = round(readability * 0.3 + efficiency * 0.3 + best_practices * 0.4)
    
    return {
        "score": min(score, 100),
        "feedback": "Analysis based on structure and patterns.",
        "details": {
            "readability": min(readability, 100),
            "efficiency": min(efficiency, 100),
            "best_practices": min(best_practices, 100)
        }
    }

def get_ai_coding_analysis(code, language, problem, test_results):
    """Provides a deep AI-driven analysis of the code logic and test failures."""
    if not HAS_AI:
        return {
            "logic_overview": "AI analysis unavailable.",
            "bug_analysis": "Check test cases for details.",
            "suggestions": "Review standard language best practices."
        }

    # Prepare context for AI
    failed_tests = [t for t in test_results if not t['passed']]
    passed_count = len(test_results) - len(failed_tests)
    
    prompt = f"""
    Analyze this code submission for the problem: "{problem['title']}".
    Description: {problem['description']}
    Language: {language}
    
    Test Results: {passed_count} passed, {len(failed_tests)} failed.
    {f"Failed Details: {json.dumps(failed_tests[:2])}" if failed_tests else "All tests passed!"}
    
    Code:
    {code}
    
    Provide a "Perfect Analysis" in the following JSON format:
    {{
        "logic_overview": "A concise (2-3 sentences) explanation of the candidate's logical approach.",
        "bug_analysis": "If failed, explain the logical gap clearly. If passed, mention any subtle edge cases they handled well.",
        "suggestions": "3 specific, high-end refactoring tips or algorithmic improvements.",
        "complexity": {{ "time": "e.g. O(n)", "space": "e.g. O(1)" }}
    }}
    """
    
    from .ai_service import call_ai, clean_json_response
    response = call_ai(prompt, "You are a Senior Technical Architect providing mentor-level code reviews.", module='coding')
    return clean_json_response(response) or {
        "logic_overview": "Logic completed. See test results.",
        "bug_analysis": "No specific bugs identified beyond test failures.",
        "suggestions": ["Add comments", "Refactor loops", "Handle edge cases"]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Case Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_test_cases(code, problem_id, language='python'):
    """Run all test cases for a problem and return results with a logic score and execution time."""
    problem = get_problem_by_id(problem_id)
    if not problem:
        return [], 0, 0

    results = []
    total_similarity = 0
    import time
    start_time = time.time()

    for i, tc in enumerate(problem["test_cases"]):
        try:
            test_result = _run_single_test(code, problem, tc, i + 1, language)
            total_similarity += test_result.get("similarity", 0)
            results.append(test_result)
        except Exception as e:
            results.append({
                "test": i + 1,
                "passed": False,
                "error": f"Internal Runner Error: {str(e)}",
                "similarity": 0
            })

    total_cases = len(problem["test_cases"])
    test_score = round((total_similarity / total_cases) * 100) if total_cases > 0 else 0
    execution_time = round((time.time() - start_time) * 1000, 2) # in ms
    
    return results, test_score, execution_time

def calculate_comprehensive_score(test_score, quality_results, ai_analysis=None):
    """Calculates a weighted final score out of 100 based on Functionality (60%) and Quality (40%)."""
    quality_score = quality_results.get('score', 0)
    
    # Weighted calculation
    final = (test_score * 0.6) + (quality_score * 0.4)
    return round(final)


def _get_target_func_name(wrapper):
    """Extracts the function name being called in the test wrapper."""
    if not wrapper: return None
    import re
    # Look for name before ( in the expression part (after =)
    expr = wrapper.split('=')[-1]
    match = re.search(r'([\w\d_]+)\s*\(', expr)
    if match:
        return match.group(1)
    return None

def _run_single_test(code, problem, test_case, test_num, language='python'):
    """Execute one test case safely in a subprocess with stdout capture."""
    try:
        # 1. Prepare Input & Expected
        tc_input = test_case.get("input")
        if tc_input is None:
            alternative_data = {k: v for k, v in test_case.items() if k != "expected"}
            tc_input = list(alternative_data.values())[0] if len(alternative_data) == 1 else alternative_data
            
        expected = test_case.get("expected")
        expected_str = json.dumps(expected) if isinstance(expected, (list, dict)) else str(expected)
        
        # 2. Build Language-Specific Script
        script = ""
        run_cmd = []
        ext = SUPPORTED_LANGUAGES.get(language, {}).get("ext", "py")

        if language == 'python':
            run_cmd = [sys.executable]
            func_name = _get_func_name(code) or "solution"
            is_dict = isinstance(tc_input, dict)
            if is_dict:
                args_str = ", ".join([json.dumps(v) for v in tc_input.values()])
                call_line = f"result = {func_name}({args_str})"
            else:
                call_line = f"result = {func_name}({json.dumps(tc_input)})"
                
            script = f"""import json\nimport sys\n{code}\ntry:\n    {call_line}\n    print(json.dumps(result))\nexcept Exception as e:\n    print(json.dumps({{"__error__": str(e)}}))"""

        elif language == 'javascript':
            run_cmd = ['node']
            func_name = _get_func_name(code) or "solution"
            is_dict = isinstance(tc_input, dict)
            if is_dict:
                args_str = ", ".join([json.dumps(v) for v in tc_input.values()])
                call_line = f"const result = {func_name}({args_str});"
            else:
                call_line = f"const result = {func_name}({json.dumps(tc_input)});"
                
            script = f"""{code}\ntry {{\n    {call_line}\n    console.log(JSON.stringify(result));\n}} catch (e) {{\n    console.log(JSON.stringify({{"__error__": e.message}}));\n}}"""

        elif language == 'go':
            run_cmd = ['go', 'run']
            func_name = _get_func_name(code) or "solution"
            is_dict = isinstance(tc_input, dict)
            if is_dict:
                args_str = ", ".join([json.dumps(v) for v in tc_input.values()])
                call_line = f"result := {func_name}({args_str})"
            else:
                call_line = f"result := {func_name}({json.dumps(tc_input)})"
            
            script = f"""package main\nimport "encoding/json"\nimport "fmt"\n{code}\nfunc main() {{\n    {call_line}\n    out, _ := json.Marshal(result)\n    fmt.Println(string(out))\n}}"""

        else:
            # Fallback for others
            run_cmd = [sys.executable] if language == 'python' else ['node']
            script = code

        # 3. Execution
        with tempfile.NamedTemporaryFile(mode='w', suffix=f".{ext}", delete=False, encoding='utf-8') as f:
            f.write(script)
            tmp_path = f.name

        process = subprocess.run(run_cmd + [tmp_path], capture_output=True, text=True, timeout=10)
        if os.path.exists(tmp_path): os.unlink(tmp_path)

        # 4. stdout & Result Processing
        lines = [line for line in process.stdout.strip().split('\n') if line.strip()]
        eval_result = None
        user_stdout = []
        
        if lines:
            try:
                eval_result = json.loads(lines[-1])
                user_stdout = lines[:-1]
            except:
                eval_result = lines[-1]
                user_stdout = lines[:-1]

        if isinstance(eval_result, dict) and "__error__" in eval_result:
            return {
                "test": test_num, "passed": False, "input": str(tc_input),
                "expected": expected_str, "actual": "Runtime Error",
                "stdout": "\n".join(user_stdout), "error": eval_result.get("__error__")
            }

        actual_val = eval_result if eval_result is not None else "No Output"
        similarity = _calculate_similarity(actual_val, expected)
        passed = similarity >= 0.95
        actual_str = json.dumps(actual_val) if isinstance(actual_val, (list, dict)) else str(actual_val)

        return {
            "test": test_num, "passed": passed, "similarity": similarity,
            "input": str(tc_input), "expected": expected_str, "actual": actual_str[:500],
            "stdout": "\n".join(user_stdout),
            "error": None if passed else ("Partial match" if similarity > 0.1 else "Logic mismatch")
        }

    except Exception as e:
        return {
            "test": test_num, "passed": False, "input": "N/A", "expected": "N/A",
            "actual": "Execution Failed", "stdout": "", "error": str(e)[:500]
        }

def _get_func_name(code):
    """Helper to extract the first top-level function name from code."""
    try:
        tree = ast.parse(code)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                return node.name
    except:
        pass
    return None

def _calculate_similarity(actual, expected):
    """Calculate the similarity (0.0 to 1.0) between actual and expected logic."""
    if actual == expected: return 1.0
    
    # Try normalized string comparison
    if str(actual).strip() == str(expected).strip(): return 1.0
    
    try:
        # Handle Numbers
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if round(float(actual), 2) == round(float(expected), 2): return 1.0
            # Numerical closeness
            diff = abs(actual - expected)
            if expected != 0:
                rel = diff / abs(expected)
                return max(0, 1.0 - rel)
            return 0.0

        # Handle Dicts (Structural Similarity)
        if isinstance(actual, dict) and isinstance(expected, dict):
            if not actual and not expected: return 1.0
            if not actual or not expected: return 0.0
            
            # Key set similarity with Type Tolerance (match 1 to "1")
            norm_act = {str(k): k for k in actual.keys()}
            norm_exp = {str(k): k for k in expected.keys()}
            
            keys_act = set(norm_act.keys())
            keys_exp = set(norm_exp.keys())
            
            common_keys = keys_act.intersection(keys_exp)
            all_keys = keys_act.union(keys_exp)
            key_sim = len(common_keys) / len(all_keys) if all_keys else 0
            
            if not common_keys:
                return key_sim * 0.4
                
            # Value similarity for common keys (mapped back to original values)
            val_sim_sum = 0
            for k in common_keys:
                # Retrieve using the original key from the mapping
                val_sim_sum += _calculate_similarity(actual[norm_act[k]], expected[norm_exp[k]])
            
            val_sim = val_sim_sum / len(keys_exp)
            return (key_sim * 0.4) + (val_sim * 0.6)

        # Handle Lists/Tuples
        if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            if not actual and not expected: return 1.0
            if not actual or not expected: return 0.0
            
            # (Weights: 30% length, 70% elements)
            len_sim = 1.0 if len(actual) == len(expected) else max(0, 1.0 - abs(len(actual) - len(expected)) / len(expected))
            
            elem_sim_sum = 0
            min_len = min(len(actual), len(expected))
            for i in range(min_len):
                elem_sim_sum += _calculate_similarity(actual[i], expected[i])
            
            elem_sim = elem_sim_sum / len(expected)
            return (len_sim * 0.3) + (elem_sim * 0.7)

        # Normalized string comparison
        if str(actual).lower().strip() == str(expected).lower().strip():
            return 1.0
            
    except Exception:
        pass
    
    return 0.0
