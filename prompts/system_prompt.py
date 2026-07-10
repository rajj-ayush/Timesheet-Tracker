import json

def get_timesheet_prompt(logs, start_date_str, end_date_str, additional_context=""):
    """Generates the prompt for the Gemini AI to draft the timesheet."""
    
    # 1. Handle the Virtual Machine / Manual Override Context
    context_block = ""
    if additional_context and additional_context.strip():
        context_block = f"""
    User's Manual Context / Notes:
    "{additional_context}"
    (CRITICAL: Seamlessly weave these manual notes into the final timesheet. These notes explain the actual work done inside black-box environments like Virtual Machines or off-screen tasks.)
    """

    # 2. Upgraded Categorization Instructions
    prompt = f"""
    You are an HR Assistant. Summarize the following desktop and browser activity 
    into a highly professional daily timesheet.

    Raw Logs:
    {json.dumps(logs, indent=2)}
    {context_block}

    Instructions: 
    - Group the summarized tasks into distinct professional categories using Markdown bolding (e.g., **Development & Engineering**, **Communication & Coordination**, **Administration & Documentation**).
    - Start each bullet point with a strong action verb (e.g., Developed, Configured, Collaborated).
    - If you see generic remote applications like "Remote Desktop", "Citrix", or "VMware", use the User's Manual Context to explain what they were actually doing. If no context is provided, categorize it generally under "Client Infrastructure / Remote Environment Tasks".
    - Filter out entirely non-work-related idle time.
    - Keep it concise and professional for a standard corporate timesheet submission.
    """
    
    # If the user selected a range, attach the strict multi-day instruction
    if start_date_str != end_date_str:
        prompt += (
            f"\n\nCRITICAL INSTRUCTION: The requested date range is EXACTLY from {start_date_str} to {end_date_str}. "
            "You MUST generate a separate Markdown heading for EVERY SINGLE DATE in this range, chronologically. "
            "If the provided logs do not contain any data for a specific date, you must still include its heading and write 'No activity tracked on this day.' below it. "
            "Do NOT skip any dates within the range."
        )
        
    return prompt