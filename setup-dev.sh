#!/bin/bash

# Chat with Data - Development Setup Script
# Sets up Python 3.12 environments with UV for CrewAI + LangGraph development

set -e

echo "🚀 Setting up Chat with Data Development Environment"
echo "📋 This script will:"
echo "   • Create Python 3.12 conda environments"
echo "   • Install UV package manager"
echo "   • Set up backend (CrewAI + LangGraph)"
echo "   • Set up frontend (Streamlit)"
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed. Please install Miniconda or Anaconda first:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Function to create conda environment
create_env() {
    local env_name=$1
    local description=$2
    
    echo "🐍 Creating conda environment: $env_name"
    if conda info --envs | grep -q "^$env_name "; then
        echo "⚠️  Environment $env_name already exists. Removing..."
        conda env remove -n $env_name -y
    fi
    
    conda create -n $env_name python=3.12 -y
    echo "✅ Created $env_name ($description)"
}

# Create backend environment
create_env "chat-backend" "CrewAI + LangGraph Backend"

# Create frontend environment  
create_env "chat-frontend" "Streamlit Frontend"

# Install UV in backend environment
echo ""
echo "📦 Installing UV package manager in backend environment..."
conda run -n chat-backend pip install uv
echo "✅ UV installed in chat-backend"

# Install UV in frontend environment
echo ""
echo "📦 Installing UV package manager in frontend environment..."
conda run -n chat-frontend pip install uv
echo "✅ UV installed in chat-frontend"

# Install backend dependencies
echo ""
echo "🔧 Installing backend dependencies (CrewAI + LangGraph)..."
cd backend
if conda run -n chat-backend uv pip install -e ".[dev]"; then
    echo "✅ Backend dependencies installed successfully"
else
    echo "⚠️  Backend dependency installation encountered issues"
    echo "💡 Try running manually: conda activate chat-backend && uv pip install -e '.[dev]'"
fi
cd ..

# Install frontend dependencies
echo ""
echo "🔧 Installing frontend dependencies..."
cd frontend
if conda run -n chat-frontend uv pip install -e ".[dev]"; then
    echo "✅ Frontend dependencies installed successfully"
else
    echo "⚠️  Frontend dependency installation encountered issues"
    echo "💡 Try running manually: conda activate chat-frontend && uv pip install -e '.[dev]'"
fi
cd ..

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "🚀 To start development:"
echo ""
echo "Backend (Terminal 1):"
echo "  conda activate chat-backend"
echo "  cd backend"
echo "  uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Frontend (Terminal 2):"
echo "  conda activate chat-frontend"
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