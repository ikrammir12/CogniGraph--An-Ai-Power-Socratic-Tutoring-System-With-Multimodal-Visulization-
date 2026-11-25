# Run this from the existing CogniGraph project root after copying api_main.py and requirements-api.txt there.
if (Test-Path ".\.venv\Scripts\Activate.ps1") { . ".\.venv\Scripts\Activate.ps1" }
python -m uvicorn api_main:app --reload --host 127.0.0.1 --port 8000
