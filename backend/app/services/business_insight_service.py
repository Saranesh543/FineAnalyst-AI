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
You are FineAnalyst AI, a Business Intelligence engine.
Your task is to analyze raw database results and generate an executive summary.

Rules:
1. NEVER fabricate or hallucinate numbers. Use ONLY the data provided.
2. Provide a 2-4 sentence executive summary.
3. Provide 3-5 key findings (bullet points).
4. Identify any obvious anomalies or outliers in the data. If none, leave empty.
5. Recommend 2-3 logical follow-up questions the user should ask next.
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
                key_findings=["No records matched the criteria for this question."],
                anomalies=[],
                recommendations=[
                    "Check if the date range or filters applied are correct.",
                    "Try broadening the search criteria."
                ]
            )

        prompt = _build_insight_prompt(question, execution_result, visualization)

        try:
            result = await self.agent.run(prompt)
            insight = result.output
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            logger.exception(
                "[%s] Insight generation failed | elapsed=%.1f ms | error=%s",
                request_id,
                elapsed_ms,
                exc,
            )
            raise BusinessInsightError(f"Failed to generate insight: {exc}") from exc

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
