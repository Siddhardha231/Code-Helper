import re
import os
import sys
import subprocess
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

# Setup page layout
st.set_page_config(page_title="Local Auto-Code Agent", layout="wide")

# Constants
# Constants
MODEL_NAME = "qwen2.5-coder:1.5b"  # <--- Add this line
MAX_ATTEMPTS = 3                    # <--- Add this line
TEMP_FILE = "temp_agent_script.py"
SUCCESS_FOLDER = "executed_successfully"

# Helper for logging to UI in real-time
class UI_Logger:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.logs = []

    def log(self, text: str):
        self.logs.append(text)
        # Update the UI code block dynamically
        self.placeholder.code("\n".join(self.logs))

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

def install_package(package_name: str, logger: UI_Logger) -> bool:
    """Installs a package dynamically into the active virtual environment."""
    logger.log(f"[*] Dependency '{package_name}' is missing. Attempting automatic installation...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.log(f"[+] Successfully installed package: '{package_name}'")
            return True
        else:
            logger.log(f"[-] Failed to install '{package_name}'. Error details:\n{result.stderr}")
            return False
    except Exception as e:
        logger.log(f"[-] An exception occurred while installing '{package_name}': {e}")
        return False

def execute_code(code: str, logger: UI_Logger, filename: str = TEMP_FILE, attempted_installs=None):
    """Writes code to file and runs it, handling dependencies and timeouts."""
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
                logger.log(f"[-] Safeguard: '{package_name}' was installed but is still not loading. Aborting install loop.")
                return returncode, stdout, stderr
            
            attempted_installs.add(package_name)
            
            if install_package(package_name, logger):
                logger.log("[*] Retrying execution with newly installed dependency...")
                return execute_code(code, logger, filename, attempted_installs)
        
        return returncode, stdout, stderr
        
    except subprocess.TimeoutExpired:
        return -1, "", "Execution timed out (took longer than 180 seconds)."
    except Exception as e:
        return -1, "", str(e)

def generate_initial_code(llm, prompt: str) -> str:
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

def correct_code(llm, original_code: str, error_message: str, prompt: str) -> str:
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

def save_successful_script(code: str, prompt: str) -> str:
    """Saves script to 'executed_successfully' and returns path."""
    os.makedirs(SUCCESS_FOLDER, exist_ok=True)
    words = re.findall(r'\b\w+\b', prompt.lower())
    stop_words = {
        "write", "a", "python", "script", "using", "use", "that", "the", "to", "and", 
        "on", "for", "with", "run", "simple", "program", "code", "create", "make"
    }
    meaningful_words = [w for w in words if w not in stop_words]
    if not meaningful_words:
        meaningful_words = ["generated_script"]
        
    base_name = "_".join(meaningful_words[:4])
    filename = f"{base_name}.py"
    full_path = os.path.join(SUCCESS_FOLDER, filename)
    
    counter = 1
    while os.path.exists(full_path):
        filename = f"{base_name}_{counter}.py"
        full_path = os.path.join(SUCCESS_FOLDER, filename)
        counter += 1
        
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(code)
    return full_path

# =====================================================================
# STREAMLIT UI SETUP
# =====================================================================

st.title("🤖 Local Self-Correcting Code Agent")
st.caption("A locally-running coding companion that executes and debugs its own code.")

# Sidebar Settings
st.sidebar.header("Configuration")
model_option = st.sidebar.text_input("Ollama Model Name", value=MODEL_NAME)
max_attempts = st.sidebar.slider("Max Execution Attempts", min_value=1, max_value=5, value=MAX_ATTEMPTS)

# LLM Initialization
@st.cache_resource
def get_llm(model: str):
    return ChatOllama(model=model, temperature=0.1)

try:
    llm = get_llm(model_option)
except Exception as e:
    st.sidebar.error(f"Failed to load Ollama model. Ensure Ollama is running.")

# Main input UI
user_task = st.text_area("What do you want to build?", placeholder="e.g., Use transformers to analyze sentiment of 'I love coding!'", height=100)
run_btn = st.button("Generate and Run Code", type="primary")

if run_btn and user_task:
    # 3 Column layout for real-time visualization
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Console Output")
        log_placeholder = st.empty()
        logger = UI_Logger(log_placeholder)
        
    with col2:
        st.subheader("Latest Code")
        code_placeholder = st.empty()

    logger.log(f"[+] Starting task: {user_task}")
    logger.log("[*] Generating initial code...")
    
    # 1. Initial generation
    code = generate_initial_code(llm, user_task)
    code_placeholder.code(code, language="python")
    
    success = False
    for attempt in range(1, max_attempts + 1):
        logger.log(f"[*] Execution Attempt {attempt}/{max_attempts}...")
        return_code, stdout, stderr = execute_code(code, logger)
        
        if return_code == 0:
            logger.log("[+] Success! Code executed with zero errors.")
            st.success("Execution Successful!")
            
            # Save and display saved path
            saved_path = save_successful_script(code, user_task)
            logger.log(f"[+] Code saved successfully to: {saved_path}")
            
            # Display output and final code clean
            st.subheader("Program Output")
            st.code(stdout if stdout else "[Executed successfully with no stdout output]")
            success = True
            break
        else:
            logger.log(f"[-] Execution failed on attempt {attempt}.")
            logger.log(f"[-] Error details: {stderr}")
            
            if attempt == max_attempts:
                st.error("Maximum correction attempts reached. Could not resolve the error.")
                break
                
            logger.log("[*] Sending error logs to LLM for correction...")
            code = correct_code(llm, code, stderr, user_task)
            code_placeholder.code(code, language="python")
            
    # Cleanup temporary script file
    if os.path.exists(TEMP_FILE):
        try:
            os.remove(TEMP_FILE)
        except OSError:
            pass