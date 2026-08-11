"""
Mermaid Generation Service

Generates and validates Mermaid diagram code based on user intent and data context.
Provides retries on syntax validation errors.
"""

import logging
import time
import subprocess
import os
import json
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from app.services.llm_provider import get_llm_model
from app.schemas.execution import SQLExecutionResponse

logger = logging.getLogger(__name__)


class MermaidResult(BaseModel):
    diagramType: str = Field(description="The type of diagram generated.")
    title: str = Field(description="A concise title for the diagram.")
    code: str = Field(description="The actual Mermaid syntax code (without markdown fences).")


_SYSTEM_PROMPT = """
You are FineAnalyst AI, generating Mermaid diagrams.
Your task is to generate valid Mermaid syntax for the requested diagram type.

Rules:
1. ONLY return the JSON object matching the requested schema.
2. The 'code' field MUST contain valid Mermaid syntax. Do NOT include markdown fences (like ```mermaid) inside the code string.
3. For ER diagrams and conceptual diagrams, ONLY use entities explicitly provided in the user's request or the provided context. Do NOT invent additional unsupported entities just to make the diagram more detailed.
4. Keep the diagram concise and focused on the user's request. Avoid excessive nodes or edges that clutter the visualization. Max 20 nodes.
5. If the user asks for a flowchart, use `flowchart TD` or `flowchart LR`.
6. If the user asks for a data chart (e.g. line chart, bar chart) or provides numeric/time-series data, you MUST use Mermaid's `xychart-beta` syntax. 
   - NEVER output invented syntax like "lineChart".
   - NEVER output raw JSON objects in the chart data.
   - Example xychart-beta:
     xychart-beta
       title "Monthly Revenue Trend"
       x-axis ["Jan", "Feb", "Mar"]
       y-axis "Revenue ($)" 0 --> 150000
       line [50000, 58000, 65000]
7. Ensure syntax is perfectly valid. Close all brackets and quotes. Avoid unescaped special characters in node labels.
8. You MUST return ONLY a JSON object matching this exact schema:
{
    "diagramType": "string (e.g. flowchart, sequenceDiagram, xychart-beta)",
    "title": "string (A concise title for the diagram)",
    "code": "string (The actual Mermaid syntax code without markdown fences)"
}
"""

class MermaidGenerationError(Exception):
    pass


class MermaidGenerationService:
    def __init__(self):
        self._agent = None

    @property
    def agent(self):
        if self._agent is None:
            self._agent = Agent(
                model=get_llm_model(),
                system_prompt=_SYSTEM_PROMPT,
                retries=0, # We handle retries manually to inject the parser error
            )
        return self._agent

    def _validate_mermaid_syntax(self, code: str) -> str | None:
        """
        Validates Mermaid syntax.
        Returns an error string if invalid, or None if valid.
        """
        # Basic limits validation
        if len(code) > 4000:
            return "Code exceeds maximum length of 4000 characters. Please generate a simpler diagram."
        
        lines = code.strip().split('\n')
        nodes = sum(1 for line in lines if '[' in line or '{' in line or '(' in line or '->' in line or '-->' in line)
        if nodes > 40:
            return "Diagram is too complex (exceeds node/edge limit). Please generate a simpler diagram."

        # Strict syntax validation via Node.js script in the frontend directory
        try:
            frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "frontend")
            validator_script = os.path.join(frontend_dir, "validate_mermaid.js")
            
            # Create the script if it doesn't exist
            if not os.path.exists(validator_script):
                with open(validator_script, "w") as f:
                    f.write('''
const mermaid = require('mermaid');
const fs = require('fs');

async function validate() {
  const code = fs.readFileSync(0, 'utf-8');
  try {
    mermaid.default.mermaidAPI.initialize({ startOnLoad: false });
    await mermaid.default.parse(code);
    console.log("VALID");
    process.exit(0);
  } catch (err) {
    console.error(err.message || err.toString());
    process.exit(1);
  }
}
validate();
                    ''')
            
            # Run the script, piping the code to stdin
            result = subprocess.run(
                ["node", "validate_mermaid.js"],
                cwd=frontend_dir,
                input=code.encode("utf-8"),
                capture_output=True,
                timeout=5  # Render timeout limit
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8").strip()
                # Clean up the error message slightly to avoid massive stack traces if present
                first_lines = "\\n".join(error_msg.split("\\n")[:3])
                return f"Mermaid parser error:\\n{first_lines}"
                
        except subprocess.TimeoutExpired:
            return "Mermaid syntax validation timed out. Diagram may be too complex."
        except Exception as e:
            logger.warning(f"Could not run Node validator: {e}. Falling back to basic validation.")
            # Basic fallback validation
            if not code.strip():
                return "Mermaid code is empty."
            first_word = code.strip().split()[0]
            valid_starts = ['flowchart', 'sequenceDiagram', 'erDiagram', 'mindmap', 'timeline', 'stateDiagram-v2', 'graph', 'pie', 'gantt', 'classDiagram', 'gitGraph', 'xychart-beta']
            if first_word not in valid_starts:
                return f"Invalid diagram type declaration '{first_word}'. Must start with one of: {', '.join(valid_starts)}"
                
        return None

    async def generate_mermaid(self, question: str, diagram_type: str | None, context: str | SQLExecutionResponse = "") -> MermaidResult:
        dt = diagram_type or "flowchart"
        prompt = f"User Question: {question}\nRequested Diagram Type: {dt}\n"
        
        if isinstance(context, SQLExecutionResponse):
            max_rows = 50
            rows_to_show = context.rows[:max_rows]
            truncated_msg = ""
            if context.row_count > max_rows:
                truncated_msg = f" (Showing first {max_rows} of {context.row_count} rows)"
            prompt += f"\nAvailable Context / Data{truncated_msg}:\nColumns: {context.columns}\nRows:\n{rows_to_show}\n"
        elif context:
            prompt += f"\nAvailable Context:\n{context}\n"
            
        logger.info(f"[MERMAID SPEC] Generating {dt} for question: {question}")
        
        last_error = None
        
        # We manually handle retries to incorporate external validation feedback
        for attempt in range(3):
            try:
                if last_error:
                    retry_prompt = prompt + f"\n\nSystem Error from previous attempt:\n{last_error}\n\nPlease fix the syntax errors and ensure the diagram is simpler if needed."
                    result = await self.agent.run(retry_prompt)
                else:
                    result = await self.agent.run(prompt)
                    
                raw_response = result.output
                
                # Clean markdown blocks
                cleaned = raw_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                try:
                    data = json.loads(cleaned)
                    mermaid_result = MermaidResult(**data)
                except Exception as parse_error:
                    logger.warning(f"[MERMAID PARSE ERROR] Failed to parse JSON: {parse_error}")
                    last_error = f"Failed to parse JSON. Ensure you return ONLY valid JSON matching the schema. Error: {parse_error}"
                    continue
                
                logger.info("[MERMAID SPEC] %s", json.dumps({
                    "diagramType": mermaid_result.diagramType,
                    "title": mermaid_result.title,
                    "code": mermaid_result.code
                }))
                
                validation_error = self._validate_mermaid_syntax(mermaid_result.code)
                
                logger.info("[MERMAID VALIDATION] %s", json.dumps({
                    "valid": validation_error is None,
                    "diagramType": mermaid_result.diagramType,
                    "codeLength": len(mermaid_result.code),
                    "error": validation_error
                }))
                
                if validation_error:
                    logger.warning(f"[MERMAID VALIDATION] Attempt {attempt + 1} failed: {validation_error}")
                    last_error = validation_error
                    continue
                    
                logger.info(f"[MERMAID SPEC] Successfully generated valid mermaid code on attempt {attempt + 1}.")
                return mermaid_result
                
            except Exception as e:
                logger.warning(f"[MERMAID ERROR] Attempt {attempt + 1} failed during LLM generation: {e}")
                last_error = str(e)
                
        logger.error(f"[MERMAID ERROR] Failed to generate valid mermaid code after 3 attempts.")
        raise MermaidGenerationError(f"Could not generate a valid Mermaid diagram. Last error: {last_error}")

mermaid_generation_service = MermaidGenerationService()
