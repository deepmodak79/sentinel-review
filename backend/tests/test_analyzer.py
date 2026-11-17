from app.analyzer import analyze_files


def test_detects_dynamic_eval_and_secret():
    files = [{"path": "sample.py", "content": 'eval(user_input)\nAPI_KEY = "this-is-a-fake-test-key-value"'}]
    findings = analyze_files(files)
    assert {f["rule_id"] for f in findings} >= {"SEC001", "SEC002"}


def test_secret_evidence_is_redacted():
    findings = analyze_files([{"path": "sample.py", "content": 'API_KEY = "this-is-a-fake-test-key-value"'}])
    assert len(findings) == 1
    assert "this-is-a-fake-test-key-value" not in findings[0]["evidence"]
    assert "[REDACTED]" in findings[0]["evidence"]


def test_detects_additional_high_risk_patterns():
    source = (
        "subprocess.run(command, shell=True)\n"
        "pickle.loads(payload)\n"
        "yaml.load(payload)\n"
        "fetch(url, { verify=False })\n"
    )
    findings = analyze_files([{"path": "sample.py", "content": source}])
    assert {f["rule_id"] for f in findings} >= {"SEC007", "SEC008", "SEC009"}
    assert all("evidence" in finding for finding in findings)


def test_clean_file_has_no_findings():
    assert analyze_files([{"path": "safe.py", "content": "json.loads(payload)"}]) == []
