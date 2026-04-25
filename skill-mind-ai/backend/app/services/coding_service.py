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
                            
                        # Persist to database — store func_name in test_wrapper for retrieval
                        func_name_hint = p.get('func_name', '')
                        new_challenge = AIChallenge(
                            user_id=user_id,
                            title=p.get('title', f'{diff.capitalize()} Coding Challenge'),
                            difficulty=p.get('difficulty', diff),
                            description=p.get('description', ''),
                            language=p.get('language', 'python'),
                            tags=p.get('tags', []),
                            starter_code=p.get('starter_code', ''),
                            test_cases=p.get('test_cases', []),
                            test_wrapper=func_name_hint  # repurposed: stores the expected function name
                        )
                        db.session.add(new_challenge)
                        db.session.flush()
                        
                        p["id"] = new_challenge.id
                        p["is_ai"] = True
                        p["func_name"] = func_name_hint  # keep it in memory too
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
            "func_name": dynamic.test_wrapper or "",  # test_wrapper repurposed to store func_name
            "test_wrapper": dynamic.test_wrapper or ""
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
    tmp_path = None
    if language == 'python':
        try:
            ast.parse(code)
            return True, "Syntax is valid."
        except SyntaxError as e:
            return False, f"error in line {e.lineno}: syntax error ({e.msg})"
        except Exception as e:
            return False, f"error in line unknown: syntax error ({str(e)})"
    
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
        error_msg = str(e)
        line_no = "unknown"
        if "line " in error_msg:
            import re
            match = re.search(r'line (\d+)', error_msg)
            if match: line_no = match.group(1)
            
        return False, f"error in line {line_no}: syntax error ({error_msg})"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def evaluate_code_quality(code, language='python', problem_title=None):
    """Evaluate code quality using language-specific analysis. AST-based for Python."""
    
    # Language Identity Check: penalize obvious wrong-language submissions
    if language in ['java', 'cpp', 'c', 'go', 'javascript']:
        python_telltales = ['def ', 'elif ', 'import pandas', '    pass']
        if sum(1 for tt in python_telltales if tt in code) >= 2:
            return {"score": 0, "feedback": "Language mismatch detected.",
                    "details": {"readability": 0, "efficiency": 0, "best_practices": 0}}
    
    readability = 0
    efficiency = 0
    best_practices = 0

    if language == 'python':
        try:
            tree = ast.parse(code)
            lines = code.split('\n')
            non_blank = [l for l in lines if l.strip()]
            
            # Readability: docstrings, comments, line count
            has_docstring = any(
                isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                for n in ast.walk(tree)
            )
            comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
            readability += 30 if has_docstring else 0
            readability += min(20, comment_lines * 5)
            readability += 20 if len(non_blank) >= 5 else 10
            readability += 15 if len(non_blank) >= 15 else 0
            readability = min(readability, 85)  # cap, never perfect without docs
            
            # Efficiency: use of built-ins, comprehensions, avoid O(n^2) antipatterns
            func_calls = [n.func.id if isinstance(n.func, ast.Name) else '' for n in ast.walk(tree) if isinstance(n, ast.Call)]
            builtin_usage = sum(1 for f in func_calls if f in ['map', 'filter', 'sorted', 'enumerate', 'zip', 'any', 'all', 'sum', 'max', 'min'])
            list_comps = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)))
            # Nested loops check (rough heuristic)
            loop_depth_penalty = 0
            for_loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
            if len(for_loops) >= 3:
                loop_depth_penalty = 10
            
            efficiency = 50 + min(30, builtin_usage * 8 + list_comps * 10) - loop_depth_penalty
            efficiency = max(20, min(efficiency, 90))

            # Best Practices: imports, type hints, returns
            has_imports = any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree))
            func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            has_type_hints = any(n.returns is not None or any(a.annotation for a in n.args.args) for n in func_defs)
            has_early_return = any(
                isinstance(n, ast.Return) and n.value is not None
                for n in ast.walk(tree)
            )
            best_practices = 40
            best_practices += 15 if has_imports else 0
            best_practices += 25 if has_type_hints else 0
            best_practices += 15 if has_early_return else 0
            best_practices = min(best_practices, 90)

        except SyntaxError:
            # Code has syntax errors — minimal quality
            return {"score": 5, "feedback": "Code has syntax errors.",
                    "details": {"readability": 5, "efficiency": 5, "best_practices": 5}}

    else:
        # Non-Python: heuristic based on keywords and structure
        lines = code.split('\n')
        non_blank = [l for l in lines if l.strip()]
        code_lower = code.lower()
        
        readability = 40
        efficiency = 50
        best_practices = 45
        
        if len(non_blank) > 10: readability += 15
        if '//' in code or '/*' in code: readability += 20  # comments
        if 'import ' in code or '#include' in code or 'package ' in code: best_practices += 15
        if 'try' in code_lower and ('catch' in code_lower or 'except' in code_lower): best_practices += 15
        if len(code) < 50:
            readability = max(10, readability - 30)
            efficiency = max(10, efficiency - 20)

        readability = min(readability, 85)
        efficiency = min(efficiency, 85)
        best_practices = min(best_practices, 85)

    score = round(readability * 0.3 + efficiency * 0.35 + best_practices * 0.35)
    return {
        "score": min(score, 100),
        "feedback": "Analysis based on code structure, patterns, and language idioms.",
        "details": {
            "readability": int(readability),
            "efficiency": int(efficiency),
            "best_practices": int(best_practices)
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
    """Calculates a weighted final score out of 100 based on Functionality (80%) and Quality (20%).
    Prioritizes test_score for marking."""
    quality_score = quality_results.get('score', 0)
    
    # Weighted calculation (Functionality is now 80%)
    final = (test_score * 0.8) + (quality_score * 0.2)
    return round(final)


def _get_func_name(code, problem_title=None, func_name_hint=None):
    """Extract the most likely main function name from code.
    Prioritizes: explicit hint > title match > common names > last defined."""
    # 1. Use explicit hint from AI-generated problem metadata
    if func_name_hint and func_name_hint.strip():
        return func_name_hint.strip()
    
    try:
        tree = ast.parse(code)
        functions = [
            node for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')
        ]
        
        if not functions:
            return None
        
        # 2. Match problem title (snake_case)
        if problem_title:
            title_snake = problem_title.lower().replace(' ', '_').replace('-', '_')
            # Also try partial match
            for f in functions:
                if f.name.lower() == title_snake or title_snake in f.name.lower():
                    return f.name
        
        # 3. Common solution function names
        for name in ['solution', 'solve', 'main_logic', 'main', 'process', 'calculate', 'compute', 'run']:
            for f in functions:
                if f.name.lower() == name:
                    return f.name
        
        # 4. Prefer the LAST defined top-level function (pattern: helpers first, main last)
        return functions[-1].name
    except:
        pass
    return None


def _normalize_output(val, expected=None):
    """Normalize output for fair comparison: strip strings, coerce numeric strings, fix booleans."""
    if isinstance(val, str):
        stripped = val.strip()
        # Boolean string coercion
        if stripped.lower() == 'true': return True
        if stripped.lower() == 'false': return False
        # Numeric coercion if expected is numeric
        if expected is not None and isinstance(expected, (int, float)):
            try:
                return int(stripped) if isinstance(expected, int) else float(stripped)
            except ValueError:
                pass
        return stripped
    return val


def _calculate_similarity(actual, expected):
    """Calculate the similarity (0.0 to 1.0) between actual and expected."""
    # Normalize both values first
    actual = _normalize_output(actual, expected)
    if isinstance(expected, str):
        expected = _normalize_output(expected)

    # Exact equality
    if actual == expected: return 1.0

    # Normalized string equality (case-insensitive, whitespace-stripped)
    if str(actual).lower().strip() == str(expected).lower().strip(): return 1.0

    try:
        # ── Numbers ─────────────────────────────────────────────────────────────
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if round(float(actual), 4) == round(float(expected), 4): return 1.0
            diff = abs(float(actual) - float(expected))
            denom = abs(float(expected)) if expected != 0 else 1.0
            return max(0.0, 1.0 - diff / denom)

        # ── Dicts ────────────────────────────────────────────────────────────────
        if isinstance(actual, dict) and isinstance(expected, dict):
            if not actual and not expected: return 1.0
            if not actual or not expected: return 0.0
            norm_act = {str(k): k for k in actual}
            norm_exp = {str(k): k for k in expected}
            common = set(norm_act) & set(norm_exp)
            all_keys = set(norm_act) | set(norm_exp)
            key_sim = len(common) / len(all_keys) if all_keys else 0
            if not common: return key_sim * 0.4
            val_sim = sum(_calculate_similarity(actual[norm_act[k]], expected[norm_exp[k]]) for k in common) / len(norm_exp)
            return (key_sim * 0.4) + (val_sim * 0.6)

        # ── Lists / Tuples ───────────────────────────────────────────────────────
        if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
            if not actual and not expected: return 1.0
            if not actual or not expected: return 0.0

            # Strategy A: order-sensitive element comparison
            len_sim = 1.0 if len(actual) == len(expected) else max(0, 1.0 - abs(len(actual) - len(expected)) / max(len(expected), 1))
            min_len = min(len(actual), len(expected))
            elem_sim = sum(_calculate_similarity(actual[i], expected[i]) for i in range(min_len)) / max(len(expected), 1)
            ordered_score = (len_sim * 0.3) + (elem_sim * 0.7)

            # Strategy B: order-independent (set-like)
            try:
                act_sorted = sorted(str(x) for x in actual)
                exp_sorted = sorted(str(x) for x in expected)
                unordered_score = 0.9 if act_sorted == exp_sorted else 0.0
            except Exception:
                unordered_score = 0.0

            return max(ordered_score, unordered_score)

    except Exception:
        pass

    return 0.0



# ─────────────────────────────────────────────────────────────────────────────
# Language Literal Helpers (Go & Java type-aware argument generation)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_go_signature(code, func_name):
    """Return list of Go parameter types for func_name, e.g. ['[]int', 'int']."""
    import re
    pattern = rf'func\s+{re.escape(func_name)}\s*\(([^)]*)\)'
    m = re.search(pattern, code)
    if not m:
        return []
    params_str = m.group(1).strip()
    if not params_str:
        return []
    # Handle "a, b int" grouped style and "a int, b string" individual style
    types = []
    parts = [p.strip() for p in params_str.split(',')]
    pending = []
    for part in parts:
        tokens = part.split()
        if len(tokens) == 1:
            pending.append(tokens[0])         # name only — type comes later
        elif len(tokens) >= 2:
            go_type = ' '.join(tokens[1:])   # e.g. "[]int", "int", "string"
            for _ in pending:
                types.append(go_type)
            pending.clear()
            types.append(go_type)
    return types


def _to_go_literal(val, go_type=None):
    """Convert a Python value to a valid Go literal string using type hint."""
    import json as _json
    if val is None:
        return "nil"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return str(val)
    if isinstance(val, str):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    if isinstance(val, list):
        if not val:
            elem = go_type[2:] if go_type and go_type.startswith("[]") else "int"
            return f"[]{elem}{{}}"
        elem_type = go_type[2:] if (go_type and go_type.startswith("[]")) else None
        # Auto-detect element type from values if not provided
        if elem_type is None:
            if all(isinstance(x, bool) for x in val): elem_type = "bool"
            elif all(isinstance(x, int) for x in val): elem_type = "int"
            elif all(isinstance(x, float) for x in val): elem_type = "float64"
            elif all(isinstance(x, str) for x in val): elem_type = "string"
            elif all(isinstance(x, list) for x in val):
                # Nested — detect inner type
                inner_elem = None
                if val and val[0]:
                    if all(isinstance(x, int) for x in val[0]): inner_elem = "int"
                    elif all(isinstance(x, str) for x in val[0]): inner_elem = "string"
                elem_type = f"[]{inner_elem or 'interface{}'}"
            else:
                elem_type = "interface{}"
        items = ", ".join(_to_go_literal(x, elem_type) for x in val)
        return f"[]{elem_type}{{{items}}}"
    if isinstance(val, dict):
        return "nil"  # maps need explicit key/val types; skip for now
    return str(val)


def _parse_java_signature(code, method_name):
    """Return list of Java parameter types for method_name, e.g. ['int[]', 'int']."""
    import re
    pattern = rf'[\w<>\[\]]+\s+{re.escape(method_name)}\s*\(([^)]*)\)'
    m = re.search(pattern, code)
    if not m:
        return []
    params_str = m.group(1).strip()
    if not params_str:
        return []
    types = []
    for part in params_str.split(','):
        tokens = part.strip().split()
        if len(tokens) >= 2:
            types.append(' '.join(tokens[:-1]))   # everything except last token (param name)
    return types


def _to_java_literal(val, java_type=None):
    """Convert a Python value to a valid Java literal string using type hint."""
    import json as _json
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        if java_type in ("long", "Long"): return f"{val}L"
        return str(val)
    if isinstance(val, float):
        if java_type in ("float", "Float"): return f"{val}f"
        return str(val)
    if isinstance(val, str):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    if isinstance(val, list):
        if not val:
            elem = java_type[:-2] if (java_type and java_type.endswith("[]")) else "int"
            return f"new {elem}[]{{}}"
        elem_type = java_type[:-2] if (java_type and java_type.endswith("[]")) else None
        if elem_type is None:
            if all(isinstance(x, bool) for x in val): elem_type = "boolean"
            elif all(isinstance(x, int) for x in val): elem_type = "int"
            elif all(isinstance(x, float) for x in val): elem_type = "double"
            elif all(isinstance(x, str) for x in val): elem_type = "String"
            elif all(isinstance(x, list) for x in val):
                # 2D array
                inner = None
                if val and val[0]:
                    if all(isinstance(x, int) for x in val[0]): inner = "int"
                    elif all(isinstance(x, str) for x in val[0]): inner = "String"
                elem_type = f"{inner or 'Object'}[]"
            else:
                elem_type = "Object"
        # Nested list (2D array like int[][])
        if elem_type.endswith("[]"):
            inner_type = elem_type[:-2]
            items = ", ".join(_to_java_literal(x, inner_type + "[]") for x in val)
            return f"new {elem_type}{{{items}}}"
        items = ", ".join(_to_java_literal(x, elem_type) for x in val)
        return f"new {elem_type}[]{{{items}}}"
    return str(val)


def _run_single_test(code, problem, test_case, test_num, language='python'):
    """Execute one test case safely in a subprocess with full stdout/stderr capture."""
    import re as _re
    tmp_path = None
    tmp_dir = None

    try:
        # ── 1. Resolve Arguments ────────────────────────────────────────────────
        expected = test_case.get("expected")
        expected_str = json.dumps(expected) if isinstance(expected, (list, dict, bool)) else str(expected)

        # Primary: new "args" format (always a list of positional arguments)
        if "args" in test_case:
            args_list = test_case["args"]
            if not isinstance(args_list, list):
                args_list = [args_list]
        else:
            # Legacy fallback: "input" key
            tc_input = test_case.get("input")
            if tc_input is None:
                # Pull first non-expected key
                alt = {k: v for k, v in test_case.items() if k != "expected"}
                tc_input = list(alt.values())[0] if len(alt) == 1 else alt
            args_list = tc_input if isinstance(tc_input, list) else [tc_input]

        input_display = json.dumps(args_list)

        # ── 2. Get function name hint ───────────────────────────────────────────
        func_name_hint = problem.get('func_name', '') or problem.get('test_wrapper', '')

        # ── 3. Build language-specific script ──────────────────────────────────
        ext = SUPPORTED_LANGUAGES.get(language, {}).get("ext", "py")
        script = ""
        run_cmd = []

        # ────────────────── PYTHON ─────────────────────────────────────────────
        if language == 'python':
            run_cmd = [sys.executable]
            func_name = _get_func_name(code, problem.get('title'), func_name_hint) or "solution"

            # Build call: check actual function signature to decide unpacking
            call_line = None
            try:
                tree = ast.parse(code)
                func_def = next(
                    (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func_name),
                    None
                )
                n_params = len(func_def.args.args) if func_def else 0
                has_vararg = func_def.args.vararg is not None if func_def else False

                if isinstance(args_list, list) and (n_params == len(args_list) or has_vararg):
                    args_str = ", ".join(json.dumps(a) for a in args_list)
                    call_line = f"result = {func_name}({args_str})"
                elif isinstance(args_list, dict):
                    args_str = ", ".join(json.dumps(v) for v in args_list.values())
                    call_line = f"result = {func_name}({args_str})"
                else:
                    call_line = f"result = {func_name}({json.dumps(args_list[0] if len(args_list)==1 else args_list)})"
            except Exception:
                arg_repr = ", ".join(json.dumps(a) for a in args_list) if isinstance(args_list, list) else json.dumps(args_list)
                call_line = f"result = {func_name}({arg_repr})"

            script = (
                "import json, sys\n"
                f"{code}\n"
                "try:\n"
                f"    {call_line}\n"
                '    print("__RESULT__:" + json.dumps(result))\n'
                "except Exception as e:\n"
                '    import traceback\n'
                '    print("__RESULT__:" + json.dumps({"__error__": str(e), "__trace__": traceback.format_exc()}))\n'
            )

        # ────────────────── JAVASCRIPT ─────────────────────────────────────────
        elif language == 'javascript':
            run_cmd = ['node']
            # Detect: named function, arrow assigned to const/let/var, or method
            js_patterns = [
                _re.search(r'function\s+([\w$]+)\s*\(', code),
                _re.search(r'(?:const|let|var)\s+([\w$]+)\s*=\s*(?:\(|[\w$]+\s*=>)', code),
                _re.search(r'(?:const|let|var)\s+([\w$]+)\s*=\s*function', code),
            ]
            js_match = next((m for m in js_patterns if m), None)
            func_name = (func_name_hint if (func_name_hint and func_name_hint in code)
                         else (js_match.group(1) if js_match else "solution"))
            args_str = ", ".join(json.dumps(a) for a in args_list)
            script = (
                f"{code}\n"
                "try {\n"
                f"    const __result__ = {func_name}({args_str});\n"
                '    console.log("__RESULT__:" + JSON.stringify(__result__));\n'
                "} catch (e) {\n"
                '    console.log("__RESULT__:" + JSON.stringify({"__error__": e.message, "__stack__": e.stack}));\n'
                "}\n"
            )

        # ────────────────── GO ─────────────────────────────────────────────────
        elif language == 'go':
            run_cmd = ['go', 'run']

            # Detect func name (skip 'main')
            all_go_funcs = _re.findall(r'func\s+([\w\d_]+)\s*\(', code)
            non_main_funcs = [f for f in all_go_funcs if f != 'main']
            func_name = (func_name_hint if (func_name_hint and func_name_hint in code)
                         else (non_main_funcs[0] if non_main_funcs else 'Solution'))

            # Parse Go function signature to get typed parameter list
            go_param_types = _parse_go_signature(code, func_name)

            # Convert each arg to a proper Go literal using the parsed types
            go_args = []
            for i, arg in enumerate(args_list):
                go_type = go_param_types[i] if i < len(go_param_types) else None
                go_args.append(_to_go_literal(arg, go_type))
            args_str = ", ".join(go_args)

            # Inject package + required imports if missing
            header_lines = []
            if "package main" not in code:
                header_lines.append("package main")
            missing_imports = []
            if '"encoding/json"' not in code: missing_imports.append('"encoding/json"')
            if '"fmt"' not in code: missing_imports.append('"fmt"')
            if missing_imports:
                header_lines.append("import (\n" + "\n".join(f"    {i}" for i in missing_imports) + "\n)")
            header = "\n".join(header_lines) + ("\n" if header_lines else "")

            script = (
                f"{header}{code}\n"
                "func main() {\n"
                f"    result := {func_name}({args_str})\n"
                "    out, _ := json.Marshal(result)\n"
                '    fmt.Println("__RESULT__:" + string(out))\n'
                "}\n"
            )

        # ────────────────── JAVA ───────────────────────────────────────────────
        elif language == 'java':
            import tempfile as _tf, shutil as _shutil
            tmp_dir = _tf.mkdtemp()

            # Remove 'public' from user's class to allow it to be embedded in __Harness__.java
            # without causing "class X is public, should be declared in a file named X.java" error.
            clean_code = _re.sub(r'public\s+class', 'class', code)
            class_match = _re.search(r'class\s+([\w\d_]+)', clean_code)
            class_name = class_match.group(1) if class_match else "Solution"

            # Detect method name and its parameter types
            java_method = func_name_hint or _re.search(
                r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+([\w\d_]+)\s*\([^)]+\)',
                clean_code
            )
            if isinstance(java_method, type(_re.match('', ''))):
                method_name = java_method.group(1)
            else:
                method_name = java_method if java_method else func_name_hint or "solution"

            java_param_types = _parse_java_signature(clean_code, method_name)

            # Build Java arg literals
            java_args = []
            for i, arg in enumerate(args_list):
                jtype = java_param_types[i] if i < len(java_param_types) else None
                java_args.append(_to_java_literal(arg, jtype))
            call_args = ", ".join(java_args)

            # Determine if method is static
            is_static = bool(_re.search(
                rf'static\s+[\w<>\[\]]+\s+{_re.escape(method_name)}\s*\(', clean_code
            ))

            if is_static:
                call_expr = f"{class_name}.{method_name}({call_args})"
            else:
                call_expr = f"(new {class_name}()).{method_name}({call_args})"

            # Build a wrapper class that calls the solution and prints __RESULT__
            harness = (
                "import java.util.Arrays;\n"
                "import java.util.List;\n"
                f"{clean_code}\n\n"
                "class __Harness__ {\n"
                "    public static void main(String[] args) {\n"
                "        try {\n"
                f"            Object result = {call_expr};\n"
                "            System.out.println(\"__RESULT__:\" + __toJson__(result));\n"
                "        } catch (Exception e) {\n"
                "            System.out.println(\"__RESULT__:\" + \"{\\\"__error__\\\":\\\"\" + e.getMessage() + \"\\\"}\");\n"
                "        }\n"
                "    }\n"
                "    static String __toJson__(Object o) {\n"
                "        if (o == null) return \"null\";\n"
                "        if (o instanceof int[]) return Arrays.toString((int[])o).replace(\", \",\",\").replace(\"[\",\"[\").replace(\"]\",\"]\");\n"
                "        if (o instanceof long[]) return Arrays.toString((long[])o).replace(\", \",\",\");\n"
                "        if (o instanceof double[]) return Arrays.toString((double[])o).replace(\", \",\",\");\n"
                "        if (o instanceof boolean[]) return Arrays.toString((boolean[])o).replace(\", \",\",\");\n"
                "        if (o instanceof String[]) { String[] a=(String[])o; StringBuilder sb=new StringBuilder(\"[\"); for(int i=0;i<a.length;i++){if(i>0)sb.append(\",\");sb.append(\"\\\"\"+a[i]+\"\\\"\");} sb.append(\"]\"); return sb.toString(); }\n"
                "        if (o instanceof int[][]) { int[][]a=(int[][])o; StringBuilder sb=new StringBuilder(\"[\"); for(int i=0;i<a.length;i++){if(i>0)sb.append(\",\");sb.append(__toJson__(a[i]));} sb.append(\"]\"); return sb.toString(); }\n"
                "        if (o instanceof Boolean) return o.toString();\n"
                "        if (o instanceof String) return \"\\\"\" + o + \"\\\"\";\n"
                "        return o.toString();\n"
                "    }\n"
                "}\n"
            )

            harness_file = os.path.join(tmp_dir, "__Harness__.java")
            with open(harness_file, 'w', encoding='utf-8') as f:
                f.write(harness)

            # Compile only the harness (solution code is embedded inside it)
            compile_proc = subprocess.run(
                ['javac', harness_file],
                capture_output=True, text=True, timeout=15, cwd=tmp_dir
            )
            if compile_proc.returncode != 0:
                err = compile_proc.stderr.strip()
                _shutil.rmtree(tmp_dir, ignore_errors=True)
                return {
                    "test": test_num, "passed": False, "input": input_display,
                    "expected": expected_str, "actual": "Compilation Error",
                    "stdout": "", "similarity": 0,
                    "error": f"Compilation Error: {err[:400]}"
                }

            run_proc = subprocess.run(
                ['java', '-cp', tmp_dir, '__Harness__'],
                capture_output=True, text=True, timeout=15
            )

            lines_out = run_proc.stdout.strip().split('\n')
            eval_result = None
            user_stdout = []
            for line in lines_out:
                if line.startswith("__RESULT__:"):
                    raw = line[len("__RESULT__:"):]
                    try: eval_result = json.loads(raw)
                    except: eval_result = raw.strip()
                elif line.strip():
                    user_stdout.append(line)

            stderr_msg = run_proc.stderr.strip()[:300] if run_proc.stderr else ""
            actual_val = eval_result if eval_result is not None else "No Output"
            similarity = _calculate_similarity(actual_val, expected)
            passed = similarity >= 0.95
            actual_str = json.dumps(actual_val) if isinstance(actual_val, (list, dict, bool)) else str(actual_val)
            _shutil.rmtree(tmp_dir, ignore_errors=True)
            return {
                "test": test_num, "passed": passed, "similarity": round(similarity, 3),
                "input": input_display, "expected": expected_str, "actual": actual_str[:500],
                "stdout": "\n".join(user_stdout),
                "error": (None if passed else (f"Runtime Error: {stderr_msg}" if stderr_msg else
                          ("Partial match" if similarity > 0.1 else "Logic mismatch")))
            }

        else:
            return {
                "test": test_num, "passed": False, "input": input_display,
                "expected": expected_str, "actual": f"Language '{language}' not supported.",
                "stdout": "", "similarity": 0, "error": f"Unsupported language: {language}"
            }

        # ── 4. Write script & execute ───────────────────────────────────────────
        # Use local temp dir for faster I/O (avoids network/roaming paths)
        local_tmp = tempfile.gettempdir()
        with tempfile.NamedTemporaryFile(mode='w', suffix=f".{ext}", delete=False,
                                         encoding='utf-8', dir=local_tmp) as f:
            f.write(script)
            tmp_path = f.name

        process = subprocess.run(run_cmd + [tmp_path], capture_output=True, text=True,
                                  timeout=30)  # 30s: go run compiles then runs
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

        # ── 5. Parse stdout/stderr ──────────────────────────────────────────────
        lines = process.stdout.strip().split('\n')
        eval_result = None
        user_stdout = []

        for line in lines:
            if line.startswith("__RESULT__:"):
                try: eval_result = json.loads(line[len("__RESULT__:"):])
                except: eval_result = line[len("__RESULT__:"):]
            elif line.strip():
                user_stdout.append(line)

        # Capture stderr for actionable error messages
        stderr_output = process.stderr.strip() if process.stderr else ""

        if isinstance(eval_result, dict) and "__error__" in eval_result:
            error_msg = eval_result.get("__error__", "")
            trace = eval_result.get("__trace__", "")
            # Extract line number from traceback
            line_no = "unknown"
            trace_match = _re.search(r'line (\d+)', trace or error_msg)
            if trace_match: line_no = trace_match.group(1)
            return {
                "test": test_num, "passed": False, "input": input_display,
                "expected": expected_str, "actual": f"Runtime Error: {error_msg}",
                "stdout": "\n".join(user_stdout), "similarity": 0,
                "error": f"line {line_no}: {error_msg}"
            }

        if eval_result is None and stderr_output:
            return {
                "test": test_num, "passed": False, "input": input_display,
                "expected": expected_str, "actual": "No output produced",
                "stdout": "\n".join(user_stdout), "similarity": 0,
                "error": f"Runtime Error: {stderr_output[:300]}"
            }

        actual_val = eval_result if eval_result is not None else "No Output"
        similarity = _calculate_similarity(actual_val, expected)
        passed = similarity >= 0.95
        actual_str = json.dumps(actual_val) if isinstance(actual_val, (list, dict, bool)) else str(actual_val)

        return {
            "test": test_num, "passed": passed, "similarity": round(similarity, 3),
            "input": input_display, "expected": expected_str, "actual": actual_str[:500],
            "stdout": "\n".join(user_stdout),
            "error": None if passed else ("Partial match" if similarity > 0.1 else "Logic mismatch")
        }

    except subprocess.TimeoutExpired:
        return {
            "test": test_num, "passed": False, "input": "N/A", "expected": "N/A",
            "actual": "Time Limit Exceeded (>10s)", "stdout": "", "similarity": 0,
            "error": "TLE: Your solution exceeded the 10 second time limit."
        }
    except Exception as e:
        return {
            "test": test_num, "passed": False, "input": "N/A", "expected": "N/A",
            "actual": "Execution Failed", "stdout": "", "similarity": 0,
            "error": str(e)[:500]
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass
        if tmp_dir and os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
