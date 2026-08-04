"""
Business Insight Service

Uses the AI Agent to analyze SQL execution results
and generate executive summaries, key findings, and recommended next questions.
"""

from __future__ import annotations

import logging
import time

from pydantic_ai import Agent, RunContext
from app.services.llm_provider import get_llm_model

from app.config.settings import settings
from app.schemas.execution import SQLExecutionResponse
from app.schemas.insight import BusinessInsightResponse
from app.schemas.visualization import VisualizationRecommendation

logger = logging.getLogger(__name__)


class BusinessInsightError(Exception):
    """Raised when the AI fails to generate an insight."""


# ---------------------------------------------------------------------------
# Prompt & Agent Definition
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are FineAnalyst AI, a professional Business Intelligence engine.
Your task is to analyze raw database results and generate an executive summary.

CRITICAL DATA BINDING RULES:
1. NEVER fabricate or hallucinate numbers, values, companies, countries, products, or ANY categorical data.
2. You MUST strictly use ONLY the exact names, entities, and numerical values present in the provided "--- DATA EXECUTED ---" rows.
3. If the SQL returns "Smith Ltd", your summary MUST say "Smith Ltd" exactly.
4. If a company, country, or entity is NOT in the rows, DO NOT mention it.
5. If the data is empty or returns no rows, you MUST explicitly state that no data was returned instead of fabricating an answer.

OUTPUT RULES:
1. Provide a concise executive summary based STRICTLY on the rows. MAX 2 SENTENCES. NEVER mention "assumptions", "sample database", "hypothetical data", or "imaginary context". Just state the facts.
2. Generate 3-6 key findings as concise bullet points. You MUST identify highest/lowest values, top/bottom performers, growth/decline, or significant differences if applicable.
3. Generate KPI Cards from the overall data. Format them properly (e.g., format="currency", "percentage", "decimal", "compact", or "text"). Do not invent KPIs not supported by the data.
4. Identify any obvious anomalies or outliers in the provided data. If none, leave empty.
5. Recommend 3-5 actionable business recommendations derived ONLY from this data. Do not generate generic advice (e.g., "Review revenue", "Improve performance"). If there is insufficient evidence, return exactly: "No evidence-based recommendation could be generated."
6. Generate 3-5 intelligent suggested follow-up questions (e.g., "Show monthly revenue", "Compare by country", "Revenue trend"). NEVER copy recommendations into suggested questions.
"""


def _get_insight_agent() -> Agent[None, BusinessInsightResponse]:
    """Lazy initialization of the PydanticAI agent."""
    model = get_llm_model()
    
    return Agent(
        model=model,
        output_type=BusinessInsightResponse,
        system_prompt=_SYSTEM_PROMPT,
        retries=2,
    )


def _build_insight_prompt(
    question: str,
    execution_result: SQLExecutionResponse,
    visualization: VisualizationRecommendation,
) -> str:
    """Constructs the prompt string with all context needed for the AI."""
    
    # Truncate rows if too large to prevent token limits.
    max_rows = 500
    rows_to_show = execution_result.rows[:max_rows]
    truncated_msg = ""
    if execution_result.row_count > max_rows:
        truncated_msg = f" (Showing first {max_rows} of {execution_result.row_count} rows)"

    lines = [
        f"Original Question: {question}",
        f"Recommended Chart: {visualization.chart} (Confidence: {visualization.confidence})",
        f"Chart Reason: {visualization.reason}",
        "",
        "--- DATA EXECUTED ---",
        f"Columns: {execution_result.columns}",
        f"Rows Returned: {execution_result.row_count}{truncated_msg}",
        "",
        "Rows:"
    ]
    
    for row in rows_to_show:
        lines.append(str(row))
        
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BusinessInsightService:
    """Service to generate business insights from data."""

    def __init__(self) -> None:
        self._agent: Agent[None, BusinessInsightResponse] | None = None
        logger.debug("BusinessInsightService initialised.")

    @property
    def agent(self) -> Agent[None, BusinessInsightResponse]:
        if self._agent is None:
            self._agent = _get_insight_agent()
        return self._agent

    async def generate_insight(
        self,
        question: str,
        execution_result: SQLExecutionResponse,
        visualization: VisualizationRecommendation,
    ) -> BusinessInsightResponse:
        """
        Generate business insights from the execution results.

        If the data is empty, it bypasses the LLM and returns a static explanation.
        """
        request_id = f"insight-{int(time.time() * 1000)}"
        t_start = time.perf_counter()

        logger.info(
            "[%s] Insight generation request received | rows=%d",
            request_id,
            execution_result.row_count,
        )

        # Handle empty results gracefully without burning LLM tokens
        if execution_result.row_count == 0:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            logger.info("[%s] Insight generated for empty data | elapsed=%.1f ms", request_id, elapsed_ms)
            return BusinessInsightResponse(
                summary="The query returned no data to analyze.",
                kpi_cards=[],
                key_findings=["No records matched the criteria for this question."],
                anomalies=[],
                recommendations=[
                    "Check if the date range or filters applied are correct.",
                    "Try broadening the search criteria."
                ],
                suggested_questions=[
                    "Show total revenue",
                    "List all customers"
                ]
            )

        prompt = _build_insight_prompt(question, execution_result, visualization)

        try:
            result = await self.agent.run(prompt)
            insight = result.output
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            
            raw_response = "Unknown"
            validation_errors = "Unknown"
            
            from pydantic_ai.exceptions import UnexpectedModelBehavior
            from pydantic import ValidationError
            if isinstance(exc, UnexpectedModelBehavior):
                # Pydantic-AI raises this when the model returns invalid JSON or fails validation.
                if hasattr(exc, "cause") and isinstance(exc.cause, ValidationError):
                    validation_errors = str(exc.cause)
                elif hasattr(exc, "__cause__") and isinstance(exc.__cause__, ValidationError):
                    validation_errors = str(exc.__cause__)
                else:
                    validation_errors = str(exc)
                logger.error(f"[{request_id}] RAW LLM VALIDATION ERRORS:\n{validation_errors}")
                
            logger.exception(
                "[%s] Insight generation failed | elapsed=%.1f ms | error=%s",
                request_id,
                elapsed_ms,
                exc,
            )
            
            # Print EXACT stack trace, SQL results, raw LLM for the user (in console only)
            print("--- ANALYTICS PIPELINE DEBUG ---")
            print(f"STAGE: insight")
            print(f"SQL RESULTS SENT TO LLM:\n{execution_result.model_dump_json(indent=2)}")
            print(f"VALIDATION ERRORS:\n{validation_errors}")
            import traceback
            print(f"STACK TRACE:\n{''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))}")
            print("--------------------------------")
            
            # Graceful fallback so the pipeline doesn't fail
            insight = BusinessInsightResponse(
                summary=f"Data was successfully retrieved ({execution_result.row_count} rows), but AI insights could not be generated due to a temporary model formatting issue.",
                kpi_cards=[],
                key_findings=["AI analysis is temporarily unavailable."],
                anomalies=[],
                recommendations=["Review the raw data table below for insights."],
                suggested_questions=["Retry query", "Show total revenue"]
            )

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "[%s] Insight generated | elapsed=%.1f ms | findings=%d",
            request_id,
            elapsed_ms,
            len(insight.key_findings),
        )

        return insight


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
business_insight_service = BusinessInsightService()
