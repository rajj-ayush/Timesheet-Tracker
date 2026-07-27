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

    # 2. Upgraded Master Prompt (No Fluff)
    prompt = f"""
    You are an expert executive assistant and timesheet generator for a professional at Hoonartek. 
    Your task is to analyze raw desktop application activity logs and generate an ultra-short, plain-text daily timesheet comment for the Keka HR portal.

    ### RAW LOGS & MANUAL CONTEXT:
    The raw logs are provided in 30-minute summary buckets.
    
    Logs:
    {json.dumps(logs, indent=2)}
    {context_block}

    ### CRITICAL INSTRUCTIONS FOR OUTPUT FORMAT: 
    1. ONLY output plain text. Absolutely NO Markdown, NO bold text (**), NO headers (###), NO bullet points, and NO tables.
    2. Keep it ULTRA-CONCISE (Maximum 1 to 2 short sentences, strictly under 25 words). 
    3. Write a single, fast-paced professional summary focusing ONLY on the highest-value tasks.
    4. Start with a strong action verb (e.g., "Developed...", "Analyzed...", "Studied...").
    5. Write directly as the employee. Do not include introductory text like "Here is the summary".
    6. STRICT ANTI-HALLUCINATION: Do NOT invent project names, pod names, or specific technologies. ONLY use specific project names if they appear directly in the raw window titles, logs, or the User's Manual Context. If no specific project is found, use generic professional terms.
    7. NO FLUFF: Completely ignore routine communications (like Microsoft Teams, Slack, Outlook, or generic chats) and administrative portals (like Keka). Focus entirely on development, engineering, or core learning tasks.
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