"""Helper to load agent.md files."""

import os

def load_agent_prompt(agent_name: str) -> str:
    """
    Reads the 'agent.md' file for a specific agent.
    
    Args:
        agent_name (str): The name of the folder inside 'agents/' (e.g., 'gastronomist', 'lumiere')
        
    Returns:
        str: The full text content of the markdown file.
        
    Raises:
        FileNotFoundError: If the file does not exist.
    """
    # Get the directory where this script (utils.py) is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path: .../amsterdam_concierge/agents/{agent_name}/agent.md
    file_path = os.path.join(base_dir, "agents", agent_name, "agent.md")
    
    # Check if exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find agent prompt. Checked path: {file_path}\n"
            f"Make sure the folder '{agent_name}' exists inside 'agents/' and contains 'agent.md'."
        )
    
    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return content