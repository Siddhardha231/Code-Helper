import streamlit as st
from pathlib import Path
from config.settings import Settings
from domain.enums import RunStatus
from domain.models import RunResult
from llm.ollama import OllamaProvider
from workspace.manager import WorkspaceManager
from execution.sandbox import ExecutionSandbox
from agent.orchestrator import AgentOrchestrator

# Configure page
st.set_page_config(
    page_title="Code-Helper | Phase 1",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Code-Helper — Autonomous Code Generation & Verification")
st.caption("Phase 1: Autonomous Python Script Generation, Sandboxed Execution, Traceback Capture & Self-Healing Retry Loop.")

# Sidebar Configuration
st.sidebar.header("Configuration")
model_name = st.sidebar.text_input("Ollama Model", value="qwen2.5-coder:1.5b")
max_attempts = st.sidebar.slider("Max Correction Attempts", min_value=1, max_value=5, value=5)
timeout_sec = st.sidebar.slider("Execution Timeout (seconds)", min_value=5, max_value=60, value=30)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Phase 1 Invariants:**
    - Script mode only (`main.py`)
    - Deterministic syntax verification
    - Sandboxed execution in workspace directory
    - Traceback-driven self-correction
    - Bounded retries (Max 5 attempts)
    """
)

# Main Prompt Input
prompt = st.text_area(
    "What Python program should be built and verified?",
    placeholder="e.g. Write a script to calculate the first 10 Fibonacci numbers and print them.",
    height=110,
)

col_btn, _ = st.columns([1, 4])
with col_btn:
    run_button = st.button("Generate & Verify", type="primary", use_container_width=True)

if run_button and prompt.strip():
    # Setup live streaming containers
    status_box = st.empty()
    status_box.info("Initializing Agent Orchestrator...")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Console & Event Log")
        log_box = st.empty()

    with col_right:
        st.subheader("Current Code (`main.py`)")
        code_box = st.empty()

    logs = []

    def ui_logger(event_type: str, data: dict):
        if event_type == "STATUS_CHANGED":
            msg = data.get("message", "")
            logs.append(f"[*] {msg}")
            log_box.code("\n".join(logs))
        elif event_type == "CODE_GENERATED":
            code_box.code(data.get("source", ""), language="python")
        elif event_type == "CODE_REPAIRED":
            logs.append(f"[+] Debugger applied patch for attempt #{data.get('attempt_number')}")
            log_box.code("\n".join(logs))
            code_box.code(data.get("repaired_source", ""), language="python")
        elif event_type == "EXECUTION_COMPLETED":
            exit_code = data.get("exit_code")
            stdout = data.get("stdout", "").strip()
            stderr = data.get("stderr", "").strip()
            logs.append(f"--> Attempt #{data.get('attempt_number')} finished with exit code {exit_code}")
            if stdout:
                logs.append(f"    [stdout]:\n{stdout}")
            if stderr:
                logs.append(f"    [stderr]:\n{stderr}")
            log_box.code("\n".join(logs))

    settings = Settings(
        model_name=model_name,
        max_attempts=max_attempts,
        execution_timeout_seconds=timeout_sec,
    )
    llm = OllamaProvider(model_name=model_name)
    sandbox = ExecutionSandbox(timeout_seconds=timeout_sec)
    workspace_manager = WorkspaceManager(root_dir=settings.workspace_root)
    orchestrator = AgentOrchestrator(
        llm=llm,
        sandbox=sandbox,
        workspace_manager=workspace_manager,
        settings=settings,
    )

    try:
        result: RunResult = orchestrator.run(prompt.strip(), on_event=ui_logger)

        if result.status == RunStatus.VERIFIED:
            status_box.success(f"✅ VERIFIED — {result.message} (Run ID: {result.run_id})")
        else:
            status_box.error(f"❌ FAILED — {result.message} (Run ID: {result.run_id})")

        # Display final code
        if result.final_source:
            code_box.code(result.final_source, language="python")

        # Attempts History Breakdown
        st.markdown("---")
        st.subheader("Attempt History & Audit Trail")

        for attempt in result.attempts:
            expander_title = (
                f"Attempt #{attempt.attempt_number} — Status: {attempt.state_after.upper()} "
                f"(Error: {attempt.error_type.value if attempt.error_type else 'none'})"
            )
            with st.expander(expander_title, expanded=(attempt.attempt_number == result.total_attempts)):
                tab1, tab2, tab3 = st.tabs(["Source Code", "Execution Output", "Diagnostics"])
                with tab1:
                    st.code(attempt.source_code, language="python")
                with tab2:
                    if attempt.execution_result:
                        st.write(f"**Exit Code:** `{attempt.execution_result.exit_code}`")
                        st.write(f"**Duration:** `{attempt.execution_result.duration_ms} ms`")
                        if attempt.execution_result.stdout:
                            st.write("**Stdout:**")
                            st.code(attempt.execution_result.stdout)
                        if attempt.execution_result.stderr:
                            st.write("**Stderr:**")
                            st.code(attempt.execution_result.stderr)
                with tab3:
                    st.write(f"**Error Classification:** `{attempt.error_type.value if attempt.error_type else 'none'}`")
                    if attempt.error_message:
                        st.write(f"**Message:** {attempt.error_message}")
                    if attempt.repair_summary:
                        st.write(f"**Repair Summary:** {attempt.repair_summary}")

    except Exception as e:
        status_box.error(f"Error during orchestration: {str(e)}")