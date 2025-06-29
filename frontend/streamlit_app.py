import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from streamlit_chat import message
import json
import time
from typing import Dict, List, Optional
import os
import sys

# Add config to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import get_frontend_settings

# Get settings
settings = get_frontend_settings()

# Page configuration
st.set_page_config(
    page_title=settings.app_name,
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2rem;
    }
    
    .chat-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem;
    }
    
    .upload-zone {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background-color: #f8f9fa;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class ChatApp:
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(int(time.time()))
        if "data_source" not in st.session_state:
            st.session_state.data_source = None
        if "data_preview" not in st.session_state:
            st.session_state.data_preview = None
        if "connection_status" not in st.session_state:
            st.session_state.connection_status = False

    def render_header(self):
        """Render the main header"""
        st.markdown('<h1 class="main-header">💬 Chat with Data</h1>', unsafe_allow_html=True)
        st.markdown("---")

    def render_sidebar(self):
        """Render the sidebar with data source options"""
        with st.sidebar:
            st.header("🔧 Data Configuration")
            
            # Data source selection
            data_source_type = st.selectbox(
                "Select Data Source",
                ["Upload File", "Database Connection", "Sample Data"],
                key="data_source_type"
            )
            
            if data_source_type == "Upload File":
                self.handle_file_upload()
            elif data_source_type == "Database Connection":
                self.handle_database_connection()
            elif data_source_type == "Sample Data":
                self.handle_sample_data()
            
            st.divider()
            
            # Connection status
            status_color = "🟢" if st.session_state.connection_status else "🔴"
            st.markdown(f"**Connection Status:** {status_color}")
            
            # Chat history management
            st.header("💾 Chat Management")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Clear Chat", use_container_width=True):
                    st.session_state.messages = []
                    st.rerun()
            with col2:
                if st.button("Export Chat", use_container_width=True):
                    self.export_chat_history()

    def handle_file_upload(self):
        """Handle file upload functionality"""
        st.subheader("📁 Upload Data File")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['csv', 'xlsx', 'xls', 'json'],
            help="Supported formats: CSV, Excel, JSON"
        )
        
        if uploaded_file:
            try:
                # Send file to backend
                files = {"file": uploaded_file.getvalue()}
                response = requests.post(
                    f"{settings.get_backend_url()}/upload-file",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                    timeout=settings.api_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.data_source = result
                    st.session_state.connection_status = True
                    st.success("✅ File uploaded successfully!")
                    
                    # Show preview
                    if "preview" in result:
                        st.session_state.data_preview = result["preview"]
                        with st.expander("📊 Data Preview"):
                            df = pd.DataFrame(result["preview"])
                            st.dataframe(df, use_container_width=True)
                else:
                    st.error("❌ Failed to upload file")
                    
            except Exception as e:
                st.error(f"❌ Error uploading file: {str(e)}")

    def handle_database_connection(self):
        """Handle database connection functionality"""
        st.subheader("🗄️ Database Connection")
        
        db_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL", "SQLite", "MongoDB"])
        
        if db_type in ["PostgreSQL", "MySQL"]:
            host = st.text_input("Host", value="localhost")
            port = st.number_input("Port", value=5432 if db_type == "PostgreSQL" else 3306)
            database = st.text_input("Database Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Test Connection", use_container_width=True):
                connection_data = {
                    "type": db_type.lower(),
                    "host": host,
                    "port": port,
                    "database": database,
                    "username": username,
                    "password": password
                }
                
                try:
                    response = requests.post(
                        f"{settings.get_backend_url()}/connect-database", 
                        json=connection_data,
                        timeout=settings.api_timeout
                    )
                    if response.status_code == 200:
                        st.session_state.data_source = connection_data
                        st.session_state.connection_status = True
                        st.success("✅ Database connected successfully!")
                    else:
                        st.error("❌ Failed to connect to database")
                except Exception as e:
                    st.error(f"❌ Connection error: {str(e)}")

    def handle_sample_data(self):
        """Handle sample data selection"""
        st.subheader("📋 Sample Data")
        
        sample_datasets = [
            "Sales Data",
            "Customer Analytics",
            "Financial Reports",
            "E-commerce Transactions"
        ]
        
        selected_sample = st.selectbox("Choose Sample Dataset", sample_datasets)
        
        if st.button("Load Sample Data", use_container_width=True):
            try:
                response = requests.post(
                    f"{settings.get_backend_url()}/load-sample-data", 
                    json={"dataset": selected_sample},
                    timeout=settings.api_timeout
                )
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.data_source = result
                    st.session_state.connection_status = True
                    st.success("✅ Sample data loaded successfully!")
                else:
                    st.error("❌ Failed to load sample data")
            except Exception as e:
                st.error(f"❌ Error loading sample data: {str(e)}")

    def render_chat_interface(self):
        """Render the main chat interface"""
        st.header("💬 Chat Interface")
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display chat messages
            for i, msg in enumerate(st.session_state.messages):
                if msg["role"] == "user":
                    message(msg["content"], is_user=True, key=f"user_{i}")
                else:
                    message(msg["content"], key=f"assistant_{i}")
                    
                    # Display any charts or data
                    if "data" in msg:
                        self.render_data_visualization(msg["data"])

        # Chat input
        if st.session_state.connection_status:
            user_input = st.chat_input("Ask something about your data...")
            
            if user_input:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Get response from backend
                with st.spinner("🤖 Analyzing your query..."):
                    response = self.get_chat_response(user_input)
                
                # Add assistant response
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response.get("message", "Sorry, I couldn't process that request."),
                    "data": response.get("data")
                })
                
                st.rerun()
        else:
            st.info("👆 Please configure a data source in the sidebar to start chatting!")

    def get_chat_response(self, user_input: str) -> Dict:
        """Get response from the backend chat API"""
        try:
            payload = {
                "message": user_input,
                "session_id": st.session_state.session_id,
                "data_source": st.session_state.data_source
            }
            
            response = requests.post(
                f"{settings.get_backend_url()}/chat", 
                json=payload,
                timeout=settings.api_timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"message": "Sorry, there was an error processing your request."}
                
        except Exception as e:
            return {"message": f"Connection error: {str(e)}"}

    def render_data_visualization(self, data: Dict):
        """Render data visualizations"""
        if not data:
            return
            
        if "chart" in data:
            chart_data = data["chart"]
            chart_type = chart_data.get("type", "bar")
            
            df = pd.DataFrame(chart_data["data"])
            
            if chart_type == "bar":
                fig = px.bar(df, x=chart_data.get("x"), y=chart_data.get("y"))
            elif chart_type == "line":
                fig = px.line(df, x=chart_data.get("x"), y=chart_data.get("y"))
            elif chart_type == "scatter":
                fig = px.scatter(df, x=chart_data.get("x"), y=chart_data.get("y"))
            else:
                fig = px.bar(df, x=chart_data.get("x"), y=chart_data.get("y"))
                
            st.plotly_chart(fig, use_container_width=True)
        
        if "table" in data:
            df = pd.DataFrame(data["table"])
            st.dataframe(df, use_container_width=True)

    def render_analytics_dashboard(self):
        """Render analytics dashboard"""
        if not st.session_state.connection_status:
            st.info("Connect a data source to view analytics")
            return
            
        st.header("📊 Analytics Dashboard")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", len(st.session_state.messages) // 2)
        with col2:
            st.metric("Data Sources", 1 if st.session_state.data_source else 0)
        with col3:
            st.metric("Session Time", f"{int(time.time() - int(st.session_state.session_id))}s")
        with col4:
            st.metric("Status", "Connected" if st.session_state.connection_status else "Disconnected")
        
        # Recent queries
        if st.session_state.messages:
            st.subheader("Recent Queries")
            recent_queries = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"][-5:]
            for i, query in enumerate(recent_queries, 1):
                st.write(f"{i}. {query}")

    def export_chat_history(self):
        """Export chat history to JSON"""
        if st.session_state.messages:
            chat_data = {
                "session_id": st.session_state.session_id,
                "messages": st.session_state.messages,
                "timestamp": time.time()
            }
            
            st.download_button(
                "Download Chat History",
                data=json.dumps(chat_data, indent=2),
                file_name=f"chat_history_{st.session_state.session_id}.json",
                mime="application/json"
            )

    def run(self):
        """Main application runner"""
        self.render_header()
        
        # Navigation menu
        selected = option_menu(
            menu_title=None,
            options=["Chat", "Analytics", "Settings"],
            icons=["chat-dots", "graph-up", "gear"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "25px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#02ab21"},
            }
        )
        
        # Render sidebar
        self.render_sidebar()
        
        # Render main content based on selection
        if selected == "Chat":
            self.render_chat_interface()
        elif selected == "Analytics":
            self.render_analytics_dashboard()
        elif selected == "Settings":
            st.header("⚙️ Settings")
            st.info("Settings panel - Configure app preferences here")

# Run the application
if __name__ == "__main__":
    app = ChatApp()
    app.run() 