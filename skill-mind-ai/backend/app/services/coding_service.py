import ast
import subprocess
import sys
import tempfile
import os
import json
import random
from .ai_service import generate_coding_challenge_llm, HAS_AI

# ─────────────────────────────────────────────────────────────────────────────
# Coding Problems Bank
# ─────────────────────────────────────────────────────────────────────────────

PROBLEMS_BANK = [
    {
        "id": 1,
        "title": "Find Duplicates",
        "difficulty": "easy",
        "tags": ["Python", "Algorithm", "Data Structures", "SQL"],
        "description": (
            "Write a function called `find_duplicates` that takes a list of integers "
            "and returns a sorted list of all values that appear more than once."
        ),
        "examples": [
            {"input": "[1, 2, 3, 2, 4, 5, 3]", "output": "[2, 3]"},
            {"input": "[1, 1, 1]", "output": "[1]"},
            {"input": "[1, 2, 3]", "output": "[]"},
        ],
        "hints": ["Consider using a dictionary or set.", "Think about edge cases like empty lists."],
        "starter_code": "def find_duplicates(nums):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": [1, 2, 3, 2, 4, 5, 3], "expected": [2, 3]},
            {"input": [1, 1, 1], "expected": [1]},
            {"input": [1, 2, 3], "expected": []},
            {"input": [], "expected": []},
            {"input": [5, 5, 6, 7, 7, 8], "expected": [5, 7]},
        ],
        "test_wrapper": "result = sorted(find_duplicates({input}))",
    },
    {
        "id": 2,
        "title": "Reverse a String",
        "difficulty": "easy",
        "tags": ["Python", "String", "Basic"],
        "description": (
            "Write a function called `reverse_string` that reverses a given string "
            "without using Python's built-in `[::-1]` slice or `reversed()`."
        ),
        "examples": [
            {"input": '"hello"', "output": '"olleh"'},
            {"input": '"abcde"', "output": '"edcba"'},
        ],
        "hints": ["Use a loop.", "Build the result character by character."],
        "starter_code": "def reverse_string(s):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": "hello", "expected": "olleh"},
            {"input": "abcde", "expected": "edcba"},
            {"input": "a", "expected": "a"},
            {"input": "", "expected": ""},
            {"input": "racecar", "expected": "racecar"},
        ],
        "test_wrapper": "result = reverse_string({input})",
    },
    {
        "id": 3,
        "title": "FizzBuzz",
        "difficulty": "easy",
        "tags": ["Python", "Basic", "Logic"],
        "description": (
            "Write a function called `fizzbuzz` that takes an integer `n` and returns a list of strings. "
            "For multiples of 3: 'Fizz', for multiples of 5: 'Buzz', for multiples of both: 'FizzBuzz', "
            "otherwise the number as a string."
        ),
        "examples": [
            {"input": "5", "output": '["1", "2", "Fizz", "4", "Buzz"]'},
        ],
        "hints": ["Check divisibility with the `%` operator.", "Order your conditions: check 15 before 3 and 5."],
        "starter_code": "def fizzbuzz(n):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": 5, "expected": ["1", "2", "Fizz", "4", "Buzz"]},
            {"input": 15, "expected": ["1","2","Fizz","4","Buzz","Fizz","7","8","Fizz","Buzz","11","Fizz","13","14","FizzBuzz"]},
            {"input": 1, "expected": ["1"]},
        ],
        "test_wrapper": "result = fizzbuzz({input})",
    },
    {
        "id": 4,
        "title": "Two Sum",
        "difficulty": "medium",
        "tags": ["Python", "Algorithm", "Hash Map"],
        "description": (
            "Write a function called `two_sum` that takes a list of integers `nums` and a target integer `target`. "
            "Return the indices of the two numbers that add up to the target. "
            "You may assume that each input would have exactly one solution."
        ),
        "examples": [
            {"input": "nums=[2,7,11,15], target=9", "output": "[0, 1]"},
            {"input": "nums=[3,2,4], target=6", "output": "[1, 2]"},
        ],
        "hints": ["Use a hash map for O(n) time.", "Store each number's index as you iterate."],
        "starter_code": "def two_sum(nums, target):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
            {"input": {"nums": [3, 3], "target": 6}, "expected": [0, 1]},
        ],
        "test_wrapper": "result = sorted(two_sum({nums}, {target}))",
    },
    {
        "id": 5,
        "title": "Palindrome Check",
        "difficulty": "medium",
        "tags": ["Python", "String", "Logic"],
        "description": (
            "Write a function called `is_palindrome` that takes a string and returns `True` "
            "if it reads the same forwards and backwards (case-insensitive, ignore non-alphanumeric characters), "
            "and `False` otherwise."
        ),
        "examples": [
            {"input": '"A man a plan a canal Panama"', "output": "True"},
            {"input": '"race a car"', "output": "False"},
        ],
        "hints": ["Filter non-alphanumeric characters first.", "Compare the cleaned string with its reverse."],
        "starter_code": "def is_palindrome(s):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": "A man a plan a canal Panama", "expected": True},
            {"input": "race a car", "expected": False},
            {"input": "Was it a car or a cat I saw", "expected": True},
            {"input": "hello", "expected": False},
            {"input": "", "expected": True},
        ],
        "test_wrapper": "result = is_palindrome({input})",
    },
    {
        "id": 6,
        "title": "Fibonacci Sequence",
        "difficulty": "medium",
        "tags": ["Python", "Algorithm", "Recursion"],
        "description": (
            "Write a function called `fibonacci` that returns a list of the first `n` Fibonacci numbers. "
            "The sequence starts with [0, 1, 1, 2, 3, 5, ...]."
        ),
        "examples": [
            {"input": "6", "output": "[0, 1, 1, 2, 3, 5]"},
            {"input": "1", "output": "[0]"},
        ],
        "hints": ["Start with [0, 1] and build up.", "Each number is the sum of the previous two."],
        "starter_code": "def fibonacci(n):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": 6, "expected": [0, 1, 1, 2, 3, 5]},
            {"input": 1, "expected": [0]},
            {"input": 2, "expected": [0, 1]},
            {"input": 10, "expected": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]},
        ],
        "test_wrapper": "result = fibonacci({input})",
    },
    {
        "id": 7,
        "title": "Valid Parentheses",
        "difficulty": "hard",
        "tags": ["Python", "Stack", "Data Structures"],
        "description": (
            "Write a function called `is_valid_parentheses` that takes a string containing only "
            "'(', ')', '{', '}', '[' and ']'. Return `True` if the brackets are balanced (opened "
            "and closed in the correct order), otherwise return `False`."
        ),
        "examples": [
            {"input": '"()"', "output": "True"},
            {"input": '"()[]{}"', "output": "True"},
            {"input": '"(]"', "output": "False"},
        ],
        "hints": ["Use a stack (list in Python).", "Push opening brackets, pop and match on closing brackets."],
        "starter_code": "def is_valid_parentheses(s):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": "()", "expected": True},
            {"input": "()[]{}", "expected": True},
            {"input": "(]", "expected": False},
            {"input": "([)]", "expected": False},
            {"input": "{[]}", "expected": True},
            {"input": "", "expected": True},
        ],
        "test_wrapper": "result = is_valid_parentheses({input})",
    },
    {
        "id": 8,
        "title": "Merge Two Sorted Lists",
        "difficulty": "hard",
        "tags": ["Python", "Algorithm", "Sorting"],
        "description": (
            "Write a function called `merge_sorted` that takes two sorted lists of integers "
            "and returns a single merged sorted list."
        ),
        "examples": [
            {"input": "[1, 3, 5], [2, 4, 6]", "output": "[1, 2, 3, 4, 5, 6]"},
            {"input": "[], [1]", "output": "[1]"},
        ],
        "hints": ["Use two pointers.", "Compare elements from each list one at a time."],
        "starter_code": "def merge_sorted(list1, list2):\n    # Write your solution here\n    pass\n",
        "test_cases": [
            {"input": {"list1": [1, 3, 5], "list2": [2, 4, 6]}, "expected": [1, 2, 3, 4, 5, 6]},
            {"input": {"list1": [], "list2": [1]}, "expected": [1]},
            {"input": {"list1": [1, 2], "list2": []}, "expected": [1, 2]},
            {"input": {"list1": [1, 1, 2], "list2": [1, 3]}, "expected": [1, 1, 1, 2, 3]},
        ],
        "test_wrapper": "result = merge_sorted({list1}, {list2})",
    },
]

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


def get_challenge_set(jd_text=None):
    """Return exactly 6 problems: 2 easy, 2 medium, 2 hard.
    Strictly prioritizes dynamic AI generation if available."""
    selected_challenges = []
    jd_skills = []
    
    # 1. Try to get AI-generated challenges first
    if HAS_AI:
        try:
            from .resume_service import analyze_resume
            jd_analysis = analyze_resume(jd_text) if jd_text else {}
            jd_skills = jd_analysis.get('skills', [])
            
            ai_p = generate_coding_challenge_llm(jd_skills, jd_text)
            if ai_p and isinstance(ai_p, dict):
                ai_p["id"] = 2000 + random.randint(1, 999)
                ai_p["is_ai"] = True
                selected_challenges.append(ai_p)
        except Exception as e:
            print(f"AI Coding Generation failed: {e}")

    # 2. Fill remaining from Bank
    all_bank = list(PROBLEMS_BANK)
    random.shuffle(all_bank)
    
    easy = [p for p in all_bank if p.get("difficulty") == "easy"]
    medium = [p for p in all_bank if p.get("difficulty") == "medium"]
    hard = [p for p in all_bank if p.get("difficulty") == "hard"]
    
    target = 6
    while len(selected_challenges) < target:
        if len([c for c in selected_challenges if c['difficulty'] == 'easy']) < 2 and easy:
            selected_challenges.append(easy.pop(0))
        elif len([c for c in selected_challenges if c['difficulty'] == 'medium']) < 2 and medium:
            selected_challenges.append(medium.pop(0))
        elif len([c for c in selected_challenges if c['difficulty'] == 'hard']) < 2 and hard:
            selected_challenges.append(hard.pop(0))
        elif all_bank:
            p = all_bank.pop(0)
            if p not in selected_challenges:
                selected_challenges.append(p)
        else:
            break
            
    random.shuffle(selected_challenges)
    
    return {
        "challenges": selected_challenges[:6],
        "languages": detect_languages_from_skills(jd_skills)
    }



def get_problem_by_id(problem_id):
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
    """Evaluate code quality using AST analysis."""
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

    score = 30
    feedback_parts = []

    if functions:
        score += 20
        feedback_parts.append(f"{len(functions)} function(s) defined")
    if loops:
        score += 10
        feedback_parts.append(f"{len(loops)} loop(s) used")
    if conditionals:
        score += 10
        feedback_parts.append(f"{len(conditionals)} conditional(s)")
    if returns:
        score += 10
        feedback_parts.append("return statement(s) present")
    if classes:
        score += 10
        feedback_parts.append(f"{len(classes)} class(es) defined")

    lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
    if len(lines) > 5:
        score += 10
        feedback_parts.append(f"{len(lines)} lines of code")

    for func in functions:
        if (func.body and isinstance(func.body[0], ast.Expr)
                and isinstance(func.body[0].value, ast.Constant)
                and isinstance(func.body[0].value.value, str)):
            score += 5
            feedback_parts.append("docstrings present")
            break

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
    tc_input = test_case["input"]
    expected = test_case["expected"]
    
    # 1. Prepare Input for Script
    input_str = json.dumps(tc_input)
    
    # 2. Build Language-Specific Script
    title_snake = problem["title"].lower().replace(' ', '_')
    script = ""
    run_cmd = []
    ext = SUPPORTED_LANGUAGES.get(language, {}).get("ext", "py")

    if language == 'python':
        if isinstance(tc_input, dict):
            call_line = problem["test_wrapper"].format(**{k: json.dumps(v) for k, v in tc_input.items()})
        else:
            call_line = problem["test_wrapper"].format(input=json.dumps(tc_input))
            
        script = f"""
import json
import sys

{code}

try:
    {call_line}
    print(json.dumps(result))
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
        if not stdout:
            return {
                "test": test_num,
                "passed": False,
                "input": str(tc_input),
                "expected": str(expected),
                "actual": f"No output. stderr: {proc.stderr.strip()[:200]}",
                "error": proc.stderr.strip()[:200],
            }

        # Handle simple string comparison for Java/others if needed
        try:
            actual = json.loads(stdout)
        except:
            actual = stdout # Fallback to raw string

        if isinstance(actual, dict) and "__error__" in actual:
            return {
                "test": test_num, "passed": False, "input": str(tc_input),
                "expected": str(expected), "actual": None, "error": actual["__error__"],
            }

        # Normalized comparison
        passed = str(actual) == str(expected) or actual == expected
        return {
            "test": test_num, "passed": passed, "input": str(tc_input),
            "expected": str(expected), "actual": str(actual), "error": None,
        }

    except Exception as e:
        return {"test": test_num, "passed": False, "input": str(tc_input), "expected": str(expected), "error": str(e)}
