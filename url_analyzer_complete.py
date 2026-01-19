import streamlit as st
import pandas as pd
import numpy as np
from urllib.parse import urlparse
import requests
from xml.etree import ElementTree as ET
from collections import defaultdict, OrderedDict
import io
import re

# Configuración de página
st.set_page_config(
    page_title="URL Directory Analyzer",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
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
    .metric-box {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #333;
    }
    .metric-sublabel {
        font-size: 0.75rem;
        color: #999;
        margin-top: 0.3rem;
    }
    .directory-item {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #667eea;
    }
    .url-table {
        font-size: 0.9rem;
    }
    .code-200 { color: #10b981; font-weight: bold; }
    .code-301 { color: #f59e0b; font-weight: bold; }
    .code-410 { color: #ef4444; font-weight: bold; }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Funciones auxiliares
@st.cache_data
def load_csv_file(file):
    """Cargar archivo CSV de Screaming Frog"""
    try:
        df = pd.read_csv(file, encoding='utf-8-sig')
        return df
    except:
        try:
            df = pd.read_csv(file, encoding='latin-1')
            return df
        except Exception as e:
            st.error(f"Error al cargar el CSV: {str(e)}")
            return None

def fetch_sitemap_urls(sitemap_url):
    """Obtener URLs desde un sitemap XML"""
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        for url_elem in root.findall('.//ns:loc', namespace):
            urls.append(url_elem.text)
        
        return urls
    except Exception as e:
        st.error(f"Error al obtener el sitemap: {str(e)}")
        return None

def parse_url_structure(url):
    """Parsear URL para obtener dominio, path y partes"""
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path if parsed.path else "/"
        
        # Extraer partes del path
        parts = [p for p in path.split('/') if p]
        
        return domain, path, parts
    except:
        return None, None, []

def get_subdomain(url):
    """Extraer subdominio"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return None

def build_directory_structure(df, filter_codes=None, subdomain_filter=None):
    """Construir estructura de directorios"""
    
    if filter_codes and len(filter_codes) > 0:
        df = df[df['Código de respuesta'].astype(str).isin([str(c) for c in filter_codes])]
    
    structure = defaultdict(list)
    
    for idx, row in df.iterrows():
        url = row.get('Dirección', '')
        if not url or pd.isna(url):
            continue
        
        domain, path, parts = parse_url_structure(url)
        
        if not domain or not path:
            continue
        
        # Filtrar por subdominio
        if subdomain_filter and subdomain_filter != "Todos":
            current_subdomain = get_subdomain(url)
            if current_subdomain != subdomain_filter:
                continue
        
        # Categorizar por primer directorio
        if not parts or path == "/":
            key = "/"
        else:
            key = f"/{parts[0]}"
        
        structure[key].append(row)
    
    return structure

def calculate_metrics(rows_list):
    """Calcular métricas agregadas"""
    if not rows_list:
        return {
            'urls': 0,
            'sessions': 0,
            'clics': 0,
            'impresiones': 0
        }
    
    df = pd.DataFrame(rows_list)
    
    sessions = pd.to_numeric(df.get('GA4 Sessions', 0), errors='coerce').fillna(0).sum()
    clics = pd.to_numeric(df.get('Clics', 0), errors='coerce').fillna(0).sum()
    impresiones = pd.to_numeric(df.get('Impresiones', 0), errors='coerce').fillna(0).sum()
    
    return {
        'urls': len(df),
        'sessions': int(sessions),
        'clics': int(clics),
        'impresiones': int(impresiones)
    }

def format_number(num):
    """Formatear números grandes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))

# Interfaz principal
st.markdown("""
<div class="header-container">
    <div class="header-title">🔗 URL Directory Analyzer</div>
    <div class="header-subtitle">Sube tu exportación de Screaming Frog o un sitemap XML para visualizar la estructura de URLs por directorio</div>
</div>
""", unsafe_allow_html=True)

# Sidebar - Carga de datos
with st.sidebar:
    st.markdown("### 📤 Fuente de Datos")
    
    data_source = st.radio(
        "Elige tu fuente:",
        ["📄 CSV (Screaming Frog)", "🌐 Sitemap XML"],
        label_visibility="collapsed"
    )
    
    df = None
    
    if data_source == "📄 CSV (Screaming Frog)":
        uploaded_file = st.file_uploader("Sube tu CSV", type=['csv'])
        if uploaded_file:
            df = load_csv_file(uploaded_file)
            if df is not None:
                st.success(f"✅ Cargadas {len(df)} URLs")
    else:
        sitemap_url = st.text_input(
            "URL del Sitemap",
            placeholder="https://example.com/sitemap.xml"
        )
        if st.button("Obtener URLs", use_container_width=True):
            if sitemap_url:
                with st.spinner("Descargando sitemap..."):
                    urls = fetch_sitemap_urls(sitemap_url)
                    if urls:
                        df = pd.DataFrame({'Dirección': urls})
                        st.success(f"✅ Cargadas {len(urls)} URLs del sitemap")

# Si hay datos cargados
if df is not None and len(df) > 0:
    
    # Sidebar - Filtros
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filtros")
    
    # Filtro de subdominios
    df['Subdominio'] = df['Dirección'].apply(get_subdomain)
    subdomains = sorted([s for s in df['Subdominio'].unique() if s])
    
    selected_subdomain = st.sidebar.selectbox(
        "Subdominio",
        ["Todos"] + subdomains,
        key="subdomain_select"
    )
    
    # Filtro de códigos de respuesta
    if 'Código de respuesta' in df.columns:
        codes = sorted(df['Código de respuesta'].dropna().unique())
        selected_codes = st.sidebar.multiselect(
            "Códigos de Respuesta",
            codes,
            default=codes,
            key="codes_select"
        )
    else:
        selected_codes = None
    
    # Aplicar filtros
    df_filtered = df.copy()
    
    if selected_codes:
        df_filtered = df_filtered[df_filtered['Código de respuesta'].astype(str).isin([str(c) for c in selected_codes])]
    
    if selected_subdomain != "Todos":
        df_filtered = df_filtered[df_filtered['Subdominio'] == selected_subdomain]
    
    # Header con dominio
    if len(df_filtered) > 0:
        domain_info = get_subdomain(df_filtered['Dirección'].iloc[0])
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                    padding: 1.5rem; border-radius: 8px; color: white; margin-bottom: 2rem;">
            <div style="font-size: 1.8rem; font-weight: bold; margin-bottom: 0.3rem;">{domain_info}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Análisis de estructura de URLs</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Métricas principales
        st.markdown("### 📊 Resumen General")
        
        general_metrics = calculate_metrics(df_filtered.to_dict('records'))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-box">
                <div class="metric-label">Total URLs</div>
                <div class="metric-value">""" + format_number(general_metrics['urls']) + """</div>
                <div class="metric-sublabel">Analizadas</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-box">
                <div class="metric-label">Sesiones GA4</div>
                <div class="metric-value">""" + format_number(general_metrics['sessions']) + """</div>
                <div class="metric-sublabel">Total acumulado</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-box">
                <div class="metric-label">Clics GSC</div>
                <div class="metric-value">""" + format_number(general_metrics['clics']) + """</div>
                <div class="metric-sublabel">Search Console</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-box">
                <div class="metric-label">Impresiones</div>
                <div class="metric-value">""" + format_number(general_metrics['impresiones']) + """</div>
                <div class="metric-sublabel">Search Console</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # URLs en raíz
        st.markdown("### 🏠 URLs en Raíz del Dominio")
        
        root_urls = []
        for idx, row in df_filtered.iterrows():
            domain, path, parts = parse_url_structure(row['Dirección'])
            if path == "/" or not parts:
                root_urls.append(row)
        
        if root_urls:
            root_metrics = calculate_metrics(root_urls)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("URLs en Raíz", root_metrics['urls'])
            with col2:
                st.metric("Sesiones", root_metrics['sessions'])
            with col3:
                st.metric("Clics", root_metrics['clics'])
            with col4:
                st.metric("Impresiones", root_metrics['impresiones'])
            
            # Tabla de URLs en raíz
            root_df = pd.DataFrame(root_urls)
            cols_to_show = ['Dirección', 'GA4 Sessions', 'Clics', 'Impresiones', 'H1-1']
            cols_to_show = [c for c in cols_to_show if c in root_df.columns]
            
            if cols_to_show:
                display_df = root_df[cols_to_show].copy()
                display_df.columns = ['URL', 'Sesiones', 'Clics', 'Impresiones', 'H1']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Exportar URLs de raíz
            csv_root = root_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar URLs de Raíz",
                data=csv_root,
                file_name="urls_root.csv",
                mime="text/csv",
                key="download_root"
            )
        
        st.markdown("---")
        
        # Estructura de directorios
        st.markdown("### 📁 Estructura de Directorios")
        st.markdown("Ordenados por sesiones de GA4")
        
        structure = build_directory_structure(
            df_filtered,
            filter_codes=selected_codes,
            subdomain_filter=selected_subdomain if selected_subdomain != "Todos" else None
        )
        
        # Ordenar por sesiones
        sorted_structure = OrderedDict(
            sorted(
                structure.items(),
                key=lambda x: calculate_metrics(x[1])['sessions'],
                reverse=True
            )
        )
        
        # Eliminar raíz si existe
        if "/" in sorted_structure:
            del sorted_structure["/"]
        
        # Mostrar directorios
        for directory, urls in sorted_structure.items():
            metrics = calculate_metrics(urls)
            
            with st.expander(
                f"📁 {directory} ({metrics['urls']} URLs • {format_number(metrics['sessions'])} sesiones)",
                expanded=False
            ):
                # Métricas del directorio
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("URLs", metrics['urls'])
                with col2:
                    st.metric("Sesiones GA4", metrics['sessions'])
                with col3:
                    st.metric("Clics", metrics['clics'])
                with col4:
                    st.metric("Impresiones", metrics['impresiones'])
                
                # Tabla de URLs
                st.markdown(f"**URLs en {directory}:**")
                
                urls_df = pd.DataFrame(urls)
                cols_to_show = ['Dirección', 'GA4 Sessions', 'Clics', 'Impresiones', 'Código de respuesta', 'H1-1']
                cols_to_show = [c for c in cols_to_show if c in urls_df.columns]
                
                if cols_to_show:
                    display_df = urls_df[cols_to_show].copy()
                    display_df.columns = ['URL', 'Sesiones', 'Clics', 'Impresiones', 'Código', 'H1']
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Exportar URLs del directorio
                csv_dir = urls_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label=f"📥 Descargar URLs de {directory}",
                    data=csv_dir,
                    file_name=f"urls_{directory.replace('/', '_').strip('_')}.csv",
                    mime="text/csv",
                    key=f"download_{directory}"
                )
        
        st.markdown("---")
        
        # Tabla detallada
        with st.expander("📋 Ver Todas las URLs Filtradas", expanded=False):
            cols_to_show = ['Dirección', 'GA4 Sessions', 'GA4 Views', 'Clics', 'Impresiones', 'Código de respuesta', 'H1-1']
            cols_to_show = [c for c in cols_to_show if c in df_filtered.columns]
            
            if cols_to_show:
                display_all = df_filtered[cols_to_show].copy()
                st.dataframe(display_all, use_container_width=True, hide_index=True)
            
            # Exportar todas las URLs
            csv_all = df_filtered.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Descargar Todas las URLs",
                data=csv_all,
                file_name="urls_completas.csv",
                mime="text/csv",
                key="download_all"
            )

else:
    # Mensaje inicial
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📄 Archivo CSV
        Exporta desde Screaming Frog:
        1. Internal HTML
        2. Selecciona todas
        3. Click derecho → Export
        4. Formato: CSV
        """)
    
    with col2:
        st.markdown("""
        ### 🌐 Sitemap XML
        O usa un sitemap XML:
        1. Encuentra tu sitemap.xml
        2. Introduce la URL
        3. Haz click en obtener URLs
        """)
    
    with col3:
        st.markdown("""
        ### ✨ Características
        - 🏗️ Estructura jerárquica
        - 📊 Métricas de GA4/GSC
        - 🏷️ Múltiples subdominios
        - 📥 Exportar a CSV
        - 🔍 Filtros avanzados
        """)
