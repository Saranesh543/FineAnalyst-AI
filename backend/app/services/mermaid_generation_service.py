"""
Mermaid Generation Service

Uses the AI Agent to generate Mermaid.js diagram syntax from SQL execution results.
"""

from __future__ import annotations

import logging
from pydantic_ai import Agent
from pydantic import BaseModel, Field

from app.services.llm_provider import get_llm_model
from app.schemas.execution import SQLExecutionResponse

logger = logging.getLogger(__name__)

class MermaidGenerationError(Exception):
    """Raised when Mermaid generation fails."""

class MermaidGenerationResponse(BaseModel):
    mermaid_code: str = Field(description="The generated Mermaid syntax.")

_SYSTEM_PROMPT = """
You are a Mermaid.js generation expert for a Business Intelligence platform.
Your task is to take a user's analytical question and the raw database results, and output valid Mermaid.js graph syntax.

CRITICAL RULES:
1. ONLY generate valid Mermaid code (e.g. `graph TD`, `pie`, `sequenceDiagram`, `gantt`). 
2. NEVER invent nodes, edges, or entities that are not present in the data rows.
3. If the data is empty, return a simple graph indicating no data.
4. Do NOT wrap the output in markdown code blocks inside the JSON response. The `mermaid_code` field must be raw Mermaid string.
5. Format the Mermaid diagram cleanly with proper indentation.

Data mapping guidelines:
- If the intent implies a process, hierarchy, or relationship, use `graph TD` or `graph LR`.
- Ensure node IDs do not contain special characters (wrap text in quotes, e.g., `A["Node Label"]`).

You MUST output ONLY valid JSON matching the schema.
"""

def _get_mermaid_agent() -> Agent:
    return Agent(
        model=get_llm_model(),
        system_prompt=_SYSTEM_PROMPT,
        result_type=MermaidGenerationResponse,
    )

class MermaidGenerationService:
    def __init__(self) -> None:
        pass

    async def generate_mermaid(
        self, question: str, execution_result: SQLExecutionResponse
    ) -> str:
        """
        Generates Mermaid syntax from the given question and dataset.
        """
        # Truncate rows if too large to prevent token limits.
        max_rows = 50
        rows_to_show = execution_result.rows[:max_rows]
        truncated_msg = ""
        if execution_result.row_count > max_rows:
            truncated_msg = f" (Showing first {max_rows} of {execution_result.row_count} rows)"

        prompt = f"""
--- USER QUESTION ---
{question}

--- EXECUTED DATA{truncated_msg} ---
Columns: {", ".join(execution_result.columns) if execution_result.columns else "None"}
Rows:
{rows_to_show}

Generate the Mermaid syntax representing this data.
"""
        try:
            agent = _get_mermaid_agent()
            result = await agent.run(prompt)
            
            # PydanticAI automatically validates against MermaidGenerationResponse
            response_data: MermaidGenerationResponse = result.data
            code = response_data.mermaid_code.strip()
            
            # Simple sanitization
            if code.startswith("```mermaid"):
                code = code[10:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
                
            return code.strip()

        except Exception as e:
            logger.exception("Failed to generate Mermaid syntax: %s", e)
            raise MermaidGenerationError(f"Mermaid generation failed: {e}") from e

mermaid_generation_service = MermaidGenerationService()
