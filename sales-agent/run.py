import uvicorn
import sys
import os
import traceback
from dotenv import load_dotenv

# Ensure the current directory is explicitly in the python path for Uvicorn's child process
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

try:
    import app.main
except Exception as e:
    with open("import_error.txt", "w") as f:
        traceback.print_exc(file=f)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
