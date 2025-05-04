# main.py
import os
import uvicorn
from dotenv import load_dotenv
from bd_law_multi_agent.api.v1.endpoints import app  # Import the app directly

load_dotenv()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,  # Use the imported app directly
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )