import os
import subprocess
import sys

def test_generate_scorecard_dry_run():
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "generate_scorecard.py")
    script_path = os.path.abspath(script_path)
    
    result = subprocess.run(
        [sys.executable, script_path, "AAPL", "--dry-run"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "# AAPL Policy Scorecard" in result.stdout
    assert "**Disclaimer:** This is an evidence-backed research classification, not financial advice or a price prediction." in result.stdout

def test_generate_scorecard_file_creation(tmp_path):
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "generate_scorecard.py")
    script_path = os.path.abspath(script_path)
    
    # We will run the script but we need to ensure it writes to a temp directory or we just clean up after.
    # Since the script hardcodes `reports` at project root, let's run it and then check and remove the file.
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    report_path = os.path.join(project_root, "reports", "TEST_scorecard.md")
    
    if os.path.exists(report_path):
        os.remove(report_path)
        
    result = subprocess.run(
        [sys.executable, script_path, "TEST"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert os.path.exists(report_path)
    
    with open(report_path, "r") as f:
        content = f.read()
        
    assert "# TEST Policy Scorecard" in content
    assert "**Disclaimer:** This is an evidence-backed research classification" in content
    
    # Cleanup
    os.remove(report_path)
