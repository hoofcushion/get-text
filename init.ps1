Start-Process pwsh -ArgumentList '-NoProfile', '-Command', {
    python -m venv venv
    & .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Read-Host '按任意键退出'
} -Wait