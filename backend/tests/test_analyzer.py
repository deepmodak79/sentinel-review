from app.analyzer import analyze_files


def test_detects_dynamic_eval_and_secret():
    files = [{"path": "sample.py", "content": 'eval(user_input)\nAPI_KEY = "this-is-a-fake-test-key-value"'}]
    findings = analyze_files(files)
    assert {f["rule_id"] for f in findings} >= {"SEC001", "SEC002"}


def test_clean_file_has_no_findings():
    assert analyze_files([{"path": "safe.py", "content": "print('hello')"}]) == []
