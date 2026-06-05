#!/usr/bin/env python3
import argparse
import sys
import os
import json
import asyncio
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.db.session import get_connection
from app.analysis.company_context import build_evidence_pack
from app.analysis.agents import run_analysis
from app.llm.hallucination_audit import audit_hallucinations

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive company memo via local LLM synthesis.")
    parser.add_argument("ticker", type=str, help="Ticker symbol (e.g., PLTR)")
    parser.add_argument("--dry-run", action="store_true", help="Build evidence pack but do not run LLMs")
    parser.add_argument("--model", type=str, default="qwen2.5:7b-instruct", help="Local Ollama model to use")
    
    args = parser.parse_args()
    ticker = args.ticker.upper()
    
    logging.info(f"Starting memo generation for {ticker}")
    logging.info(f"Using model: {args.model}")
    
    try:
        with get_connection() as conn:
            logging.info("Building evidence pack from deterministic ratios and RAG...")
            evidence_pack = build_evidence_pack(conn, ticker)
            
            if args.dry_run:
                logging.info("DRY RUN: Evidence pack built. Skipping LLM synthesis.")
                print(json.dumps(evidence_pack, indent=2))
                return
                
            logging.info("Running sub-analysts concurrently...")
            memo_path = asyncio.run(run_analysis(ticker, evidence_pack, model=args.model))
            
            logging.info(f"Memo generated successfully: {memo_path}")
            
            logging.info("Running hallucination audit...")
            with open(memo_path, "r") as f:
                final_memo_text = f.read()
                
            audit_result = audit_hallucinations(final_memo_text, evidence_pack)
            
            if audit_result["pass"]:
                logging.info("Hallucination audit PASSED. No unsupported numbers found.")
            else:
                logging.warning(f"Hallucination audit FAILED. Suspicious numbers found: {audit_result['suspicious_numbers']}")
                
                # Append audit result to the memo
                with open(memo_path, "a") as f:
                    f.write("\n\n---\n")
                    f.write("## ⚠️ AI Hallucination Audit Report\n")
                    f.write("The following numbers were detected in this memo but could not be traced back to the underlying financial ratios or SEC source chunks. Treat them with caution:\n")
                    for num in audit_result['suspicious_numbers']:
                        f.write(f"- `{num}`\n")
            
            print(f"\nFinal memo available at: {memo_path}")
            
    except Exception as e:
        logging.error(f"Generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
