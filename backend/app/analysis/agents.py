import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from app.llm.ollama_provider import generate_chat
from app.analysis.schemas import AnalystOutput

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../llm/prompts")
REPORTS_DIR = "reports"

def load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPT_DIR, filename), "r") as f:
        return f.read()

def run_sub_analyst(role_file: str, ticker: str, evidence_pack_str: str, model: str = "qwen2.5:7b-instruct") -> AnalystOutput:
    prompt_template = load_prompt(role_file)
    prompt = prompt_template.replace("{ticker}", ticker).replace("{evidence_pack}", evidence_pack_str)
    
    # Extract the system prompt part and the user prompt part.
    # For simplicity, we can pass the whole template as the user prompt and a basic system prompt.
    system_prompt = f"You are a sub-analyst for {ticker}. Follow the instructions carefully."
    
    try:
        response = generate_chat(
            prompt=prompt,
            system=system_prompt,
            model=model,
            response_model=AnalystOutput
        )
        return response # type: ignore
    except Exception as e:
        return AnalystOutput(
            ticker=ticker,
            agent_name=role_file.replace(".md", ""),
            summary=f"Failed to generate output: {str(e)}",
            key_points=[],
            evidence=[],
            citations=[],
            confidence=0.0,
            uncertainties=["Error running LLM or parsing response"],
            red_flags=[],
            what_would_change_my_mind=""
        )

async def run_analysis(ticker: str, evidence_pack: Dict[str, Any], model: str = "qwen2.5:7b-instruct") -> str:
    """
    Run the multi-agent workflow concurrently and produce a final memo.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    evidence_pack_str = json.dumps(evidence_pack, indent=2)
    
    roles = [
        "financial_ratio_explainer.md",
        "risk_factor_analyst.md",
        "bull_analyst.md",
        "bear_analyst.md",
        "forensic_accountant.md"
    ]
    
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        tasks = [
            loop.run_in_executor(pool, run_sub_analyst, role, ticker, evidence_pack_str, model)
            for role in roles
        ]
        results = await asyncio.gather(*tasks)
    
    analysts_combined = json.dumps([r.model_dump() for r in results], indent=2)
    
    final_prompt_template = load_prompt("final_company_memo.md")
    final_prompt = final_prompt_template.replace("{ticker}", ticker).replace("{analyst_outputs}", analysts_combined)
    
    # Final memo does not output JSON
    final_system = "You are the Lead Analyst. Produce a cohesive markdown memo."
    final_response = generate_chat(
        prompt=final_prompt,
        system=final_system,
        model=model
    )
    
    # final_response will be a Dict containing the raw response
    if isinstance(final_response, dict):
        final_memo_md = final_response.get("message", {}).get("content", "")
    else:
        final_memo_md = str(final_response)
    
    memo_path = os.path.join(REPORTS_DIR, f"{ticker}_memo.md")
    with open(memo_path, "w") as f:
        f.write(final_memo_md)
        
    return memo_path
