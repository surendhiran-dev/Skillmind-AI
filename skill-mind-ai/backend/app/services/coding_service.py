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
    # Always return the fixed set requested by the user
    return ["python", "javascript", "java", "cpp", "c", "sql"]

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
                    ai_batch = generate_coding_challenges_batch_llm(
                        skills=skills, 
                        jd_text=jd_text, 
                        resume_text=resume_text, 
                        count=needed, 
                        difficulty=diff
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
        return True, "Syntax check skipped (tooling missing)."
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def evaluate_code_quality(code):
    """Evaluate code quality using AST analysis with a fair, flexible scoring system."""
    tree = None
    try:
        tree = ast.parse(code)
    except Exception:
        return {"score": 0, "feedback": "Code cannot be parsed."}

    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    conditionals = [n for n in ast.walk(tree) if isinstance(n, ast.If)]
    returns = [n for n in ast.walk(tree) if isinstance(n, ast.Return)]

    # New base score (higher starting point for valid syntax)
    score = 45 
    feedback_parts = []

    if functions:
        score += 20
        feedback_parts.append(f"{len(functions)} function(s)")
    if loops or conditionals:
        score += 15
        feedback_parts.append("logic structures (loops/conditionals)")
    if returns:
        score += 5
        feedback_parts.append("return statements")
    
    lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
    if len(lines) > 5:
        score += 10
        feedback_parts.append("sufficient code length")

    # Reward docstrings specifically
    has_doc = False
    for func in functions:
        if (func.body and isinstance(func.body[0], ast.Expr)
                and isinstance(func.body[0].value, ast.Constant)
                and isinstance(func.body[0].value.value, str)):
            has_doc = True
            break
    if has_doc:
        score += 10
        feedback_parts.append("docstrings present")

    if classes:
        score += 5 # Optional bonus
        feedback_parts.append(f"{len(classes)} class(es)")

    # New Check: Triviality/Boilerplate detection
    # If no logic (loops/conditionals) and every function is just 'pass' or docstrings
    has_implementation = False
    if loops or conditionals:
        has_implementation = True
    else:
        for func in functions:
            # Look for nodes that aren't Pass, Expr (Docstrings), or simple return of default value
            body_logic = [n for n in func.body if not isinstance(n, (ast.Pass, ast.Expr))]
            if body_logic:
                has_implementation = True
                break
    
    if not has_implementation and not classes:
        score = 15 # Below 20 as requested for "default syntax"
        feedback = "Code quality: Default syntax/boilerplate submitted without implementation."
    else:
        feedback = ("Code quality: " + ", ".join(feedback_parts) + ".") if feedback_parts else "Basic code submitted."
        
    return {"score": min(score, 100), "feedback": feedback}


# ─────────────────────────────────────────────────────────────────────────────
# Test Case Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_test_cases(code, problem_id, language='python'):
    """
    Run the submitted code against all test cases for the given problem.
    """
    problem = get_problem_by_id(problem_id)
    if not problem:
        return [], 0

    is_valid, syntax_msg = check_syntax(code, language)
    if not is_valid:
        return [{"test": i + 1, "passed": False, "error": syntax_msg} for i in range(len(problem["test_cases"]))], 0

    results = []
    passed = 0

    for i, tc in enumerate(problem["test_cases"]):
        test_result = _run_single_test(code, problem, tc, i + 1, language)
        if test_result["passed"]:
            passed += 1
        results.append(test_result)

    total = len(problem["test_cases"])
    score = round((passed / total) * 100) if total > 0 else 0
    return results, score


def _run_single_test(code, problem, test_case, test_num, language='python'):
    """
    Execute one test case safely in a subprocess.
    """
    # 1. Prepare Input for Script
    # Resilience: Handle cases where the AI uses a semantic key instead of "input"
    tc_input = test_case.get("input")
    if tc_input is None:
        # Fallback: find the first key that isn't "expected"
        alternative_keys = [k for k in test_case.keys() if k != "expected"]
        if alternative_keys:
            tc_input = test_case[alternative_keys[0]]
        else:
            tc_input = {} # Truly empty input
            
    expected = test_case.get("expected")
    input_str = json.dumps(tc_input)
    
    # 2. Build Language-Specific Script
    title_snake = problem["title"].lower().replace(' ', '_')
    script = ""
    run_cmd = []
    ext = SUPPORTED_LANGUAGES.get(language, {}).get("ext", "py")

    if language == 'python':
        if isinstance(tc_input, dict):
            # Check if wrapper is compatible with the input keys
            try:
                call_line = problem["test_wrapper"].format(**{k: json.dumps(v) for k, v in tc_input.items()})
                
                # HEURISTIC: If wrapper uses '.' but user didn't define that class, it's likely a Java remnant
                if "." in call_line.split('=')[-1] and "(" in call_line:
                    found_func = _get_func_name(code)
                    if found_func and found_func not in call_line:
                        raise ValueError("Wrapper likely language-mismatched")
            except (KeyError, ValueError):
                # Fallback: find the first function defined in the code and use it
                func_name = _get_func_name(code) or problem["title"].lower().replace(' ', '_')
                args_str = ", ".join([json.dumps(v) for v in tc_input.values()])
                call_line = f"result = {func_name}({args_str})"
        else:
            try:
                call_line = problem["test_wrapper"].format(input=json.dumps(tc_input))
                if "." in call_line.split('=')[-1] and "(" in call_line:
                    found_func = _get_func_name(code)
                    if found_func and found_func not in call_line:
                        raise ValueError("Wrapper likely language-mismatched")
            except (KeyError, ValueError):
                func_name = _get_func_name(code) or problem["title"].lower().replace(' ', '_')
                call_line = f"result = {func_name}({json.dumps(tc_input)})"
            
        script = f"""
import json
import sys

{code}

# Ensure result is defined even if execution fails
result = "__not_computed__"
try:
    {call_line}
    # Special normalization for floats/lists
    def normalize_json(obj):
        if isinstance(obj, float): return round(obj, 2)
        if isinstance(obj, dict): return {{k: normalize_json(v) for k, v in obj.items()}}
        if isinstance(obj, list): return [normalize_json(v) for v in obj]
        return obj
    
    print(json.dumps(normalize_json(result)))
except Exception as e:
    print(json.dumps({{"__error__": str(e)}}))
"""
        run_cmd = [sys.executable]

    elif language == 'javascript':
        # Translate Python test_wrapper to JS
        if "result = sorted(" in problem["test_wrapper"]:
            call_js = problem["test_wrapper"].replace("result = sorted(", "let result = (")
        else:
            call_js = problem["test_wrapper"].replace("result = ", "let result = ")
        
        # Handle dict inputs for JS
        if isinstance(tc_input, dict):
            call_js = call_js.format(**{k: json.dumps(v) for k, v in tc_input.items()})
        else:
            call_js = call_js.format(input=json.dumps(tc_input))
            
        script = f"""
{code}
try {{
    {call_js}
    console.log(JSON.stringify(result));
}} catch (e) {{
    console.log(JSON.stringify({{"__error__": e.message}}));
}}
"""
        run_cmd = ['node']

    elif language == 'go':
        if "result = sorted(" in problem["test_wrapper"]:
            call_go = problem["test_wrapper"].replace("result = sorted(", "result := (")
        else:
            call_go = problem["test_wrapper"].replace("result = ", "result := ")

        if isinstance(tc_input, dict):
            call_go = call_go.format(**{k: json.dumps(v) for k, v in tc_input.items()})
        else:
            call_go = call_go.format(input=json.dumps(tc_input))

        script = f"""package main\nimport "encoding/json"\nimport "fmt"\n{code}\nfunc main() {{\n    {call_go}\n    out, _ := json.Marshal(result)\n    fmt.Println(string(out))\n}}"""
        run_cmd = ['go', 'run']

    elif language in ['c', 'cpp']:
        ext = 'c' if language == 'c' else 'cpp'
        compiler = 'gcc' if language == 'c' else 'g++'
        main_file = "SolutionTest"
        
        # Simplified wrapper for C/C++ (assumes user provides logic in class/function)
        script = f"""
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <nlohmann/json.hpp> // Assuming json library though it might not be there 
// (Fallback to primitive prints for demo)

{code}

int main() {{
    // Placeholder for actual test execution
    std::cout << "SUCCESS" << std::endl; 
    return 0;
}}
"""
        run_cmd = [compiler]

    elif language == 'sql':
        import sqlite3
        try:
            conn = sqlite3.connect(":memory:")
            # For SQL, we just execute the code and return results
            cursor = conn.cursor()
            cursor.execute(code)
            result = cursor.fetchall()
            
            # Simple result normalization for comparison
            actual = result[0][0] if len(result) == 1 and len(result[0]) == 1 else result
            
            passed = str(actual) == str(expected) or actual == expected
            return {
                "test": test_num, "passed": passed, "input": str(tc_input),
                "expected": str(expected), "actual": str(actual), "error": None,
            }
        except Exception as e:
            return {"test": test_num, "passed": False, "error": f"SQL Error: {str(e)}"}
        finally:
            conn.close()

    elif language == 'java':
        class_name = "SolutionTest"
        # Java is tricky because it needs a predefined class structure
        # We assume the user provided a class 'Solution' or equivalent
        call_java = problem["test_wrapper"].replace("result = sorted(", "Object result = ").replace("result = ", "Object result = ")
        if isinstance(tc_input, dict):
            call_java = call_java.format(**{k: json.dumps(v) for k, v in tc_input.items()})
        else:
            call_java = call_java.format(input=json.dumps(tc_input))

        script = f"""
import java.util.*;

{code}

public class {class_name} {{
    public static void main(String[] args) {{
        try {{
            Solution sol = new Solution();
            {call_java}
            // Simple stringification for comparison
            System.out.println(result.toString());
        }} catch (Exception e) {{
            System.out.println("{{\\\"__error\\\": \\\"" + e.getMessage() + "\\\"}}");
        }}
    }}
}}
"""
        run_cmd = ['java', tmp_path] # Java needs more complex setup usually, Simplified here.
        # Actually Java needs .java file matching public class name
        ext = "java"

    # 3. Execution
    try:
        suffix = f".{ext}"
        # Special case for Java: file name must match class name
        if language == 'java':
            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, f"{class_name}.java")
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(script)
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
                f.write(script)
                tmp_path = f.name

        if language == 'java':
            # Compile first
            compile_proc = subprocess.run(['javac', tmp_path], capture_output=True, text=True, timeout=10)
            if compile_proc.returncode != 0:
                os.unlink(tmp_path)
                return {"test": test_num, "passed": False, "error": "Compilation Error: " + compile_proc.stderr.strip()}
            
            # Use java -cp to run
            run_cmd = ['java', '-cp', tempfile.gettempdir(), class_name]
        else:
            run_cmd.append(tmp_path)

        proc = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        # Cleanup
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        if language == 'java':
            class_file = tmp_path.replace('.java', '.class')
            if os.path.exists(class_file): os.unlink(class_file)

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        
        if not stdout:
            return {
                "test": test_num,
                "passed": False,
                "input": str(tc_input),
                "expected": str(expected),
                "actual": f"No output. {f'Error: {stderr[:200]}' if stderr else ''}",
                "error": stderr[:200] if stderr else "Empty output",
            }

        # Attempt to parse json for consistency, fallback to raw
        try:
            actual = json.loads(stdout)
        except:
            actual = stdout

        if isinstance(actual, dict) and "__error__" in actual:
            return {
                "test": test_num,
                "passed": False,
                "input": str(tc_input),
                "expected": str(expected),
                "actual": "Runtime Error",
                "error": actual["__error__"][:500],
            }

        passed = _is_equivalent(actual, expected)
        return {
            "test": test_num,
            "passed": passed,
            "input": str(tc_input),
            "expected": str(expected),
            "actual": str(actual)[:500],
            "error": None if passed else "Logic mismatch",
        }

    except Exception as e:
        return {
            "test": test_num,
            "passed": False,
            "input": str(tc_input),
            "expected": str(expected),
            "actual": "Execution Failed",
            "error": str(e)[:500]
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

def _is_equivalent(actual, expected):
    """Check for logical equivalence between outputs (handles types and float rounding)."""
    if actual == expected: return True
    
    # Try normalized string comparison
    if str(actual).strip() == str(expected).strip(): return True
    
    # Try JSON/Float normalization comparison
    try:
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return round(float(actual), 2) == round(float(expected), 2)
        
        # Handle dicts with different key orders
        if isinstance(actual, dict) and isinstance(expected, dict):
            return actual == expected
    except:
        pass
    
    return False
