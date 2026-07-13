import re
import os
import sys
import subprocess
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

# Configuration
MODEL_NAME = "qwen2.5-coder:1.5b"  # Optimized for dual-core CPU execution
MAX_ATTEMPTS = 3
TEMP_FILE = "temp_agent_script.py"
SUCCESS_FOLDER = "executed_successfully"

# Initialize local LLM via Ollama
llm = ChatOllama(model=MODEL_NAME, temperature=0.1)

def extract_code(text: str) -> str:
    """Extracts Python code from markdown code blocks in the LLM response."""
    pattern = r"```python\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    pattern_generic = r"```\s*(.*?)\s*```"
    match_generic = re.search(pattern_generic, text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()
    
    return text.strip()

def install_package(package_name: str) -> bool:
    """Installs a package dynamically into the active virtual environment."""
    print(f"[*] Dependency '{package_name}' is missing. Attempting automatic installation...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[+] Successfully installed package: '{package_name}'")
            return True
        else:
            print(f"[-] Failed to install '{package_name}'. Error details:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"[-] An exception occurred while installing '{package_name}': {e}")
        return False

def execute_code(code: str, filename: str = TEMP_FILE, attempted_installs=None):
    """Writes the code to a temporary file and runs it, capturing the output and errors."""
    if attempted_installs is None:
        attempted_installs = set()

    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    
    try:
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        
        # Intercept missing module errors
        match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", stderr)
        if match:
            missing_module = match.group(1)
            
            package_map = {
                "yaml": "pyyaml",
                "cv2": "opencv-python",
                "bs4": "beautifulsoup4",
                "sklearn": "scikit-learn"
            }
            package_name = package_map.get(missing_module, missing_module)
            
            if package_name in attempted_installs:
                print(f"[-] Safeguard: '{package_name}' was installed but is still not loading. Aborting install loop.")
                return returncode, stdout, stderr
            
            attempted_installs.add(package_name)
            
            if install_package(package_name):
                print("[*] Retrying execution with newly installed dependency...")
                return execute_code(code, filename, attempted_installs)
        
        return returncode, stdout, stderr
        
    except subprocess.TimeoutExpired:
        return -1, "", "Execution timed out (took longer than 180 seconds)."
    except Exception as e:
        return -1, "", str(e)

def generate_initial_code(prompt: str) -> str:
    """Asks the LLM to write the initial script."""
    system_prompt = (
        "You are an expert Python developer. Write clean, complete, and functional Python code "
        "to solve the user's request. Always wrap your Python code in a markdown code block: "
        "```python\n# your code\n```. "
        "Do not write explanations outside the code block."
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{user_input}")
    ])
    
    chain = prompt_template | llm
    response = chain.invoke({"user_input": prompt})
    return extract_code(response.content)

def correct_code(original_code: str, error_message: str, prompt: str) -> str:
    """Asks the LLM to fix the code based on the runtime error message."""
    system_prompt = (
        "You are an expert Python developer. The previous code you generated failed with an error. "
        "Review the original code, the runtime error, and the user's goal. Write a corrected, "
        "complete version of the code that resolves the error. Always wrap your corrected code "
        "in a markdown code block: ```python\n# your corrected code\n```. "
        "Do not write explanations outside the code block."
    )
    
    user_message = (
        f"Original Goal: {prompt}\n\n"
        f"Failed Code:\n```python\n{original_code}\n```\n\n"
        f"Runtime Error:\n{error_message}\n\n"
        f"Please provide the complete, corrected code."
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{user_message}")
    ])
    
    chain = prompt_template | llm
    response = chain.invoke({"user_message": user_message})
    return extract_code(response.content)

def save_successful_script(code: str, prompt: str):
    """Saves the successfully run script with a clean, dynamic filename."""
    os.makedirs(SUCCESS_FOLDER, exist_ok=True)
    
    # Extract words from the prompt
    words = re.findall(r'\b\w+\b', prompt.lower())
    
    # Filter out generic prompt and program vocabulary
    stop_words = {
        "write", "a", "python", "script", "using", "use", "that", "the", "to", "and", 
        "on", "for", "with", "run", "simple", "program", "code", "create", "make"
    }
    meaningful_words = [w for w in words if w not in stop_words]
    
    # Fallback to general name if prompt words are mostly filtered
    if not meaningful_words:
        meaningful_words = ["generated_script"]
        
    # Take the first 4 key words and join them with underscores
    base_name = "_".join(meaningful_words[:4])
    filename = f"{base_name}.py"
    full_path = os.path.join(SUCCESS_FOLDER, filename)
    
    # Duplicate prevention loop: appends a counter if name already exists
    counter = 1
    while os.path.exists(full_path):
        filename = f"{base_name}_{counter}.py"
        full_path = os.path.join(SUCCESS_FOLDER, filename)
        counter += 1
        
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[+] Successfully saved script to: {full_path}")
    except Exception as e:
        print(f"[-] Failed to save successful script: {e}")

def run_agent(task_prompt: str):
    """Orchestrates the generate-execute-correct loop."""
    print(f"\n[+] Starting task: {task_prompt}")
    
    # 1. Generate Initial Code
    print("[*] Generating initial code...")
    code = generate_initial_code(task_prompt)
    print("\n--- Generated Code ---")
    print(code)
    print("----------------------")
    
    success = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n[*] Execution Attempt {attempt}/{MAX_ATTEMPTS}...")
        return_code, stdout, stderr = execute_code(code)
        
        if return_code == 0:
            print("[+] Success! Code executed without errors.")
            print("\n--- Execution Output ---")
            print(stdout)
            print("------------------------")
            
            # Save the successful file
            save_successful_script(code, task_prompt)
            success = True
            break
        else:
            print(f"[-] Execution failed on attempt {attempt}.")
            print("\n--- Error Output ---")
            print(stderr)
            print("--------------------")
            
            if attempt == MAX_ATTEMPTS:
                print("[-] Maximum correction attempts reached. Could not resolve the error automatically.")
                break
            
            print("[*] Attempting to auto-correct the code...")
            code = correct_code(code, stderr, task_prompt)
            print("\n--- Corrected Code Proposed ---")
            print(code)
            print("-------------------------------")
            
    # Always clean up temporary script file
    if os.path.exists(TEMP_FILE):
        try:
            os.remove(TEMP_FILE)
        except OSError:
            pass

if __name__ == "__main__":
    print("==================================================")
    print("    Local Self-Correcting Code Agent Initiated    ")
    print("  Type your task and press Enter. Type 'exit' to quit.")
    print("==================================================")
    
    while True:
        try:
            task = input("\nEnter your task > ").strip()
            
            if task.lower() == "exit":
                print("[*] Shutting down agent. Goodbye!")
                break
            
            if not task:
                continue
            
            run_agent(task)
            
        except KeyboardInterrupt:
            print("\n\n[*] Shutting down agent. Goodbye!")
            break