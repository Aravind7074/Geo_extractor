import pandas as pd
import google.generativeai as genai
import os
import time
import json
from PIL import Image

# Initialize AI with Cloud Secrets
def get_ai_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def process_uploaded_files(files):
    """Processes a list of files from memory. Returns (Status_Msg, DataFrame)"""
    model = get_ai_model()
    if not model:
        return "❌ API Key Missing in Cloud Secrets", pd.DataFrame()

    results = []
    for file in files:
        try:
            img = Image.open(file)
            prompt = "Identify this landmark. Return ONLY JSON: {'lat': float, 'lng': float, 'name': str}"
            response = model.generate_content([prompt, img])
            
            # Clean and parse JSON
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)
            
            results.append({
                "File": file.name,
                "Lat": data.get('lat'),
                "Lon": data.get('lng'),
                "Source": "AI Neural Vision",
                "landmark": data.get('name', 'Unknown Node')
            })
            time.sleep(1.2) # Rate limit breather
        except Exception as e:
            print(f"Error: {e}")
            
    if not results:
        return "⚠️ No landmarks recognized in these images.", pd.DataFrame()
        
    return "✅ Intelligence Extraction Successful", pd.DataFrame(results)
