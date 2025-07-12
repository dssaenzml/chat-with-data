#!/bin/bash

# Chat with Data - Development Setup Script
# Sets up Python 3.12 environments with UV for CrewAI + LangGraph development

set -e

echo "🚀 Setting up Chat with Data Development Environment"
echo "📋 This script will:"
echo "   • Create Python 3.12 virtual environments"
echo "   • Install UV package manager"
echo "   • Set up backend (CrewAI + LangGraph)"
echo "   • Set up frontend (Streamlit)"
echo ""

# Check if Python 3.12 is available
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is not installed. Please install Python 3.12 first:"
    echo "   https://www.python.org/downloads/"
    echo "   Or use pyenv: pyenv install 3.12.0"
    exit 1
fi

# Check if UV is installed globally
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV package manager globally..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ UV installed globally"
    echo "🔄 Please restart your terminal or run: source ~/.bashrc"
    echo "   Then run this script again."
    exit 0
fi

# Function to create virtual environment
create_env() {
    local env_name=$1
    local description=$2
    
    echo "🐍 Creating virtual environment: $env_name"
    if [ -d "$env_name" ]; then
        echo "⚠️  Environment $env_name already exists. Removing..."
        rm -rf "$env_name"
    fi
    
    python3.12 -m venv "$env_name"
    echo "✅ Created $env_name ($description)"
}

# Create backend environment
create_env "chat-backend" "CrewAI + LangGraph Backend"

# Create frontend environment  
create_env "chat-frontend" "Streamlit Frontend"

# Install backend dependencies
echo ""
echo "🔧 Installing backend dependencies (CrewAI + LangGraph)..."
cd backend
if uv pip install -e ".[dev]"; then
    echo "✅ Backend dependencies installed successfully"
else
    echo "⚠️  Backend dependency installation encountered issues"
    echo "💡 Try running manually: uv pip install -e '.[dev]'"
fi
cd ..

# Install frontend dependencies
echo ""
echo "🔧 Installing frontend dependencies..."
cd frontend
if uv pip install -e ".[dev]"; then
    echo "✅ Frontend dependencies installed successfully"
else
    echo "⚠️  Frontend dependency installation encountered issues"
    echo "💡 Try running manually: uv pip install -e '.[dev]'"
fi
cd ..

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "🚀 To start development:"
echo ""
echo "Backend (Terminal 1):"
echo "  cd backend"
echo "  uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Frontend (Terminal 2):"
echo "  cd frontend"
echo "  uv run streamlit run streamlit_app.py --server.port 3000"
echo ""
echo "🌐 Access your application:"
echo "  • Frontend: http://localhost:3000"
echo "  • Backend API: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo ""
echo "🤖 Key Features:"
echo "  • CrewAI Multi-Agent Collaboration"
echo "  • LangGraph Workflow Orchestration"
echo "  • Python 3.12 Performance"
echo "  • UV Ultra-Fast Package Management"
echo ""
echo "📚 Next Steps:"
echo "  1. Copy env.example to .env and add your OpenAI API key"
echo "  2. Review the README.md for detailed usage instructions"
echo "  3. Start asking questions about your data!"
echo "" 