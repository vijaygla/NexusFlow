"""
NexusFlow Universal Multi-Language Coder Agent Node
Generates enterprise-grade, modular software solutions in ANY programming language.
Leverages execute_and_validate_code to self-test and self-correct implementation bugs.
Maintains chronological iteration history snapshots for Diff / Time Machine inspection.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.agents.state import GraphState
from app.agents.llm import get_chat_model
from app.config import get_settings
from app.tools.code_executor import run_code_validation, LANGUAGE_EXTENSIONS

logger = logging.getLogger("nexusflow.coder")

LANGUAGE_ENTRYPOINTS = {
    "java": ("Main.java", "MainTest.java"),
    "csharp": ("Program.cs", "ProgramTests.cs"),
    "cs": ("Program.cs", "ProgramTests.cs"),
    "go": ("main.go", "main_test.go"),
    "rust": ("main.rs", "tests.rs"),
    "cpp": ("main.cpp", "test_main.cpp"),
    "c": ("main.c", "test_main.c"),
    "javascript": ("index.js", "index.test.js"),
    "typescript": ("index.ts", "index.test.ts"),
    "sql": ("schema.sql", "queries.sql"),
    "ruby": ("main.rb", "test_main.rb"),
    "php": ("index.php", "test.php"),
    "kotlin": ("Main.kt", "MainTest.kt"),
    "swift": ("main.swift", "Tests.swift"),
    "python": ("main.py", "test_main.py"),
}


def get_default_filenames(lang: str) -> tuple[str, str]:
    normalized = lang.lower().strip()
    if normalized in LANGUAGE_ENTRYPOINTS:
        return LANGUAGE_ENTRYPOINTS[normalized]
    ext = LANGUAGE_EXTENSIONS.get(normalized, "txt")
    return (f"main.{ext}", f"test_main.{ext}")


def build_coder_system_prompt(language: str) -> str:
    lang_upper = language.upper()
    main_file, test_file = get_default_filenames(language)
    ext = LANGUAGE_EXTENSIONS.get(language.lower(), "txt")

    return f"""You are the Principal Software Engineer at NexusFlow, an elite enterprise engineering studio.
Your mandate is to craft production-grade, highly scalable, and completely working code solutions in {lang_upper}.

CORE DIRECTIVES:
1. MODULAR & ENTERPRISE ARCHITECTURE ({lang_upper}):
   - Organize code into clean, cohesive files adhering strictly to {lang_upper} conventions (e.g. `{main_file}`, `{test_file}`).
   - Implement comprehensive type annotations, error handling, idiomatic structures, and docstrings / comments.
   - NO placeholders, NO 'pass', NO empty stubs, and NO 'TODO' comments. Everything must be fully implemented and working.

2. UNIT TESTS MANDATORY:
   - Always include a dedicated runnable test file (e.g. `{test_file}`) verifying core functionalities and edge cases in {lang_upper}.

3. FILE SEPARATION FORMAT:
   Always structure each file cleanly with this exact header before each code block:

   ### FILE: <filename.{ext}>
   ```{ext}
   <source code>
   ```

4. REFINEMENT & ITERATION:
   - If previous review feedback or execution errors are provided, carefully analyze every critique.
   - Directly resolve every bug, performance bottleneck, edge case, and architectural issue identified.
"""


def extract_files_from_markdown(text: str, default_lang: str = "python") -> Dict[str, str]:
    """
    Parses code blocks and file annotations from LLM output across any programming language.
    """
    files: Dict[str, str] = {}
    main_name, test_name = get_default_filenames(default_lang)

    # Pattern 1: ### FILE: filename.ext followed by code fence
    pattern1 = re.compile(
        r"(?:###|##|#)?\s*(?:FILE|File|Filename):\s*([a-zA-Z0-9_\-\.\/\\]+)\s*\n+```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)```",
        re.MULTILINE,
    )
    for match in pattern1.finditer(text):
        filename = match.group(1).strip()
        code = match.group(2).strip()
        if filename and code:
            files[filename] = code

    # Pattern 2: ```lang:filename.ext
    if not files:
        pattern2 = re.compile(
            r"```[a-zA-Z0-9_-]*\s*[:\s]\s*([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)\s*\n([\s\S]*?)```",
            re.MULTILINE,
        )
        for match in pattern2.finditer(text):
            filename = match.group(1).strip()
            code = match.group(2).strip()
            if filename and code:
                files[filename] = code

    # Pattern 3: Fallback generic code blocks
    if not files:
        pattern3 = re.compile(r"```[a-zA-Z0-9_+#.-]*\s*\n([\s\S]*?)```", re.MULTILINE)
        matches = list(pattern3.finditer(text))
        if matches:
            if len(matches) == 1:
                files[main_name] = matches[0].group(1).strip()
            else:
                for idx, m in enumerate(matches):
                    code_chunk = m.group(1).strip()
                    if "test" in code_chunk.lower() or "assert" in code_chunk.lower():
                        files[test_name] = code_chunk
                    elif idx == 0:
                        files[main_name] = code_chunk
                    else:
                        ext = LANGUAGE_EXTENSIONS.get(default_lang.lower(), "txt")
                        files[f"module_{idx}.{ext}"] = code_chunk

    if not files and text.strip():
        files[main_name] = text.strip()

    return files


async def coder_node(state: GraphState) -> Dict[str, Any]:
    """
    Coder Node execution:
    1. Reads user prompt and review feedback.
    2. Synthesizes/refines code in the TARGET PROGRAMMING LANGUAGE.
    3. Runs execution validation on executable scripts.
    4. Records chronological iteration snapshot for Time Machine & Diff comparison.
    5. Updates state with generated_code, iterations, and active node.
    """
    settings = get_settings()
    llm = get_chat_model(model_name=settings.CODER_MODEL, temperature=settings.DEFAULT_TEMPERATURE)

    iterations = state.get("iterations", 0) + 1
    existing_feedback = state.get("review_feedback")
    existing_code = state.get("generated_code", {})
    existing_history = list(state.get("iteration_history", []))
    target_language = state.get("language", "python")

    user_prompt = ""
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            user_prompt = msg.content
            break

    if not user_prompt and state.get("messages"):
        user_prompt = state["messages"][0].content

    system_prompt = build_coder_system_prompt(target_language)
    conversation_history: List[Any] = [SystemMessage(content=system_prompt)]

    if iterations == 1 or not existing_code:
        coder_input = (
            f"TARGET PROGRAMMING LANGUAGE: {target_language.upper()}\n"
            f"USER SPECIFICATION REQUIREMENT:\n{user_prompt}\n\n"
            f"Produce a complete, robust, multi-file solution with runnable test cases in {target_language.upper()}.\n"
            "Format every file using `### FILE: <filename>`."
        )
    else:
        files_dump = "\n\n".join(
            [f"### FILE: {fname}\n```{target_language}\n{code}\n```" for fname, code in existing_code.items()]
        )
        coder_input = (
            f"TARGET PROGRAMMING LANGUAGE: {target_language.upper()}\n"
            f"ORIGINAL SPECIFICATION:\n{user_prompt}\n\n"
            f"CURRENT IMPLEMENTATION (ITERATION {iterations - 1}):\n{files_dump}\n\n"
            f"REVIEWER FEEDBACK & CRITICAL DEFICIENCIES TO RESOLVE:\n{existing_feedback}\n\n"
            f"Please revise the implementation to resolve ALL review findings completely in {target_language.upper()}.\n"
            "Produce the full updated files using `### FILE: <filename>`."
        )

    conversation_history.append(HumanMessage(content=coder_input))

    logger.info(f"[Coder Node] Executing iteration {iterations} in {target_language.upper()}...")
    ai_response = await llm.ainvoke(conversation_history)
    generated_text = ai_response.content if isinstance(ai_response.content, str) else str(ai_response.content)

    # Parse synthesized files
    parsed_files = extract_files_from_markdown(generated_text, default_lang=target_language)
    if not parsed_files and existing_code:
        parsed_files = existing_code

    # Safe validation execution in subprocess sandbox
    exec_result: Dict[str, Any] = {"success": True, "exit_code": 0, "stdout": "", "stderr": "", "language": target_language}
    target_exec_file = None
    for fname in parsed_files.keys():
        if fname.startswith("test_") or "test" in fname.lower():
            target_exec_file = fname
            break
    if not target_exec_file and parsed_files:
        target_exec_file = list(parsed_files.keys())[0]

    if target_exec_file and parsed_files.get(target_exec_file):
        runnable_bundle = parsed_files.get(target_exec_file, "")
        logger.info(f"[Coder Node] Validating execution of {target_exec_file} in {target_language} sandbox...")
        exec_result = run_code_validation(runnable_bundle, language=target_language)

    # Record snapshot for Iteration Time Machine
    snapshot = {
        "iteration": iterations,
        "files": dict(parsed_files),
        "execution_result": exec_result,
        "review_feedback": str(existing_feedback or ""),
        "language": target_language,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    existing_history.append(snapshot)

    summary_message = (
        f"Coder Agent synthesized {len(parsed_files)} file(s) in {target_language.upper()} on iteration {iterations}.\n"
        f"Validation status: {'SUCCESS' if exec_result.get('success') else 'FAILED'} (Exit code {exec_result.get('exit_code')})."
    )

    return {
        "generated_code": parsed_files,
        "iterations": iterations,
        "current_node": "coder",
        "execution_result": exec_result,
        "iteration_history": existing_history,
        "language": target_language,
        "messages": [AIMessage(content=f"{summary_message}\n\n{generated_text}")],
    }
