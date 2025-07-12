# Prompt Management System

This directory contains the YAML prompt files and documentation for the Chat with Data prompt management system.

## Overview

The prompt management system allows you to:
- Store system prompts in YAML files for easy editing
- Load prompts from Langfuse for dynamic updates
- Cache prompts for performance
- Fallback to local YAML files when Langfuse is unavailable

## File Structure

```
prompts/
├── README.md                    # This file
├── crew_agent_prompts.yaml      # CrewAI agent system prompts
├── sql_agent_prompts.yaml       # SQL agent system prompts
└── langgraph_prompts.yaml       # LangGraph orchestrator prompts
```

## Prompt Files

### crew_agent_prompts.yaml
Contains prompts for CrewAI agents:
- **agents**: Agent definitions (role, goal, backstory)
- **tasks**: Task definitions for different analysis types
- **data_summary_template**: Template for data summaries
- **result_formatting**: Output formatting guidelines

### sql_agent_prompts.yaml
Contains prompts for SQL generation:
- **sql_generation**: SQL query generation prompts
- **pandas_operations**: Pandas code generation prompts
- **query_validation**: Validation rules
- **error_handling**: Error handling guidelines
- **output_formatting**: Result formatting specifications

### langgraph_prompts.yaml
Contains prompts for LangGraph orchestration:
- **intent_analysis**: Query intent analysis prompts
- **routing_logic**: Analysis routing rules
- **synthesis**: Result synthesis prompts
- **response_formatting**: Final response formatting
- **workflow_states**: State management
- **error_handling**: Error handling strategies

## Usage

### Loading Prompts in Code

```python
from services.prompt_service import get_prompt_service

# Get the prompt service
prompt_service = get_prompt_service()

# Load a specific prompt
system_prompt = prompt_service.get_prompt("crew_agent", "agents", "data_analyst.backstory")

# Load a complete prompt dictionary
agents_config = prompt_service.get_prompt_dict("crew_agent", "agents")
```

### Updating Prompts

#### Local Development
1. Edit the YAML files in this directory
2. Restart the application to load changes
3. The prompt service will automatically reload from YAML

#### Production with Langfuse
1. Update prompts in Langfuse
2. The prompt service will automatically load from Langfuse
3. If Langfuse is unavailable, it falls back to local YAML

### Syncing to Langfuse

```python
# Sync all local prompts to Langfuse
results = prompt_service.sync_prompts_to_langfuse()
print(f"Synced {len(results)} prompts")
```

## Prompt Service Features

### Caching
- Prompts are cached for 1 hour by default
- Cache can be cleared manually: `prompt_service.clear_cache()`
- Cache is automatically invalidated when prompts are updated

### Fallback Strategy
1. Try to load from Langfuse first
2. If Langfuse is unavailable, load from local YAML
3. If YAML is not found, use hardcoded defaults
4. Log warnings for missing prompts

### Error Handling
- Graceful fallback to defaults if prompts are missing
- Detailed logging for debugging
- Cache invalidation on errors

## Best Practices

### Writing Prompts
1. **Be specific**: Include clear instructions and examples
2. **Use placeholders**: Use `{variable}` syntax for dynamic content
3. **Structure consistently**: Follow the established YAML structure
4. **Version control**: Keep prompts in version control for tracking changes

### Managing Prompts
1. **Test locally**: Always test prompt changes locally first
2. **Backup defaults**: Keep hardcoded defaults as fallbacks
3. **Monitor performance**: Watch for prompt loading performance
4. **Document changes**: Document significant prompt changes

### Langfuse Integration
1. **Initialize collections**: Ensure Langfuse collections exist
2. **Sync regularly**: Sync local changes to Langfuse
3. **Monitor sync status**: Check sync results for errors
4. **Backup strategy**: Keep local YAML as backup

## Testing

Run the test script to verify the prompt management system:

```bash
cd backend
python test_prompts.py
```

This will test:
- YAML file loading
- Agent initialization with prompts
- Prompt caching
- Cache clearing

## Troubleshooting

### Common Issues

1. **Prompts not loading**
   - Check YAML file syntax
   - Verify file paths
   - Check log messages for errors

2. **Langfuse not working**
   - Verify Langfuse configuration
   - Check network connectivity
   - Ensure API keys are valid

3. **Cache issues**
   - Clear cache manually: `prompt_service.clear_cache()`
   - Check cache TTL settings
   - Restart the application

### Debug Mode

Enable debug logging to see detailed prompt loading information:

```python
import logging
logging.getLogger('services.prompt_service').setLevel(logging.DEBUG)
```

## Future Enhancements

- **Prompt versioning**: Track prompt versions and changes
- **A/B testing**: Support for prompt A/B testing
- **Performance metrics**: Track prompt loading and usage metrics
- **Prompt validation**: Validate prompt syntax and structure
- **Multi-language support**: Support for multiple languages
- **Prompt templates**: Reusable prompt templates 