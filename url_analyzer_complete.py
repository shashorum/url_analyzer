import streamlit as st
from urllib.parse import urlparse
import requests
from xml.etree import ElementTree as ET
from collections import defaultdict, OrderedDict
import csv
import io

# Inicializar sesión ANTES que todo
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = None

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
    .subdirectory-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        border-left: 3px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Funciones auxiliares
@st.cache_data
def load_csv_file(file):
    """Cargar archivo CSV sin pandas"""
    try:
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        data = list(reader)
        return data
    except:
        try:
            content = file.read().decode('latin-1')
            reader = csv.DictReader(io.StringIO(content))
            data = list(reader)
            return data
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

def get_subdirectories(data, parent_dir):
    """Obtener subdirectorios dentro de un directorio padre"""
    subdirs = defaultdict(list)
    
    for row in data:
        url = row.get('Dirección', '')
        domain, path, parts = parse_url_structure(url)
        
        if not parts:
            continue
        
        # Obtener el primer nivel del path
        first_level = f"/{parts[0]}"
        
        # Si es el directorio padre y hay más niveles, añadir a subdirectorios
        if first_level == parent_dir and len(parts) > 1:
            subdir = f"/{parts[0]}/{parts[1]}"
            subdirs[subdir].append(row)
        elif first_level == parent_dir:
            # URLs directas del directorio sin subdirectorios
            subdirs['_direct'].append(row)
    
    return subdirs

def calculate_metrics(rows_list):
    """Calcular métricas agregadas"""
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
    
    if data_source == "📄 CSV (Screaming Frog)":
        uploaded_file = st.file_uploader("Sube tu CSV", type=['csv'])
        if uploaded_file:
            data = load_csv_file(uploaded_file)
            if data is not None:
                st.session_state.data_cache = data
                st.success(f"✅ Cargadas {len(data)} URLs")
    else:
        sitemap_url = st.text_input("URL del Sitemap", placeholder="https://example.com/sitemap.xml")
        if st.button("Obtener URLs", use_container_width=True):
            if sitemap_url:
                with st.spinner("Descargando sitemap..."):
                    urls = fetch_sitemap_urls(sitemap_url)
                    if urls:
                        st.session_state.data_cache = [{'Dirección': url} for url in urls]
                        st.success(f"✅ Cargadas {len(urls)} URLs del sitemap")

data = st.session_state.data_cache

# Si hay datos cargados
if data is not None and len(data) > 0:
    
    # Sidebar - Filtros
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filtros Avanzados")
    
    # Filtro de subdominios
    subdomains = sorted(list(set(get_subdomain(row['Dirección']) for row in data if row.get('Dirección'))))
    main_domain = subdomains[0] if subdomains else "N/A"
    selected_subdomain = st.sidebar.selectbox(
        "Subdominio", 
        [main_domain] + [s for s in subdomains if s != main_domain],
        key="subdomain_select"
    )
    
    # Filtro de códigos de respuesta (solo 200 por defecto)
    codes = sorted(list(set(str(row.get('Código de respuesta', '')) for row in data)))
    default_codes = ['200'] if '200' in codes else (codes[:1] if codes else [])
    selected_codes = st.sidebar.multiselect(
        "Códigos de Respuesta",
        codes,
        default=default_codes,
        key="codes_select"
    )
    
    # Aplicar filtros
    filtered_data = [row for row in data 
                     if (not selected_codes or str(row.get('Código de respuesta', '')) in selected_codes)
                     and (selected_subdomain == "Todos" or get_subdomain(row['Dirección']) == selected_subdomain)]
    
    # Header con dominio
    if len(filtered_data) > 0:
        domain_info = get_subdomain(filtered_data[0]['Dirección'])
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                    padding: 1.5rem; border-radius: 8px; color: white; margin-bottom: 2rem;">
            <div style="font-size: 1.8rem; font-weight: bold; margin-bottom: 0.3rem;">{domain_info}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Análisis de estructura de URLs</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Métricas principales
        st.markdown("### 📊 Resumen General")
        general_metrics = calculate_metrics(filtered_data)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total URLs", format_number(general_metrics['urls']))
        with col2:
            st.metric("Sesiones GA4", format_number(general_metrics['sessions']))
        with col3:
            st.metric("Clics GSC", format_number(general_metrics['clics']))
        with col4:
            st.metric("Impresiones", format_number(general_metrics['impresiones']))
        
        st.markdown("---")
        
        # URLs en raíz
        st.markdown("### 🏠 URLs en Raíz del Dominio")
        root_urls = [row for row in filtered_data if parse_url_structure(row['Dirección'])[1] == "/"]
        
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
            
            st.dataframe(root_urls, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Estructura de directorios
        st.markdown("### 📁 Estructura de Directorios")
        
        # Agrupar URLs por directorio principal
        dir_structure = defaultdict(list)
        for row in filtered_data:
            url = row.get('Dirección', '')
            domain, path, parts = parse_url_structure(url)
            
            if not parts or path == "/":
                continue
            
            dir_key = f"/{parts[0]}"
            dir_structure[dir_key].append(row)
        
        # Ordenar por sesiones
        sorted_dirs = OrderedDict(sorted(
            dir_structure.items(),
            key=lambda x: calculate_metrics(x[1])['sessions'],
            reverse=True
        ))
        
        for directory, urls in sorted_dirs.items():
            metrics = calculate_metrics(urls)
            
            with st.expander(f"📁 {directory} ({metrics['urls']} URLs • {format_number(metrics['sessions'])} sesiones)"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("URLs", metrics['urls'])
                with col2:
                    st.metric("Sesiones", metrics['sessions'])
                with col3:
                    st.metric("Clics", metrics['clics'])
                with col4:
                    st.metric("Impresiones", metrics['impresiones'])
                
                # Obtener subdirectorios
                subdirs = get_subdirectories(urls, directory)
                
                if '_direct' in subdirs:
                    st.markdown("#### URLs directas")
                    st.dataframe(subdirs['_direct'], use_container_width=True, hide_index=True)
                
                # Mostrar subdirectorios
                for subdir in sorted(subdirs.keys()):
                    if subdir != '_direct':
                        subdir_urls = subdirs[subdir]
                        subdir_metrics = calculate_metrics(subdir_urls)
                        st.markdown(f"""
                        <div class="subdirectory-box">
                            <strong>{subdir}</strong> • {subdir_metrics['urls']} URLs • {format_number(subdir_metrics['sessions'])} sesiones
                        </div>
                        """, unsafe_allow_html=True)
                        st.dataframe(subdir_urls, use_container_width=True, hide_index=True)

else:
    st.info("Carga un CSV de Screaming Frog o un Sitemap XML para comenzar")
