#!/bin/bash

# Chat with Data - Development Setup Script
# Sets up Python environments with UV for CrewAI + LangGraph development

set -e

echo "🚀 Setting up Chat with Data Development Environment"
echo "📋 This script will:"
echo "   • Create Python virtual environments using UV"
echo "   • Install UV package manager (if needed)"
echo "   • Set up backend (CrewAI + LangGraph)"
echo "   • Set up frontend (Streamlit)"
echo ""

# Function to install pyenv if not available
install_pyenv() {
    if ! command -v pyenv &> /dev/null; then
        echo "📦 Installing pyenv (Python version manager)..."
        if command -v brew &> /dev/null; then
            brew install pyenv
        else
            curl https://pyenv.run | bash
        fi
        
        # Add pyenv to shell profile
        echo "🔧 Configuring pyenv in shell profile..."
        {
            echo 'export PYENV_ROOT="$HOME/.pyenv"'
            echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"'
            echo 'eval "$(pyenv init -)"'
        } >> ~/.zshrc
        
        # Source the profile for current session
        export PYENV_ROOT="$HOME/.pyenv"
        [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
        
        echo "✅ pyenv installed successfully"
    fi
}

# Function to install Python 3.12 using pyenv
install_python312() {
    echo "🐍 Installing Python 3.12.7 using pyenv..."
    pyenv install 3.12.7
    pyenv global 3.12.7
    echo "✅ Python 3.12.7 installed and set as global version"
}

# Check if Python 3.12 is available
if ! command -v python3.12 &> /dev/null; then
    echo "⚠️  Python 3.12 not found. Installing..."
    
    # Install pyenv if needed
    install_pyenv
    
    # Install Python 3.12
    install_python312
    
    # Verify installation
    if command -v python3.12 &> /dev/null; then
        echo "✅ Python 3.12 successfully installed: $(python3.12 --version)"
    else
        echo "❌ Failed to install Python 3.12. Please install manually:"
        echo "   Using pyenv: pyenv install 3.12.7 && pyenv global 3.12.7"
        echo "   Or download from: https://www.python.org/downloads/"
        exit 1
    fi
else
    echo "✅ Python 3.12 found: $(python3.12 --version)"
fi

PYTHON_CMD="python3.12"

# Check if UV is installed globally
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV package manager globally..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ UV installed globally"
    echo "🔄 Please restart your terminal or run: source ~/.bashrc"
    echo "   Then run this script again."
    exit 0
fi

# Function to setup environment using UV
setup_environment() {
    local env_name=$1
    local project_dir=$2
    local description=$3
    
    echo ""
    echo "🐍 Setting up $description..."
    cd "$project_dir"
    
    # Remove existing environment if it exists
    if [ -d ".venv" ]; then
        echo "⚠️  Removing existing .venv environment..."
        rm -rf .venv
    fi
    
    # Create UV virtual environment with detected Python version
    echo "📦 Creating virtual environment with $PYTHON_CMD..."
    uv venv --python "$PYTHON_CMD"
    
    # Install dependencies using UV
    echo "� Installing dependencies..."
    if uv pip install -e ".[dev]"; then
        echo "✅ $description dependencies installed successfully"
    else
        echo "⚠️  $description dependency installation encountered issues"
        echo "💡 Try running manually: cd $project_dir && uv pip install -e '.[dev]'"
        return 1
    fi
    
    cd ..
}

# Setup backend environment
setup_environment "backend" "backend" "Backend (CrewAI + LangGraph)"

# Setup frontend environment  
setup_environment "frontend" "frontend" "Frontend (Streamlit)"

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