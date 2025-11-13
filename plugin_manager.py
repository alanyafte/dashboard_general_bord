# plugin_manager.py
import streamlit as st
import importlib
import sys

class PluginManager:
    def __init__(self):
        self.plugins = []
    
    def cargar_plugins(self):
        """Carga todos los plugins disponibles"""
        plugins_disponibles = [
            "modulo_ia_incidencias",
            "modulo_ia_predicciones" 
        ]
        
        for plugin_name in plugins_disponibles:
            try:
                modulo = importlib.import_module(plugin_name)
                if hasattr(modulo, 'integrar_en_produccion'):
                    config = modulo.integrar_en_produccion()
                    self.plugins.append({
                        'nombre': config['nombre'],
                        'icono': config['icono'],
                        'funcion': config['funcion'],
                        'modulo': modulo
                    })
                    st.sidebar.success(f"✅ {config['nombre']} cargado")
            except ImportError as e:
                st.sidebar.info(f"⚠️ {plugin_name} no disponible")
            except Exception as e:
                st.sidebar.error(f"❌ Error cargando {plugin_name}: {e}")
    
    def mostrar_plugins(self, df_produccion=None, df_calculado=None):
        """Muestra la interfaz de plugins"""
        if not self.plugins:
            st.info("No hay plugins de IA disponibles")
            return
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🤖 Plugins IA")
        
        # Botones en sidebar para cada plugin
        plugin_activo = st.sidebar.radio(
            "Seleccionar Plugin:",
            [p['nombre'] for p in self.plugins],
            index=None
        )
        
        # Mostrar plugin activo
        if plugin_activo:
            plugin = next((p for p in self.plugins if p['nombre'] == plugin_activo), None)
            if plugin:
                st.header(f"{plugin['icono']} {plugin['nombre']}")
                plugin['funcion'](df_produccion, df_calculado)
