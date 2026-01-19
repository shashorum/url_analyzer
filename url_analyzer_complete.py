import streamlit as st
from urllib.parse import urlparse
import requests
from xml.etree import ElementTree as ET
from collections import defaultdict, OrderedDict
import csv
import io

st.set_page_config(
    page_title="URL Directory Analyzer",
    page_icon="🔗",
    layout="wide"
)

st.markdown("""
<style>
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .header-title {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .header-subtitle {
        font-size: 0.95rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

def parse_url_structure(url):
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path if parsed.path else "/"
        parts = [p for p in path.split('/') if p]
        return domain, path, parts
    except:
        return None, None, []

def get_subdomain(url):
    try:
        return urlparse(url).netloc
    except:
        return None

def calculate_metrics(rows_list):
    if not rows_list:
        return {'urls': 0, 'sessions': 0, 'clics': 0, 'impresiones': 0}
    try:
        sessions = sum(int(float(row.get('GA4 Sessions', 0) or 0)) for row in rows_list)
        clics = sum(int(float(row.get('Clics', 0) or 0)) for row in rows_list)
        impresiones = sum(int(float(row.get('Impresiones', 0) or 0)) for row in rows_list)
    except:
        sessions = clics = impresiones = 0
    return {'urls': len(rows_list), 'sessions': sessions, 'clics': clics, 'impresiones': impresiones}

def format_number(num):
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))

st.markdown("""
<div class="header-container">
    <div class="header-title">🔗 URL Directory Analyzer</div>
    <div class="header-subtitle">Sube tu CSV de Screaming Frog</div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Sube tu CSV", type=['csv'])

if uploaded_file:
    try:
        content = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        data = list(reader)
        
        st.success(f"✅ Cargadas {len(data)} URLs")
        
        # Filtro de subdominios
        subdomains = sorted(list(set(get_subdomain(row['Dirección']) for row in data if row.get('Dirección'))))
        selected_subdomain = st.selectbox("Subdominio", subdomains)
        
        # Filtrar
        filtered_data = [row for row in data if get_subdomain(row['Dirección']) == selected_subdomain]
        
        # Métricas
        st.markdown("### 📊 Resumen")
        metrics = calculate_metrics(filtered_data)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total URLs", format_number(metrics['urls']))
        with col2:
            st.metric("Sesiones GA4", format_number(metrics['sessions']))
        with col3:
            st.metric("Clics", format_number(metrics['clics']))
        with col4:
            st.metric("Impresiones", format_number(metrics['impresiones']))
        
        # Directorios
        st.markdown("### 📁 Directorios")
        dir_structure = defaultdict(list)
        for row in filtered_data:
            url = row.get('Dirección', '')
            domain, path, parts = parse_url_structure(url)
            if parts:
                dir_key = f"/{parts[0]}"
                dir_structure[dir_key].append(row)
        
        for directory in sorted(dir_structure.keys()):
            urls = dir_structure[directory]
            metrics = calculate_metrics(urls)
            with st.expander(f"{directory} ({metrics['urls']} URLs)"):
                st.dataframe(urls, use_container_width=True, hide_index=True)
                
    except Exception as e:
        st.error(f"Error: {str(e)}")
