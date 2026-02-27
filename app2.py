import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder, HeatMap
from geopy.distance import geodesic
from fpdf import FPDF
import random
import io

# --- 1. PAGE SETUP & CYBER-THEME ---
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

# --- 2. LOGIC: PDF GENERATION ---
def create_pdf(data, distance):
    pdf = FPDF()
    pdf.add_page()
    def clean_text(text): return text.encode('ascii', 'ignore').decode('ascii').strip()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 15, "Geo-Forensic Intelligence Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Nodes: {len(data)} | Distance: {distance:.2f} KM", ln=True)
    pdf.set_fill_color(0, 150, 255); pdf.set_text_color(255, 255, 255)
    pdf.cell(80, 10, "Evidence Name", 1, 0, 'C', True)
    pdf.cell(50, 10, "Source", 1, 0, 'C', True)
    pdf.cell(60, 10, "Match", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Helvetica", "", 10)
    for d in data:
        pdf.cell(80, 10, clean_text(d['name'][:30]), 1)
        pdf.cell(50, 10, clean_text(d['source']), 1)
        pdf.cell(60, 10, clean_text(d['landmark']), 1, 1)
    return pdf.output()

# --- 3. DATA PROCESSING ---
import pipeline
from geopy.distance import geodesic

# 1. QUALITY FIX: Give the app "Memory" so the map survives clicks!
if "all_nodes" not in st.session_state:
    st.session_state.all_nodes = []
if "total_distance" not in st.session_state:
    st.session_state.total_distance = 0.0

with st.sidebar:
    st.markdown("<h2 style='color:#00f2ff;'>🛡️ RECON CORE</h2>", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Inject Forensic Media", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    st.divider()
    
    show_heatmap = st.checkbox("Toggle Evidence Heatmap", value=False)
    show_cctv = st.checkbox("Overlay Potential CCTV Coverage", value=False)
    
    # 2. QUALITY FIX: Put the button back so we don't spam the API!
    if uploaded_files:
        if st.button("🚀 INITIATE AI RECONNAISSANCE", use_container_width=True):
            with st.spinner("Executing Neural Extraction Pipeline..."):
                
                # Clear old memory for a fresh run
                st.session_state.all_nodes = [] 
                st.session_state.total_distance = 0.0
                
                _, extracted_df = pipeline.process_uploaded_files(uploaded_files)
                
                if not extracted_df.empty:
                    for i, file in enumerate(uploaded_files):
                        match = extracted_df[extracted_df['File'] == file.name]
                        if not match.empty:
                            lat = match.iloc[0]['Lat']
                            lon = match.iloc[0]['Lon']
                            source = match.iloc[0]['Source']
                            
                            is_ai = "AI" in source.upper() 
                            gmaps_url = f"https://www.google.com/maps?q={lat},{lon}"
                            
                            # Save to Streamlit Memory
                            st.session_state.all_nodes.append({
                                "name": file.name, "lat": lat, "lon": lon,
                                "landmark": "AI Vision Match" if is_ai else "GPS Metadata",
                                "source": source,
                                "color": "#00f2ff" if is_ai else "#FF3B30",
                                "img": file, "url": gmaps_url
                            })
                
                # Calculate real path distance
                if len(st.session_state.all_nodes) > 1:
                    for i in range(len(st.session_state.all_nodes)-1):
                        st.session_state.total_distance += geodesic(
                            (st.session_state.all_nodes[i]['lat'], st.session_state.all_nodes[i]['lon']), 
                            (st.session_state.all_nodes[i+1]['lat'], st.session_state.all_nodes[i+1]['lon'])
                        ).km

    st.markdown(f"""<div class="terminal-box">
        [SYS]: M2 Engine Active & Synced<br>[SCAN]: {len(st.session_state.all_nodes)} Nodes<br>[STATUS]: Analysis Live
    </div>""", unsafe_allow_html=True)

# 3. Alias the memory back to her original variables so the rest of her code works perfectly!
all_nodes = st.session_state.all_nodes
total_distance = st.session_state.total_distance
# --- 4. MAIN DASHBOARD ---
st.title("📍 GEOSPATIAL FORENSIC ENGINE")

if all_nodes:
    st.markdown("### 🕒 Temporal Investigation Playback")
    
    # QUALITY FIX: Only show the slider if there is a timeline (2+ nodes) to reconstruct!
    if len(all_nodes) > 1:
        step = st.slider("Drag to reconstruct the movement timeline", 1, len(all_nodes), len(all_nodes))
    else:
        step = 1
        st.info("Single node detected. Inject more evidence to unlock the timeline slider.")
        
    processed_data = all_nodes[:step] 
else:
    processed_data = []

m1, m2, m3 = st.columns(3)
m1.metric("ACTIVE NODES", len(processed_data))
m2.metric("CURRENT TRAJECTORY", f"{total_distance:.2f} KM")
m3.metric("TIMELINE STEP", f"{step if processed_data else 0} / {len(all_nodes)}")

st.divider()

if processed_data:
    col_left, col_right = st.columns([2.5, 1])
    
    with col_left:
        st.subheader("Satellite Recon Map")
        # Initialize map focused on the latest node
        m = folium.Map(location=[processed_data[-1]['lat'], processed_data[-1]['lon']], zoom_start=17, tiles=None)
        
        # --- SATELLITE VIEW (Default) ---
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite Analysis',
            overlay=False,
            control=True
        ).add_to(m)

        # Dark tiles as an alternative option
        folium.TileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', name="Dark Intelligence", attr='CARTO').add_to(m)
        
        if show_heatmap:
            HeatMap([[d['lat'], d['lon']] for d in processed_data]).add_to(m)
            
        if len(processed_data) > 1:
            folium.PolyLine([[d['lat'], d['lon']] for d in processed_data], color="#00f2ff", weight=4, opacity=0.8).add_to(m)
        
        for d in processed_data:
            # 1. POPUP HTML: High-tech info card with Navigation link
            popup_html = f"""
            <div style="font-family: 'Courier New', monospace; width: 220px; color: #333;">
                <h4 style="margin: 0; color: {d['color']};">FORENSIC NODE</h4>
                <hr style="border: 0.5px solid #ccc;">
                <b>FILE:</b> {d['name']}<br>
                <b>SRC:</b> {d['source']}<br>
                <b>MATCH:</b> {d['landmark']}<br><br>
                <a href="{d['url']}" target="_blank" 
                   style="display: block; text-align: center; background: {d['color']}; color: white; padding: 8px; border-radius: 5px; text-decoration: none; font-weight: bold;">
                   🚀 NAVIGATE TO LOCATION
                </a>
            </div>
            """
            
            # 2. CUSTOM PULSING ICON
            icon_html = f"""
            <div style="position:relative; width:16px; height:16px; background-color:{d['color']}; border-radius:50%; box-shadow:0 0 10px {d['color']};">
                <div style="position:absolute; width:100%; height:100%; border-radius:50%; background-color:{d['color']}; animation:pulse 1.5s infinite; opacity:0.4;"></div>
            </div>
            <style>
                @keyframes pulse {{
                    0% {{ transform: scale(1); opacity: 0.7; }}
                    100% {{ transform: scale(3.5); opacity: 0; }}
                }}
            </style>
            """
            
            folium.Marker(
                [d['lat'], d['lon']], 
                popup=folium.Popup(popup_html, max_width=250), 
                icon=folium.DivIcon(html=icon_html)
            ).add_to(m)

            if show_cctv:
                folium.Circle([d['lat'], d['lon']], radius=100, color='#FFD700', fill=True, fill_opacity=0.1).add_to(m)
            
        folium.LayerControl().add_to(m)
        st_folium(m, use_container_width=True, height=550)

    with col_right:
        st.subheader("Evidence Logs")
        st.dataframe(pd.DataFrame(processed_data)[['name', 'source', 'landmark']], height=510, use_container_width=True)

    # --- GALLERY ---
    st.markdown("---")
    st.subheader("🖼️ RECONNAISSANCE GALLERY")
    g_cols = st.columns(4)
    for i, d in enumerate(processed_data):
        with g_cols[i % 4]:
            with st.container(border=True):
                st.image(d['img'], use_container_width=True)
                st.markdown(f"<p style='color:{d['color']}; font-weight:bold;'>NODE {i+1}</p>", unsafe_allow_html=True)
                st.link_button("EXTERNAL NAV", d['url'], use_container_width=True)

    # --- EXPORT ---
    st.divider()
    pdf_bytes = create_pdf(processed_data, total_distance)
    st.download_button("📂 DOWNLOAD CLASSIFIED REPORT", data=bytes(pdf_bytes), file_name="Forensic_Analysis.pdf", use_container_width=True)

else:
    st.info("⚡ System Standby. Inject forensic images via the sidebar to initialize tracking.")
