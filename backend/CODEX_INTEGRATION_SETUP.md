# 🔗 Codex Integration Setup Guide

## 📋 **Overview**

This guide shows you exactly how to integrate our CodeZX agent system with your Codex setup. After following these steps, Codex will automatically switch between different agent modes based on your requests.

## 🛠️ **Step 1: Configuration Files Created**

✅ Configuration files have been created in `codex_config/`:
- `architect_config.json` - Architecture and design mode
- `developer_config.json` - Development and coding mode
- `qa_config.json` - Testing and quality assurance mode
- `devops_config.json` - Deployment and infrastructure mode

## 🔧 **Step 2: Codex Integration Methods**

### **Method A: Direct API Integration (Recommended)**

Create a Codex plugin/extension that calls our agent system:

```javascript
// codex-agent-plugin.js
class CodeXAgentPlugin {
    constructor() {
        this.apiUrl = 'http://localhost:8000/codezx';
    }
    
    async processRequest(userInput) {
        try {
            // Get mode detection from our system
            const response = await fetch(`${this.apiUrl}/agents/flexible-assignment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_description: userInput })
            });
            
            const result = await response.json();
            const detectedMode = result.data.recommended_agent;
            
            // Load mode configuration
            const config = await this.loadModeConfig(detectedMode);
            
            // Return enhanced prompt for Codex
            return {
                mode: detectedMode,
                systemPrompt: config.system_prompt,
                enhancedPrompt: this.createEnhancedPrompt(userInput, config),
                knowledgeFiles: config.knowledge_base
            };
        } catch (error) {
            console.error('Agent detection failed:', error);
            return this.getDefaultConfig();
        }
    }
    
    async loadModeConfig(mode) {
        const configPath = `./codex_config/${mode}_config.json`;
        const config = await fetch(configPath);
        return await config.json();
    }
    
    createEnhancedPrompt(userInput, config) {
        return `${config.system_prompt}

User Request: ${userInput}

Please respond as a ${config.mode} with expertise in the relevant knowledge areas.
Reference the following knowledge base files if relevant:
${config.knowledge_base.map(file => `- ${file}`).join('\n')}

${config.response_templates.introduction}`;
    }
    
    getDefaultConfig() {
        return {
            mode: 'developer',
            systemPrompt: 'You are a coding assistant.',
            enhancedPrompt: 'Please help with this coding request.',
            knowledgeFiles: []
        };
    }
}

// Usage in Codex
const agentPlugin = new CodeXAgentPlugin();

async function enhanceCodexRequest(userInput) {
    const agentConfig = await agentPlugin.processRequest(userInput);
    
    // Use agentConfig to enhance Codex's system prompt
    return {
        systemPrompt: agentConfig.systemPrompt,
        userPrompt: agentConfig.enhancedPrompt,
        mode: agentConfig.mode
    };
}
```

### **Method B: Configuration-Based Integration**

If Codex supports configuration-based mode switching, create a `codex-agents.config.json`:

```json
{
  "agents": {
    "architect": {
      "trigger_patterns": [
        "design.*database.*schema",
        "architecture.*system",
        "scalability.*requirements",
        "design.*pattern"
      ],
      "system_prompt": "You are CodeZX-Architect, a senior system architect. Focus on: system design, scalability, architectural patterns, and long-term planning.",
      "knowledge_base": [
        "knowledge_base/architecture_guidelines.md",
        "knowledge_base/system_patterns.md"
      ],
      "response_style": "Provide high-level architectural guidance with clear reasoning and multiple options when appropriate."
    },
    "developer": {
      "trigger_patterns": [
        "implement.*function",
        "fix.*bug",
        "write.*code",
        "create.*class"
      ],
      "system_prompt": "You are CodeZX-Developer, a senior software developer. Focus on: clean code, best practices, implementation details, and practical solutions.",
      "knowledge_base": [
        "knowledge_base/coding_standards.md",
        "knowledge_base/best_practices.md"
      ],
      "response_style": "Provide practical, implementable code solutions with explanations and best practices."
    },
    "qa": {
      "trigger_patterns": [
        "test.*performance",
        "security.*vulnerabilities",
        "quality.*assurance",
        "test.*api"
      ],
      "system_prompt": "You are CodeZX-QA, a senior quality assurance engineer. Focus on: testing strategies, quality metrics, edge cases, and validation approaches.",
      "knowledge_base": [
        "knowledge_base/testing_protocols.md",
        "knowledge_base/quality_metrics.md"
      ],
      "response_style": "Provide comprehensive testing approaches with specific test cases and quality considerations."
    },
    "devops": {
      "trigger_patterns": [
        "deploy.*production",
        "infrastructure.*setup",
        "monitoring.*system",
        "ci.*cd.*pipeline"
      ],
      "system_prompt": "You are CodeZX-DevOps, a senior DevOps engineer. Focus on: infrastructure, deployment, monitoring, and operational excellence.",
      "knowledge_base": [
        "knowledge_base/deployment_guides.md",
        "knowledge_base/infrastructure_patterns.md"
      ],
      "response_style": "Provide infrastructure and deployment solutions with operational considerations and best practices."
    }
  },
  "default_agent": "developer",
  "confidence_threshold": 0.3
}
```

## 🚀 **Step 3: Start the Backend API**

Make sure our CodeZX agent API is running:

```bash
# In the backend directory
cd /opt/spx-atr/Whispr/backend

# Start the FastAPI server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000` with these endpoints:
- `GET /codezx/agents/status` - Get agent status
- `POST /codezx/agents/flexible-assignment` - Get mode recommendations
- `POST /codezx/agents/{type}/tasks` - Assign tasks directly
- `GET /codezx/health` - Health check

## 🧪 **Step 4: Test the Integration**

### **Test Mode Detection:**

```bash
# Test architecture request
curl -X POST "http://localhost:8000/codezx/agents/flexible-assignment" \
  -H "Content-Type: application/json" \
  -d '{"task_description": "Design a new database schema for user management"}'

# Expected response:
{
  "status": "success",
  "data": {
    "recommended_agent": "architect",
    "reasoning": "High confidence (12.7%) - matched keywords: design, schema",
    "flexibility_note": "Any agent can work on any task..."
  }
}
```

### **Test Different Modes:**

```bash
# Developer mode
curl -X POST "http://localhost:8000/codezx/agents/flexible-assignment" \
  -H "Content-Type: application/json" \
  -d '{"task_description": "Fix the login bug in the authentication system"}'

# QA mode  
curl -X POST "http://localhost:8000/codezx/agents/flexible-assignment" \
  -H "Content-Type: application/json" \
  -d '{"task_description": "Test the API endpoints for security vulnerabilities"}'

# DevOps mode
curl -X POST "http://localhost:8000/codezx/agents/flexible-assignment" \
  -H "Content-Type: application/json" \
  -d '{"task_description": "Deploy the application to production with monitoring"}'
```

## 🎯 **Step 5: Codex Configuration**

### **Option 1: If Codex Supports Custom Configurations**

1. Copy the configuration files to your Codex config directory:
```bash
cp -r codex_config/ ~/.codex/agents/
cp -r knowledge_base/ ~/.codex/knowledge/
```

2. Update your Codex settings to enable agent mode detection:
```json
{
  "agents": {
    "enabled": true,
    "config_path": "~/.codex/agents/",
    "knowledge_path": "~/.codex/knowledge/",
    "api_endpoint": "http://localhost:8000/codezx"
  }
}
```

### **Option 2: If Codex Supports Plugins**

1. Install the CodeZX plugin:
```bash
codex plugin install codex-agent-plugin
```

2. Configure the plugin:
```bash
codex config set agent.api_url "http://localhost:8000/codezx"
codex config set agent.enabled true
```

### **Option 3: Manual Integration**

If Codex doesn't support automatic integration, you can manually trigger modes:

```
# In Codex, prefix your requests:
@architect Design a new database schema for user management
@developer Fix the login bug in the authentication system  
@qa Test the API endpoints for security vulnerabilities
@devops Deploy the application to production
```

## 🔄 **Step 6: Workflow Examples**

### **Automatic Mode Detection (Ideal):**
```
You type: "Design a scalable database for user management"
↓
Codex detects: Architecture keywords
↓
Codex switches to: Architect mode
↓
Response: High-level architectural guidance with design patterns
```

### **Manual Mode Override:**
```
You type: "@qa Design a database schema"
↓
Codex uses: QA mode (even though it's an architecture task)
↓
Response: Database design from a testing/quality perspective
```

### **Fallback Mode:**
```
You type: "Hello, how are you?"
↓
Codex detects: No specific keywords
↓
Codex uses: Developer mode (default)
↓
Response: General coding assistance response
```

## 📊 **Step 7: Monitor and Optimize**

### **Check Agent Performance:**
```bash
curl "http://localhost:8000/codezx/agents/status"
```

### **View Interaction History:**
```bash
curl "http://localhost:8000/codezx/agents/statistics"
```

### **Adjust Mode Detection:**
Edit `codex_integration.py` to improve keyword matching based on your usage patterns.

## 🛡️ **Troubleshooting**

### **Agent API Not Responding:**
```bash
# Check if the service is running
curl "http://localhost:8000/codezx/health"

# Restart the service
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### **Wrong Mode Detection:**
1. Check the keywords in your request
2. Review `codex_integration.py` keyword lists
3. Add more specific keywords for your use case
4. Use manual mode override if needed

### **Configuration Issues:**
1. Verify configuration files exist in `codex_config/`
2. Check JSON syntax is valid
3. Ensure file permissions are correct
4. Test API endpoints manually

## 🎉 **Success Indicators**

When integration is working correctly, you should see:

1. **Automatic Mode Switching**: Codex responds differently based on request type
2. **Appropriate Knowledge**: Responses reference relevant knowledge base content
3. **Consistent Style**: Responses match the expected agent personality
4. **Accurate Detection**: Mode detection matches your intent 80%+ of the time

## 🔄 **Next Steps**

1. **Customize Keywords**: Add domain-specific keywords for your trading system
2. **Create More Knowledge**: Add trading-specific knowledge base files
3. **Train the System**: Use it regularly to improve detection accuracy
4. **Add Custom Modes**: Create specialized agents for trading strategies

---

**🎯 Your Codex is now enhanced with intelligent agent switching! Each request will automatically get the expertise it needs.**
