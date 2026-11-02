# Command to create this project
```
# 1. Create main workspace root
New-Item -ItemType Directory -Path "NexusFlow"
Set-Location -Path "NexusFlow"

# 2. Build out Backend (FastAPI + LangGraph) structure
New-Item -ItemType Directory -Path "backend/app/agents"
New-Item -ItemType Directory -Path "backend/app/tools"
New-Item -ItemType Directory -Path "backend/app/schemas"
New-Item -ItemType Directory -Path "backend/app/routers"

# Create backend files
New-Item -ItemType File -Path "backend/requirements.txt"
New-Item -ItemType File -Path "backend/.env"
New-Item -ItemType File -Path "backend/Dockerfile"
New-Item -ItemType File -Path "backend/app/__init__.py"
New-Item -ItemType File -Path "backend/app/main.py"
New-Item -ItemType File -Path "backend/app/config.py"
New-Item -ItemType File -Path "backend/app/agents/__init__.py"
New-Item -ItemType File -Path "backend/app/agents/state.py"
New-Item -ItemType File -Path "backend/app/agents/graph.py"
New-Item -ItemType File -Path "backend/app/agents/coder_agent.py"
New-Item -ItemType File -Path "backend/app/agents/reviewer_agent.py"
New-Item -ItemType File -Path "backend/app/tools/__init__.py"
New-Item -ItemType File -Path "backend/app/tools/code_executor.py"
New-Item -ItemType File -Path "backend/app/schemas/__init__.py"
New-Item -ItemType File -Path "backend/app/schemas/chat.py"
New-Item -ItemType File -Path "backend/app/routers/__init__.py"
New-Item -ItemType File -Path "backend/app/routers/workflow.py"

# 3. Build out Frontend (Angular Architecture) structure
New-Item -ItemType Directory -Path "frontend/src/app/core/services"
New-Item -ItemType Directory -Path "frontend/src/app/features/dashboard"
New-Item -ItemType Directory -Path "frontend/src/app/features/chat-panel"
New-Item -ItemType Directory -Path "frontend/src/app/features/code-viewer"
New-Item -ItemType Directory -Path "frontend/src/assets"

# Create base Angular configuration and shell files
New-Item -ItemType File -Path "frontend/package.json"
New-Item -ItemType File -Path "frontend/angular.json"
New-Item -ItemType File -Path "frontend/tsconfig.json"
New-Item -ItemType File -Path "frontend/src/index.html"
New-Item -ItemType File -Path "frontend/src/main.ts"
New-Item -ItemType File -Path "frontend/src/app/app.config.ts"
New-Item -ItemType File -Path "frontend/src/app/app.routes.ts"
New-Item -ItemType File -Path "frontend/src/app/app.component.ts"

# Create core services and feature views files
New-Item -ItemType File -Path "frontend/src/app/core/services/workflow.service.ts"
New-Item -ItemType File -Path "frontend/src/app/features/dashboard/dashboard.component.ts"
New-Item -ItemType File -Path "frontend/src/app/features/dashboard/dashboard.component.html"
New-Item -ItemType File -Path "frontend/src/app/features/dashboard/dashboard.component.scss"
New-Item -ItemType File -Path "frontend/src/app/features/chat-panel/chat-panel.component.ts"
New-Item -ItemType File -Path "frontend/src/app/features/chat-panel/chat-panel.component.html"
New-Item -ItemType File -Path "frontend/src/app/features/code-viewer/code-viewer.component.ts"
New-Item -ItemType File -Path "frontend/src/app/features/code-viewer/code-viewer.component.html"

Write-Host "Success! 'NexusFlow' directory architecture successfully provisioned." -ForegroundColor Green
```

## command to run this project
# Navigate into the backend directory
cd backend

# (Optional) Create a Python Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install required Python packages
pip install -r requirements.txt

# Launch the FastAPI application server with live reload enabled
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# Navigate into the frontend directory
cd frontend

# Install Node modules/dependencies specified in package.json
npm install

# Start the Angular development workspace server
npm start


