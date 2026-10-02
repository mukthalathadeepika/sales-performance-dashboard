import ast
import sys

sys.stdout.reconfigure(encoding="utf-8")

file_path = "frontend/views/dashboard_view.py"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

tree = ast.parse(code, filename=file_path)
funcs = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
print(f"Total functions found: {len(funcs)}")
for f in funcs:
    print(f" - {f}")

from collections import Counter
counts = Counter(funcs)
dups = [name for name, c in counts.items() if c > 1]
if dups:
    print(f"DUPLICATES: {dups}")
else:
    print("No duplicate functions found! Syntax and AST are completely clean.")
