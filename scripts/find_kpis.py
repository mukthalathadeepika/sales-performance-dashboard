import os
import re

for root, dirs, files in os.walk("."):
    if ".git" in root or ".venv" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith((".py", ".css", ".html", ".md")):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "kpi" in content.lower():
                    matches = re.findall(r"(?:def\s+[^\(]*kpi[^\(]*|class\s+[^\(:]*kpi|kpi-card[^{;<\n]*|\.kpi[a-zA-Z0-9_\-]*)", content, re.IGNORECASE)
                    if matches:
                        print(f"{path}: {set(matches[:10])}")
