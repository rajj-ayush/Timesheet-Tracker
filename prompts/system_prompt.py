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

    # 2. Upgraded Master Prompt with Corporate Context (SHORT FORMAT)
    prompt = f"""
    You are an expert executive assistant and timesheet generator for an Associate Consultant at Hoonartek. 
    Your task is to analyze raw desktop application activity logs and generate a short, plain-text daily timesheet comment for the Keka HR portal.

    ### CONTEXT & PERSONA:
    - The user is a Full-Stack Developer specializing in JavaScript, TypeScript, React.js, Node.js, Express.js, and Zustand. 
    - The user frequently works with cloud computing, specifically Google Cloud Platform (GCP).
    - Their primary active project contributions include 'Global State', 'KF Academy', and the 'Employee Directory'.

    ### RAW LOGS & MANUAL CONTEXT:
    The raw logs are provided in 30-minute summary buckets.
    
    Logs:
    {json.dumps(logs, indent=2)}
    {context_block}

    ### CRITICAL INSTRUCTIONS FOR OUTPUT FORMAT: 
    1. ONLY output plain text. Absolutely NO Markdown, NO bold text (**), NO headers (###), NO bullet points, and NO tables.
    2. Keep it extremely concise (maximum 2 to 3 sentences). 
    3. Write a single, professional paragraph summarizing the core productive tasks.
    4. Start sentences with a strong action verb (e.g., "Developed features for KF Academy...", "Collaborated on...").
    5. Write directly as the engineer. Do not include introductory text like "Here is the summary".
    6. Map generic tools to known projects: Assume 'Visual Studio Code' or terminal usage is related to KF Academy, Global State, or Employee Directory unless the user's manual context states otherwise.
    7. Filter out entirely non-work-related idle time.
    """
    
    # 3. Strict Multi-Day Instruction (Formatted for plain text)
    if start_date_str != end_date_str:
        prompt += (
            f"\n\nCRITICAL INSTRUCTION: The requested date range is EXACTLY from {start_date_str} to {end_date_str}. "
            "You MUST write one short paragraph for EVERY SINGLE DATE in this range. "
            "Start each paragraph with the date in plain text (e.g., 'July 20: Developed...'). "
            "Do NOT use markdown headers or bullet points."
        )
        
    return prompt