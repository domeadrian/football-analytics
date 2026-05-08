import sys
import re
with open("football_dashboard_v2.py", encoding="utf-8") as f:
    content = f.read()

# Test that all imports work
try:
    exec(content.split("st.set_page_config")[0])
    print("All imports OK")
except Exception as e:
    print(f"Import error: {e}")

# Check line count
lines = len(content.splitlines())
print(f"Total lines: {lines}")

# Quick check number of pages
pages = re.findall(r"elif page == |if page == ", content)
print(f"Total page handlers: {len(pages)}")

try:
    nav_block = content.split("page = st.sidebar.radio")[0].split("pages = [")[1].split("]")[0]
    nav_pages = re.findall(r"\"([^\"]+)\"", nav_block)
    print(f"Navigation pages: {len(nav_pages)}")
    print(f"Pages: {nav_pages}")
except Exception as e:
    print(f"Navigation parsing error: {e}")
