# Chat with Data - Frontend

This is the Streamlit frontend for the Chat with Data platform, providing an intuitive web interface for data analysis conversations.

## Documentation

For complete setup, usage, and deployment instructions, please see the main [README.md](../README.md) in the project root.

## Quick Start

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run development server
streamlit run streamlit_app.py --server.port 8501
```

## Features

- **Interactive Chat Interface** - Natural language data analysis conversations
- **File Upload Support** - CSV, Excel, JSON, and Parquet file handling
- **Real-time Visualizations** - Dynamic charts and graphs using Plotly
- **Multi-Agent Status** - Live updates from CrewAI agent collaboration
- **Session Management** - Persistent conversation history
- **Responsive Design** - Modern, mobile-friendly interface

## Architecture

This frontend provides the user interface layer, featuring:
- Streamlit web application framework
- Real-time communication with FastAPI backend
- File upload and processing capabilities
- Interactive data visualization components
- Multi-agent workflow status display 