from pathlib import Path

def test_scanner_file_exists():
    scanner_file = Path("app/scanners/scan_52w.py")
    assert scanner_file.exists()

def test_dashboard_file_exists():
    dashboard_file = Path("app/dashboard/dashboard.py")
    assert dashboard_file.exists()

def test_requirements_file_exists():
    requirements_file = Path("requirements.txt")
    assert requirements_file.exists()
