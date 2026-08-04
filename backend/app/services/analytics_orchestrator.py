"""
Analytics Orchestrator Service

Orchestrates the complete analytics workflow by chaining all individual modules:
Schema Discovery -> SQL Generation -> SQL Execution -> Visualization -> Insight.
"""

from __future__ import annotations

import logging
import time

from app.schemas.analyze import AnalyzeResponse
from app.services.business_insight_service import business_insight_service
from app.services.chart_recommender_service import chart_recommender_service
from app.services.schema_service import schema_service
from app.services.sql_executor_service import sql_executor_service
from app.services.sql_generator_service import sql_generator_service

logger = logging.getLogger(__name__)


class AnalyticsWorkflowError(Exception):
    """Raised when any stage of the analytics workflow fails."""
    
    def __init__(self, message: str, stage: str, original_error: Exception | None = None):
        super().__init__(message)
        self.stage = stage
        self.original_error = original_error


class AnalyticsOrchestratorService:
    """Singleton service for executing the end-to-end analytical pipeline."""

    def __init__(self) -> None:
        logger.debug("AnalyticsOrchestratorService initialised.")

    async def analyze(self, question: str) -> AnalyzeResponse:
        """
        Executes the full analytics workflow.

        Args:
            question: The natural-language business question.

        Returns:
            AnalyzeResponse containing the unified results.

        Raises:
            AnalyticsWorkflowError: If any pipeline stage fails.
        """
        t_start = time.perf_counter()
        request_id = f"workflow-{int(time.time() * 1000)}"

        logger.info("[%s] Analytics workflow started | question=%r", request_id, question)

        # -----------------------------------------------------------------------
        # 1. Schema Discovery
        # -----------------------------------------------------------------------
        try:
            schema_response = await schema_service.get_schema()
            logger.info("[%s] Schema completed", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at schema discovery: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"Schema discovery failed: {exc}", stage="schema", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 2. SQL Generation
        # -----------------------------------------------------------------------
        try:
            sql_response = await sql_generator_service.generate(question, schema_response)
            logger.info("[%s] SQL generated", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at SQL generation: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"SQL generation failed: {exc}", stage="sql_generation", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 3. SQL Execution
        # -----------------------------------------------------------------------
        try:
            execution_response = await sql_executor_service.execute_sql(sql_response.sql)
            logger.info("[%s] SQL executed", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at SQL execution: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"SQL execution failed: {exc}", stage="sql_execution", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 4. Visualization Recommendation
        # -----------------------------------------------------------------------
        try:
            vis_response = chart_recommender_service.recommend(question, execution_response)
            logger.info("[%s] Visualization selected", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at visualization recommendation: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"Visualization recommendation failed: {exc}", stage="visualization", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 5. Business Insight Generation
        # -----------------------------------------------------------------------
        try:
            insight_response = await business_insight_service.generate_insight(
                question=question,
                execution_result=execution_response,
                visualization=vis_response,
            )
            logger.info("[%s] Insight generated", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at insight generation: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"Insight generation failed: {exc}", stage="insight", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # Final Assembly
        # -----------------------------------------------------------------------
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "[%s] Workflow completed | elapsed=%.1f ms",
            request_id,
            elapsed_ms,
        )

        return AnalyzeResponse(
            question=question,
            sql=sql_response.sql,
            execution=execution_response,
            visualization=vis_response,
            insight=insight_response,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
analytics_orchestrator = AnalyticsOrchestratorService()
