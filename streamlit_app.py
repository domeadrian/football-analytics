# Streamlit Cloud entrypoint
import importlib.util, sys, os
spec = importlib.util.spec_from_file_location(
    "dashboard",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "football_dashboard_v3.py"),
)
mod = importlib.util.module_from_spec(spec)
sys.modules["dashboard"] = mod
spec.loader.exec_module(mod)
