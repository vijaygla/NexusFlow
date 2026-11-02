"""
NexusFlow Automated Security & Vulnerability Auditor
Static AST and pattern analyzer for synthesized codebases.
Detects shell injections, dynamic code execution, hardcoded credentials,
insecure deserialization, and SQL injection vulnerabilities.
"""

import re
from typing import Dict, Any, List


# Security audit rules
SECURITY_RULES = [
    {
        "id": "SEC-001",
        "severity": "HIGH",
        "name": "Dangerous Dynamic Code Execution",
        "pattern": r"\b(eval|exec|__import__)\s*\(",
        "message": "Use of dynamic execution primitives (eval/exec) can lead to arbitrary code execution.",
        "recommendation": "Refactor logic to use safe parsers (ast.literal_eval) or direct function dispatching.",
    },
    {
        "id": "SEC-002",
        "severity": "HIGH",
        "name": "Shell Injection Vulnerability",
        "pattern": r"(os\.system\s*\(|subprocess\.(Popen|run|call)\s*\(.*shell\s*=\s*True)",
        "message": "Subprocess execution with shell=True is susceptible to command injection.",
        "recommendation": "Pass arguments as structured lists with shell=False.",
    },
    {
        "id": "SEC-003",
        "severity": "HIGH",
        "name": "Insecure Deserialization",
        "pattern": r"\b(pickle\.loads|marshal\.loads|_pickle\.loads|yaml\.load\s*\([^,)]+\))",
        "message": "Insecure object deserialization can result in remote code execution.",
        "recommendation": "Use yaml.safe_load or standard JSON serialization (json.loads).",
    },
    {
        "id": "SEC-004",
        "severity": "MEDIUM",
        "name": "Potential SQL Injection via String Formatting",
        "pattern": r"(execute|cursor\.execute)\s*\(\s*(f[\"']|\".*%\s*|'.*%\s*).*(SELECT|INSERT|UPDATE|DELETE)",
        "message": "Direct string interpolation into SQL queries allows SQL injection.",
        "recommendation": "Use parameterized queries with placeholder binding (?) or ORM abstractions.",
    },
    {
        "id": "SEC-005",
        "severity": "MEDIUM",
        "name": "Hardcoded Credential or Secret",
        "pattern": r"(?i)(password|secret|api_key|token|access_key)\s*=\s*[\"'][a-zA-Z0-9_\-\.]{8,}[\"']",
        "message": "Detected potential hardcoded credential or secret key in source code.",
        "recommendation": "Load credentials securely from environment variables using Pydantic Settings or os.environ.",
    },
    {
        "id": "SEC-006",
        "severity": "LOW",
        "name": "Insecure Randomness for Security Context",
        "pattern": r"\brandom\.(random|randint|choice)\s*\(",
        "message": "Standard pseudo-random number generator used. Not cryptographically secure.",
        "recommendation": "Use secrets or os.urandom if generating security tokens or nonces.",
    },
]


def audit_code_security(code: str, file_name: str = "main.py") -> Dict[str, Any]:
    """
    Performs static security analysis on code.
    Returns audit findings, vulnerability count, score (0-100), and verdict.
    """
    findings: List[Dict[str, Any]] = []
    lines = code.split("\n")

    for rule in SECURITY_RULES:
        regex = re.compile(rule["pattern"])
        for idx, line in enumerate(lines):
            # Ignore comments
            clean_line = line.strip()
            if clean_line.startswith("#") or clean_line.startswith("//"):
                continue

            match = regex.search(line)
            if match:
                findings.append({
                    "id": rule["id"],
                    "severity": rule["severity"],
                    "name": rule["name"],
                    "file": file_name,
                    "line": idx + 1,
                    "snippet": line.strip()[:100],
                    "message": rule["message"],
                    "recommendation": rule["recommendation"],
                })

    # Calculate overall security score
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
    low_count = sum(1 for f in findings if f["severity"] == "LOW")

    deductions = (high_count * 30) + (med_count * 15) + (low_count * 5)
    score = max(0, 100 - deductions)

    if score >= 90:
        verdict = "CLEAN"
    elif score >= 70:
        verdict = "LOW_RISK"
    elif score >= 40:
        verdict = "MEDIUM_RISK"
    else:
        verdict = "HIGH_RISK"

    return {
        "file": file_name,
        "score": score,
        "verdict": verdict,
        "total_issues": len(findings),
        "high_severity_count": high_count,
        "medium_severity_count": med_count,
        "low_severity_count": low_count,
        "vulnerabilities": findings,
    }


def audit_codebase_security(files: Dict[str, str]) -> Dict[str, Any]:
    """Audits an entire multi-file codebase and aggregates security findings."""
    all_findings: List[Dict[str, Any]] = []
    total_files = len(files)
    scores: List[int] = []

    for fname, content in files.items():
        res = audit_code_security(content, file_name=fname)
        scores.append(res["score"])
        all_findings.extend(res["vulnerabilities"])

    avg_score = round(sum(scores) / max(1, total_files)) if total_files > 0 else 100

    if avg_score >= 90:
        verdict = "CLEAN"
    elif avg_score >= 70:
        verdict = "LOW_RISK"
    elif avg_score >= 40:
        verdict = "MEDIUM_RISK"
    else:
        verdict = "HIGH_RISK"

    return {
        "overall_score": avg_score,
        "verdict": verdict,
        "files_analyzed": total_files,
        "total_vulnerabilities": len(all_findings),
        "vulnerabilities": all_findings,
    }
