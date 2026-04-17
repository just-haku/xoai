import os
import requests
from dotenv import load_dotenv

def fetch_google_models(api_key: str):
    """
    Fetches available models directly from the Google Gemini REST API.
    This is highly useful for your Intelligent API Pool as it doesn't 
    require heavy SDK dependencies, just raw HTTP requests.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Successfully authenticated with Google API.")
        print("-" * 50)
        
        # Filter and display the models
        available_models = []
        for model in data.get("models", []):
            # We only care about models that can generate content (chat/text/multimodal)
            if "generateContent" in model.get("supportedGenerationMethods", []):
                available_models.append(model['name'])
                print(f"🤖 Model Name: {model['name']}")
                print(f"   Display: {model['displayName']}")
                print(f"   Context Window: {model.get('inputTokenLimit', 'Unknown')} tokens")
                print("-" * 50)
                
        return available_models

    except requests.exceptions.HTTPError as e:
        print(f"❌ API Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"❌ Request Failed: {str(e)}")


# ==========================================
# Run the script
# ==========================================
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Replace with your actual API key, or pull from .env
    API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
    
    if API_KEY == "YOUR_API_KEY_HERE" or not API_KEY:
        print("⚠️ Please set 'GEMINI_API_KEY' with your actual Google API Key in the .env file.")
    else:
        fetch_google_models(API_KEY)
