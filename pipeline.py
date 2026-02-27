import os
import json
import exifread
import folium
from google import genai
from PIL import Image
from dotenv import load_dotenv
import pandas as pd 

# --- 1. CONFIGURATION & SETUP ---
# Load environment variables immediately
load_dotenv()

# Grab the API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found. Check your .env file.")

# Initialize the Gemini Client
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"❌ Error initializing Gemini Client: {e}")

# --- 2. HELPER FUNCTIONS ---
def convert_to_degrees(value):
    """Converts EXIF GPS format (Degrees, Minutes, Seconds) to Decimal."""
    d = value.values[0]
    m = value.values[1]
    s = value.values[2]
    return (d.num / d.den) + (m.num / m.den / 60.0) + (s.num / s.den / 3600.0)

# --- 3. CORE LOGIC: IMAGE PROCESSING ---
def process_images(folder):
    """
    Scans a folder, extracts GPS (EXIF) or asks AI (Gemini), 
    and returns a Map object and a list of data points.
    """
    all_pts = []
    
    if not os.path.exists(folder):
        return None, []

    print(f"\n📂 Scanning folder: {folder}...")

    for f in os.listdir(folder):
        if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            continue
            
        path = os.path.join(folder, f)
        print(f"\n[+] Processing: {f}")
        
        # ---------------------------------------------------------
        # STRATEGY A: EXIF DATA (Fast & Accurate)
        # ---------------------------------------------------------
        found_exif = False
        try:
            with open(path, 'rb') as img:
                tags = exifread.process_file(img)
            
            lat_tag = tags.get('GPS GPSLatitude')
            lat_ref = tags.get('GPS GPSLatitudeRef')
            lng_tag = tags.get('GPS GPSLongitude')
            lng_ref = tags.get('GPS GPSLongitudeRef')

            if lat_tag and lng_tag and lat_ref and lng_ref:
                lat = convert_to_degrees(lat_tag)
                if lat_ref.values[0] != 'N': lat = -lat
                
                lng = convert_to_degrees(lng_tag)
                if lng_ref.values[0] != 'E': lng = -lng
                
                all_pts.append({
                    'lat': lat, 
                    'lng': lng, 
                    'name': f"GPS Data ({f})",
                    'filename': f,
                    'source': 'EXIF'
                })
                print(f"  ✅ Found exact EXIF coordinates!")
                found_exif = True
        except Exception as e:
            print(f"  ⚠️ Error parsing EXIF: {e}")

        if found_exif:
            continue

        # ---------------------------------------------------------
        # STRATEGY B: GEMINI AI (The Brains)
        # ---------------------------------------------------------
        print(f"  🔍 No usable GPS. Booting Gemini AI...")
        try:
            img_data = Image.open(path)
            prompt = """
            Identify the landmark in this photo. Return ONLY a JSON object:
            {"name": "Landmark Name", "lat": 0.0, "lng": 0.0, "desc": "1-sentence context"}
            If unknown or generic, return {"error": "unknown"}.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash', # ✅ SWITCHED TO STABLE MODEL
                contents=[prompt, img_data]
            )
            
            # Clean the response text to ensure valid JSON
            raw_text = response.text.replace('```json', '').replace('```', '').strip()
            
            # Sometimes the model adds extra text, try to find the JSON start/end
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                raw_text = raw_text[start_idx:end_idx]

            data = json.loads(raw_text)
            
            if "error" not in data:
                all_pts.append({
                    'lat': data['lat'], 
                    'lng': data['lng'], 
                    'name': data['name'],
                    'filename': f,
                    'desc': data.get('desc', ''),
                    'source': 'AI'
                })
                print(f"  📍 AI found: {data['name']}")
            else:
                print("  ❌ AI could not identify a landmark.")
        except Exception as e:
            print(f"  ⚠️ AI Error: {e}")

    # ---------------------------------------------------------
    # MAP GENERATION
    # ---------------------------------------------------------
    if all_pts:
        print(f"\n🗺️ Generating Investigative Map with {len(all_pts)} points...")
        # Center map on the first point found
        m = folium.Map(location=[all_pts[0]['lat'], all_pts[0]['lng']], zoom_start=4)
        
        for p in all_pts:
            # Color coding: Green for EXIF, Red for AI guesses
            color = "green" if p['source'] == 'EXIF' else "red"
            icon_type = "ok-sign" if p['source'] == 'EXIF' else "camera"
            
            popup_html = f"<b>{p['name']}</b><br>Source: <b>{p['source']}</b>"
            if 'desc' in p:
                popup_html += f"<br><i>{p['desc']}</i>"
                
            folium.Marker(
                [p['lat'], p['lng']], 
                popup=popup_html,
                icon=folium.Icon(color=color, icon=icon_type)
            ).add_to(m)
            
        return m, all_pts
    else:
        print("\n⚠️ No data found to map.")
        return None, []

# --- 4. STREAMLIT ADAPTER ---
def process_uploaded_files(uploaded_files):
    """
    Adapter function for Streamlit: Takes memory files, saves them, 
    runs the AI pipeline, and returns the formatted map and dataframe.
    """
    TEMP_FOLDER = "streamlit_temp_evidence"
    
    # 1. Create a fresh temp folder
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    else:
        # Clear out old evidence so we don't re-process old files
        for f in os.listdir(TEMP_FOLDER):
            try:
                os.remove(os.path.join(TEMP_FOLDER, f))
            except Exception:
                pass # Skip if file is locked

    # 2. Save Streamlit's memory files to the hard drive
    for file in uploaded_files:
        with open(os.path.join(TEMP_FOLDER, file.name), "wb") as f:
            f.write(file.getbuffer())

    # 3. Run the pipeline on the new folder
    investigation_map, raw_data = process_images(TEMP_FOLDER)

    # 4. Format the data for Streamlit Display & PDF
    if raw_data:
        formatted_data = []
        for item in raw_data:
            formatted_data.append({
                "File": item.get("filename", "Unknown"),
                "Lat": item.get("lat", 0.0),
                "Lon": item.get("lng", 0.0),
                "Source": item.get("source", "AI Detected")
            })
        df = pd.DataFrame(formatted_data)
    else:
        df = pd.DataFrame()

    return investigation_map, df

# --- 5. EXECUTION GUARD ---
if __name__ == "__main__":
    # This block allows you to test pipeline.py manually without running the app
    TEST_FOLDER = "evidence_images"
    process_images(TEST_FOLDER)