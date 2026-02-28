import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from geopy.distance import geodesic
import io
import os
import time
import json
import google.generativeai as genai
from PIL import Image
import re

# ==========================================
# --- 0. AI NEURAL ENGINE (BACKEND CORE) ---
# ==========================================

def get_ai_model():
    """Securely fetches the API key from Cloud Secrets and boots Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def process_uploaded_files(files):
    """Processes images with active UI Telemetry to catch silent cloud errors."""
    model = get_ai_model()
    if not model:
        return "❌ Cloud Security Error: API Key Missing.", pd.DataFrame()

    results = []
    
    for file in files:
        try:
            img = Image.open(file)
            
            prompt = """Identify the landmark in this image. 
            You must reply ONLY with a raw JSON object. Format exactly like this: 
            {"lat": 35.6586, "lng": 139.7454, "name": "Tokyo Tower"}"""
            
            response = model.generate_content([prompt, img])
            
            # --- X-RAY CHECK 1: Did Google's safety filter block the response? ---
            try:
                raw_text = response.text
            except ValueError:
                return f"🚨 AI Safety Block: Google Gemini refused to analyze {file.name} due to safety filters.", pd.DataFrame()
            
            # --- X-RAY CHECK 2: Can we read the JSON? ---
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                
                # ✅ FIX 1: SAFETY CHECK FOR NULL COORDINATES
                # If 'lat' is None (null), fallback to 0.0 immediately
                lat = float(data.get('lat') or 0.0)
                lng = float(data.get('lng') or 0.0)
                
                results.append({
                    "File": file.name,
                    "Lat": lat,
                    "Lon": lng,
                    "Source": "AI Neural Vision",
                    "landmark": data.get('name', 'Unknown Node')
                })
            else:
                return f"🚨 Format Error! The AI replied with: {raw_text}", pd.DataFrame()
                
            time.sleep(2.0) 
            
        except Exception as e:
            return f"🚨 System Crash on {file.name}: {str(e)}", pd.DataFrame()
            
    if not results:
        return "⚠️ AI Neural Vision could not extract recognizable landmarks.", pd.DataFrame()
        
    return "✅ Neural Intelligence Extraction Successful.", pd.DataFrame(results)

# ==========================================
# --- 1. PAGE SETUP & CYBER-THEME ---
# ==========================================
st.set_page_config(page_title="M2 Geo-Forensics Engine", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e0e0e0; font-family: 'Courier New', Courier, monospace; }
    
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(0, 242, 255, 0.2);
    }

    [data-testid="stMetricValue"] { color: #00f2ff !important; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); }
    
    div[data-testid="stElementContainer"] > div[style*="border"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(0, 242, 255, 0.15) !important;
        border-radius: 10px !important;
    }

    .terminal-box {
        background: rgba(0, 0, 0, 0.7); color: #00ff41; padding: 10px;
        font-size: 0.8rem; border-left: 2px solid #00ff41; margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# --- 2. SESSION INITIALIZATION ---
# ==========================================
if "all_nodes" not in st.session_state:
    st.session_state.all_nodes = []
if "total_distance" not in st.session_state:
    st.session_state.total_distance = 0.0

# ==========================================
# --- 3. SIDEBAR RECON CORE ---
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color:#00f2ff;'>🛡️ RECON CORE</h2>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Inject Forensic Media", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    st.divider()
    
    show_heatmap = st.checkbox("Toggle Evidence Heatmap", value=False)
    show_cctv = st.checkbox("Overlay CCTV Coverage", value=False)
    
    if uploaded_files:
        if st.button("🚀 INITIATE AI RECONNAISSANCE", use_container_width=True):
            with st.spinner("Executing Neural Extraction Pipeline..."):
                # Reset memory for fresh injection
                st.session_state.all_nodes = []
                st.session_state.total_distance = 0.0
                
                # CALL INTEGRATED BACKEND
                msg, df = process_uploaded_files(uploaded_files)
                
                if not df.empty:
                    for _, row in df.iterrows():
                        # Link back to the original file for the Gallery view
                        orig_file = next(f for f in uploaded_files if f.name == row['File'])
                        
                        # ✅ FIX 2: STANDARD GOOGLE MAPS URL
                        clean_url = f"https://www.google.com/maps?q={row['Lat']},{row['Lon']}"
                        
                        st.session_state.all_nodes.append({
                            "name": row['File'], 
                            "lat": row['Lat'], 
                            "lon": row['Lon'],
                            "landmark": row.get('landmark', 'Identified Node'),
                            "source": row['Source'],
                            "color": "#00f2ff" if "AI" in row['Source'] else "#FF3B30",
                            "img": orig_file, 
                            "url": clean_url
                        })
                    
                    # Calculate total trajectory distance
                    if len(st.session_state.all_nodes) > 1:
                        dist = 0.0
                        for i in range(len(st.session_state.all_nodes)-1):
                            dist += geodesic(
                                (st.session_state.all_nodes[i]['lat'], st.session_state.all_nodes[i]['lon']), 
                                (st.session_state.all_nodes[i+1]['lat'], st.session_state.all_nodes[i+1]['lon'])
                            ).km
                        st.session_state.total_distance = dist
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown(f"""<div class="terminal-box">
        [SYS]: M2 Engine Active<br>[SCAN]: {len(st.session_state.all_nodes)} Nodes<br>[STATUS]: Analysis Live
    </div>""", unsafe_allow_html=True)

# ==========================================
# --- 4. MAIN DASHBOARD ---
# ==========================================
st.title("📍 GEOSPATIAL FORENSIC ENGINE")

all_nodes = st.session_state.all_nodes
total_distance = st.session_state.total_distance

if all_nodes:
    # Temporal Timeline Slider
    st.markdown("### 🕒 Temporal Investigation Playback")
    if len(all_nodes) > 1:
        step = st.slider("Reconstruct movement timeline", 1, len(all_nodes), len(all_nodes))
    else:
        step = 1
        st.info("Single node detected. Upload more media to unlock timeline.")
    
    processed_data = all_nodes[:step]

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("ACTIVE NODES", len(processed_data))
    m2.metric("TRAJECTORY", f"{total_distance:.2f} KM")
    m3.metric("TIMELINE STEP", f"{step} / {len(all_nodes)}")

    st.divider()

    # Map & Data View
    col_left, col_right = st.columns([2.5, 1])
    
    with col_left:
        st.subheader("Satellite Recon Map")
        if processed_data:
            # Start map at latest node
            m = folium.Map(location=[processed_data[-1]['lat'], processed_data[-1]['lon']], zoom_start=16)
            
            # Satellite Base Layer
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satellite Recon', overlay=False
            ).add_to(m)

            if show_heatmap:
                HeatMap([[d['lat'], d['lon']] for d in processed_data]).add_to(m)

            if len(processed_data) > 1:
                folium.PolyLine([[d['lat'], d['lon']] for d in processed_data], color="#00f2ff", weight=4).add_to(m)

            for d in processed_data:
                # ----------------------------------------------------
                # POPUP WITH WORKING NAVIGATION LINK
                # ----------------------------------------------------
                popup_html = f"""
                <div style="font-family: monospace; width: 180px;">
                    <b>NODE:</b> {d['landmark']}<br>
                    <b>SRC:</b> {d['source']}<br>
                    <hr style="margin:5px 0;">
                    <a href="{d['url']}" target="_blank" 
                       style="background-color: {d['color']}; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; display: block; text-align: center; font-weight: bold;">
                       🚀 OPEN MAPS
                    </a>
                </div>
                """
                
                # High-tech pulsing marker
                icon_html = f"""<div style="width:14px; height:14px; background:{d['color']}; border-radius:50%; box-shadow:0 0 10px {d['color']}; border: 2px solid white;"></div>"""
                
                folium.Marker(
                    [d['lat'], d['lon']],
                    popup=folium.Popup(popup_html, max_width=250),
                    icon=folium.DivIcon(html=icon_html)
                ).add_to(m)
                
                if show_cctv:
                    folium.Circle([d['lat'], d['lon']], radius=100, color='#FFD700', fill=True, fill_opacity=0.05).add_to(m)

            # THE ANTI-FLICKER FIX
            st_folium(m, use_container_width=True, height=550, returned_objects=[])

    with col_right:
        st.subheader("Intelligence Stream")
        st.dataframe(pd.DataFrame(processed_data)[['name', 'source', 'landmark']], height=510, use_container_width=True)

    # RECON GALLERY
    st.markdown("---")
    st.subheader("🖼️ RECONNAISSANCE GALLERY")
    
    # We use a loop for rows of 4
    if processed_data:
        cols = st.columns(4)
        for i, d in enumerate(processed_data):
            with cols[i % 4]:
                with st.container(border=True):
                    st.image(d['img'], use_container_width=True)
                    st.markdown(f"<p style='color:{d['color']}; font-weight:bold; font-size: 0.8rem;'>NODE {i+1}: {d['landmark']}</p>", unsafe_allow_html=True)
                    st.link_button("🚀 NAVIGATE", d['url'], use_container_width=True)
else:
    st.info("🛰️ **System Standby.** Inject forensic images via the sidebar to initialize tracking.")
