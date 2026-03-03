import os
import httpx
import psutil
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Pi 5 AI Gateway")

# SECURITY: Set your secret key here
API_KEY_SECRET = "MySuperSecretKey123"

# Allow your Mobile App to connect without CORS issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

# Helper: Check API Key
async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return x_api_key

# --- ENDPOINTS ---

@app.get("/health")
async def health():
    """Check the physical status of the Pi 5"""
    # Get CPU Temperature (Pi-specific)
    temp = os.popen("vcgencmd measure_temp").readline().replace("temp=","").strip()
    return {
        "status": "online",
        "cpu_temp": temp,
        "ram_usage_percent": psutil.virtual_memory().percent,
        "cpu_usage_percent": psutil.cpu_percent()
    }

# This ensures your REST client sends the right JSON structure
class PromptRequest(BaseModel):
    prompt: str

@app.post("/generate")
async def generate(data: PromptRequest):
    # The URL where your llama-server is running
    LLAMA_SERVER_URL = "http://127.0.0.1:8080/completion"
    
    # TinyLlama specific prompt template for better instructions
    formatted_prompt = f"<|user|>\n{data.prompt}</s>\n<|assistant|>\n"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LLAMA_SERVER_URL,
                json={
                    "prompt": formatted_prompt,
                    "n_predict": 100, # Number of tokens to generate
                    "temperature": 0.7,
                    "stream": False
                },
                timeout=60.0 
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Llama server error")

            result = response.json()
            return {
                "status": "success",
                "response": result.get("content").strip()
            }
            
        except httpx.ConnectError:
            return {"error": "Llama engine is not running. Start the llama-server first!"}
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Bind to Tailscale interface only for better isolation
    uvicorn.run(app, host="0.0.0.0", port=8000)
