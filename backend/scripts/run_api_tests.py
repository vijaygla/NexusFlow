"""
Automated API Test Runner for NexusFlow
Validates all endpoints: Health, Sandbox (Python & Node), Security Scan, History, Analytics, and SSE.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_all():
    print("==================================================")
    print("RUNNING NEXUSFLOW COMPREHENSIVE TEST SUITE")
    print("==================================================")

    # 1. Health Diagnostics
    print("\n[TEST 1] GET /health")
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    print("-> PASSED: Health status is 200 OK")

    # 2. Python Sandbox
    print("\n[TEST 2] POST /api/workflow/validate (Python)")
    res = client.post("/api/workflow/validate", json={
        "code": "assert 5 * 5 == 25\nprint('Python OK')",
        "language": "python"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
    print("-> PASSED: Python sandbox executed successfully")

    # 3. Node.js Sandbox
    print("\n[TEST 3] POST /api/workflow/validate (Node.js / JS)")
    res = client.post("/api/workflow/validate", json={
        "code": "console.log('NodeJS Sandbox verified');",
        "language": "javascript"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "NodeJS Sandbox verified" in res.json()["stdout"]
    print("-> PASSED: Node.js sandbox executed successfully")

    # 4. Security Vulnerability Scan
    print("\n[TEST 4] POST /api/workflow/security-scan")
    vuln_code = (
        "import os\n"
        "eval('2 + 2')\n"
        "os.system('echo dangerous')\n"
    )
    res = client.post("/api/workflow/security-scan", json={"code": vuln_code})
    assert res.status_code == 200
    sec_data = res.json()
    assert sec_data["total_issues"] >= 2
    assert sec_data["high_severity_count"] >= 2
    assert sec_data["verdict"] in ("MEDIUM_RISK", "HIGH_RISK")
    print("-> PASSED: Security scan flagged dangerous primitives accurately")

    # 5. Session History Query (MS SQL Server)
    print("\n[TEST 5] GET /api/workflow/history")
    res = client.get("/api/workflow/history?limit=10")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    print(f"-> PASSED: Retrieved {len(res.json())} sessions from SQL Server")

    # 6. Analytics Query (MS SQL Server)
    print("\n[TEST 6] GET /api/workflow/analytics")
    res = client.get("/api/workflow/analytics")
    assert res.status_code == 200
    ana_data = res.json()
    assert "total_runs" in ana_data
    assert "pass_rate_percentage" in ana_data
    print(f"-> PASSED: Analytics data: {ana_data}")

    # 7. Error Handling (404 and 422)
    print("\n[TEST 7] Error responses (404 & 422)")
    res_404 = client.get("/api/workflow/unknown-route")
    assert res_404.status_code == 404
    assert res_404.json()["error"] is True

    res_422 = client.post("/api/workflow/execute", json={"prompt": ""})
    assert res_422.status_code == 422
    assert res_422.json()["error"] is True
    print("-> PASSED: Error handlers return structured JSON payloads")

    print("\n==================================================")
    print("ALL 7 ENTERPRISE BACKEND TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    test_all()
