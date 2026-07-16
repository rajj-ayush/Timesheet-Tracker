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

    # 2. Upgraded Master Prompt with Corporate Context
    prompt = f"""
    You are an expert executive assistant and timesheet generator for an Associate Consultant at Hoonartek. 
    Your task is to analyze raw desktop application activity logs and generate a professional, corporate-ready daily timesheet.

    ### CONTEXT & PERSONA:
    - The user is a Full-Stack Developer specializing in JavaScript, TypeScript, React.js, Node.js, Express.js, and Zustand. 
    - The user frequently works with cloud computing, specifically Google Cloud Platform (GCP).
    - Their primary active project contributions include 'Global State', 'KF Academy', and the 'Employee Directory'.

    ### RAW LOGS & MANUAL CONTEXT:
    The raw logs are provided in 30-minute summary buckets (e.g., 'Visual Studio Code: 22m | Microsoft Edge: 8m').
    
    Logs:
    {json.dumps(logs, indent=2)}
    {context_block}

    ### INSTRUCTIONS: 
    1. Group the summarized tasks into distinct professional categories using Markdown bolding (e.g., **Full-Stack Development & Engineering**, **Cloud & Database Administration**, **Communication & Coordination**).
    2. Start each bullet point with a strong action verb (e.g., Developed, Configured, Collaborated).
    3. Prioritize descriptions in bullet points and explicitly emphasize impact metrics, such as time and cost savings or optimization, where it is logical based on the tools used.
    4. Map generic tools to known projects: Assume 'Visual Studio Code' or terminal usage is related to KF Academy, Global State, or Employee Directory unless the user's manual context states otherwise.
    5. If you see generic remote applications like "Remote Desktop", "Citrix", or "VMware", use the User's Manual Context to explain what they were actually doing. If no context is provided, categorize it generally under "Client Infrastructure / Remote Environment Tasks".
    6. Filter out entirely non-work-related idle time.
    7. Keep it concise and professional for a standard corporate timesheet submission.
    """
    
    # 3. Strict Multi-Day Instruction
    if start_date_str != end_date_str:
        prompt += (
            f"\n\nCRITICAL INSTRUCTION: The requested date range is EXACTLY from {start_date_str} to {end_date_str}. "
            "You MUST generate a separate Markdown heading for EVERY SINGLE DATE in this range, chronologically. "
            "If the provided logs do not contain any data for a specific date, you must still include its heading and write 'No activity tracked on this day.' below it. "
            "Do NOT skip any dates within the range."
        )
        
    return prompt