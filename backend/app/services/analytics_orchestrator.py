"""
Analytics Orchestrator Service

Orchestrates the complete analytics workflow by chaining all individual modules:
Schema Discovery -> SQL Generation -> SQL Execution -> Visualization -> Insight.
"""

from __future__ import annotations

import logging
import time

from app.schemas.analyze import AnalyzeResponse
from app.schemas.intent import Intent
from app.services.business_insight_service import business_insight_service
from app.services.chart_recommender_service import chart_recommender_service
from app.services.intent_router import intent_router
from app.services.schema_service import schema_service
from app.services.sql_executor_service import sql_executor_service
from app.services.sql_generator_service import sql_generator_service
from app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


class AnalyticsWorkflowError(AppException):
    """Raised when any stage of the analytics workflow fails."""
    
    def __init__(self, message: str, stage: str, original_error: Exception | None = None):
        super().__init__(message=message, status_code=400)
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
        # 0. Intent Routing
        # -----------------------------------------------------------------------
        try:
            intent_result = await intent_router.classify(question)
            logger.info("[%s] Intent classified as %s", request_id, intent_result.intent)

            if intent_result.intent in (Intent.CONVERSATION, Intent.KNOWLEDGE):
                return AnalyzeResponse(
                    question=question,
                    intent=intent_result.intent,
                    sql=None,
                    execution=None,
                    visualization=None,
                    insight=None,
                )
        except Exception as exc:
            logger.exception("[%s] Workflow failed at intent routing: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"Intent routing failed: {exc}", stage="intent_routing", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 1. Schema Discovery
        # -----------------------------------------------------------------------
        try:
            logger.info("[%s] Loading schema...", request_id)
            schema_response = await schema_service.get_schema()
            logger.info("[%s] Schema loaded successfully", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at schema discovery: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"Schema discovery failed: {exc}", stage="schema", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 2. SQL Generation
        # -----------------------------------------------------------------------
        try:
            logger.info("[%s] Generating SQL...", request_id)
            sql_response = await sql_generator_service.generate(question, schema_response)
            logger.info("[%s] SQL generated", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at SQL generation: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"SQL generation failed: {exc}", stage="sql_generation", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 3. SQL Execution
        # -----------------------------------------------------------------------
        try:
            logger.info("[%s] Executing SQL...", request_id)
            execution_response = await sql_executor_service.execute_sql(sql_response.sql)
            logger.info("[%s] Rows returned: %d", request_id, execution_response.row_count)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at SQL execution: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"SQL execution failed: {exc}", stage="sql_execution", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 4. Visualization Recommendation
        # -----------------------------------------------------------------------
        try:
            logger.info("[%s] Generating visualization...", request_id)
            vis_response = chart_recommender_service.recommend(question, execution_response)
            logger.info("[%s] Visualization selected", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at visualization recommendation: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"Visualization recommendation failed: {exc}", stage="visualization", original_error=exc) from exc

        # -----------------------------------------------------------------------
        # 5. Business Insight Generation
        # -----------------------------------------------------------------------
        try:
            logger.info("[%s] Generating insights...", request_id)
            insight_response = await business_insight_service.generate_insight(
                question=question,
                execution_result=execution_response,
                visualization=vis_response,
            )
            logger.info("[%s] Finished", request_id)
        except Exception as exc:
            logger.exception("[%s] Workflow failed at insight generation: %s | Type: %s", request_id, exc, type(exc).__name__)
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

        # Calculate dynamic confidence score
        base_confidence = vis_response.confidence if vis_response else 0.8
        
        # Penalize confidence if insight generation fell back to the error object
        if insight_response and insight_response.key_findings == ["AI analysis is temporarily unavailable."]:
            base_confidence -= 0.3
            
        # Penalize if no rows
        if execution_response.row_count == 0:
            base_confidence -= 0.5
            
        if base_confidence >= 0.85:
            confidence_score = "High"
        elif base_confidence >= 0.6:
            confidence_score = "Medium"
        else:
            confidence_score = "Low"

        return AnalyzeResponse(
            question=question,
            intent=Intent.DATABASE.value,
            sql=sql_response.sql,
            execution=execution_response,
            visualization=vis_response,
            insight=insight_response,
            confidence_score=confidence_score,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
analytics_orchestrator = AnalyticsOrchestratorService()
