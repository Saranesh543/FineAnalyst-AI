"""
Analytics Orchestrator Service

Orchestrates the complete analytics workflow by chaining all individual modules:
Schema Discovery -> SQL Generation -> SQL Execution -> Visualization -> Insight.
"""

from __future__ import annotations

import logging
import time

from app.schemas.analyze import AnalyzeResponse, WorkflowStep
from app.schemas.insight import BusinessInsightResponse
from app.schemas.intent import Intent
from app.schemas.agent import MessageTurn
from app.services.business_insight_service import business_insight_service
from app.services.chart_intelligence_service import chart_intelligence_service
from app.services.intent_router import intent_router
from app.services.schema_service import schema_service
from app.services.sql_executor_service import sql_executor_service
from app.services.sql_generator_service import sql_generator_service
from app.services.sql_validator_service import SQLSchemaValidationError
from app.utils.exceptions import AppException
from pydantic_ai.exceptions import ModelHTTPError

logger = logging.getLogger(__name__)


class AnalyticsWorkflowError(AppException):
    """Raised when any stage of the analytics workflow fails."""
    
    def __init__(self, message: str, stage: str, original_error: Exception | None = None, steps: list[WorkflowStep] | None = None):
        super().__init__(message=message, status_code=400)
        self.stage = stage
        self.original_error = original_error
        self.steps = steps or []


class AnalyticsOrchestratorService:
    """Singleton service for executing the end-to-end analytical pipeline."""

    def __init__(self) -> None:
        logger.debug("AnalyticsOrchestratorService initialised.")

    async def analyze(self, question: str, history: list[MessageTurn] | None = None, user_id: int | None = None, session_id: str | None = None) -> AnalyzeResponse:
        """
        Executes the full analytics workflow.

        Args:
            question: The user's natural language question.
            history: Optional list of previous questions for context.
            user_id: Optional ID of the user requesting the analysis.
            session_id: Optional session ID to fetch attachments.
        """
        t_start = time.perf_counter()
        request_id = id(self)
        logger.info("[%s] Starting analytics workflow for question: %s", request_id, question)
        
        steps: list[WorkflowStep] = []
        
        context_injected_question = question
        
        # Inject file attachments if session_id is provided
        if session_id and user_id:
            try:
                from sqlalchemy.ext.asyncio import AsyncSession
                from app.database.session import AsyncSessionLocal
                from sqlalchemy import select
                from app.models.chat import FileAttachment
                
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(FileAttachment).where(
                            FileAttachment.session_id == session_id,
                            FileAttachment.user_id == user_id
                        )
                    )
                    attachments = result.scalars().all()
                    
                    if attachments:
                        logger.info("[%s] Resolved %d uploaded files for session_id=%s", request_id, len(attachments), session_id)
                        file_context = "Context from uploaded files:\n"
                        for att in attachments:
                            logger.info("[%s] Including attachment: %s (type=%s, table=%s)", request_id, att.filename, att.file_type, att.table_name)
                            if att.table_name:
                                file_context += f"--- {att.filename} ---\nThis structured file was imported into the database table `{att.table_name}`. Query this table to answer questions about this file.\n\n"
                            elif att.extracted_text:
                                file_context += f"--- {att.filename} ---\n{att.extracted_text[:10000]}\n\n"
                        
                        context_injected_question = f"{file_context}\n\nUser Question:\n{question}"
                        logger.info("[%s] Final injected context input:\n%s", request_id, context_injected_question[:500] + ("..." if len(context_injected_question) > 500 else ""))
            except Exception as e:
                logger.error("Failed to fetch attachments for orchestrator context: %s", e)

        # -----------------------------------------------------------------------
        # 1. Intent Classification
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            intent_result = await intent_router.classify(context_injected_question, history=history)
            
            # Use corrected message internally if available, else original
            internal_query = intent_result.corrected_message if intent_result.corrected_message else context_injected_question
            
            logger.info("[%s] Classified intent: %s | internal_query: %r", request_id, intent_result.intent, internal_query)
            
            if intent_result.intent in (Intent.CONVERSATION, Intent.KNOWLEDGE):
                return AnalyzeResponse(
                    question=question,
                    intent=intent_result.intent,
                    sql=None,
                    execution=None,
                    visualization=None,
                    insight=None,
                    steps=[WorkflowStep(
                        name="Responding...",
                        status="done",
                        duration_ms=(time.perf_counter() - step_start) * 1000
                    )]
                )
                
            steps.append(WorkflowStep(
                name="intent_routing",
                status="done",
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
                
            if intent_result.intent == Intent.SCHEMA:
                logger.info("[%s] Fetching schema for SCHEMA intent...", request_id)
                step_start = time.perf_counter()
                schema_response = await schema_service.get_schema(user_id=user_id)
                steps.append(WorkflowStep(
                    name="schema_discovery",
                    status="done",
                    duration_ms=(time.perf_counter() - step_start) * 1000
                ))
                steps.append(WorkflowStep(name="sql_generation", status="skipped"))
                steps.append(WorkflowStep(name="sql_execution", status="skipped"))
                
                # Build detailed markdown response
                db_name = schema_response.database or "Unknown"
                dialect = schema_response.dialect or "Unknown"
                table_count = schema_response.table_count
                
                md_parts = [
                    f"**Database:** {db_name} ({dialect})",
                    f"**Total Tables:** {table_count}\n",
                ]
                
                for table in schema_response.tables:
                    col_names = [c.name for c in table.columns]
                    fks = [f"-> {fk.referred_table}" for fk in table.foreign_keys]
                    md_parts.append(f"#### Table: `{table.name}`")
                    md_parts.append(f"- **Columns:** {', '.join(col_names)}")
                    if fks:
                        md_parts.append(f"- **Relationships:** {', '.join(fks)}")
                    if table.row_count is not None:
                        md_parts.append(f"- **Rows:** {table.row_count:,}")
                    md_parts.append("")
                
                detailed_analysis = "\n".join(md_parts)
                
                insight = BusinessInsightResponse(
                    summary="Here is the metadata and schema information for the connected database.",
                    kpi_cards=[],
                    key_findings=[f"Discovered {table_count} tables in the {dialect} database."],
                    detailed_analysis=detailed_analysis,
                    anomalies=[],
                    recommendations=["Ask analytical questions to query data from these tables."],
                    suggested_questions=["Show top customers", "What is the total revenue?"],
                    conclusion="Database schema successfully retrieved."
                )
                
                return AnalyzeResponse(
                    question=question,
                    intent=intent_result.intent,
                    sql=None,
                    execution=None,
                    visualization=None,
                    insight=insight,
                    confidence_score="High",
                    steps=steps
                )
        except Exception as exc:
            logger.exception("[%s] Intent classification failed: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"Intent routing failed: {exc}", stage="intent_routing", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # 2. Schema Discovery
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Discovering schema...", request_id)
            schema_response = await schema_service.get_schema(user_id=user_id)
            logger.info("[%s] Discovered %d tables", request_id, len(schema_response.tables))
            steps.append(WorkflowStep(
                name="schema_discovery",
                status="done",
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
        except Exception as exc:
            steps.append(WorkflowStep(
                name="schema_discovery",
                status="error",
                detail=str(exc)
            ))
            if isinstance(exc, ModelHTTPError) and (exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower()):
                logger.exception("[%s] Workflow failed at schema discovery due to rate limit: %s", request_id, exc)
                raise AnalyticsWorkflowError(f"Rate limit exceeded: {exc}", stage="rate_limited", original_error=exc, steps=steps) from exc
            logger.exception("[%s] Workflow failed at schema discovery: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"Schema discovery failed: {exc}", stage="schema", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # SQL Generation
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Generating SQL...", request_id)
            sql_response = await sql_generator_service.generate(internal_query, schema_response, history=history)
            logger.info("[%s] SQL generated", request_id)
            steps.append(WorkflowStep(
                name="sql_generation",
                status="done",
                detail=sql_response.sql,
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
        except SQLSchemaValidationError as exc:
            logger.warning("[%s] Schema validation failed. Attempting retry...", request_id)
            try:
                sql_response = await sql_generator_service.generate_retry(
                    question=internal_query,
                    schema=schema_response,
                    previous_sql=getattr(exc, "sql", ""),
                    validation_error=exc
                )
                logger.info("[%s] SQL generated successfully on retry", request_id)
                steps.append(WorkflowStep(
                    name="sql_generation",
                    status="done",
                    detail=sql_response.sql,
                    duration_ms=(time.perf_counter() - step_start) * 1000
                ))
            except SQLSchemaValidationError as retry_exc:
                # If retry ALSO fails schema validation, it's an impossible question.
                logger.info("[%s] Impossible question detected via schema validation failure: %s", request_id, retry_exc)
                steps.append(WorkflowStep(
                    name="sql_generation",
                    status="skipped",
                    detail="Requested data does not exist in the database.",
                    duration_ms=(time.perf_counter() - step_start) * 1000
                ))
                steps.append(WorkflowStep(name="sql_execution", status="skipped"))
                steps.append(WorkflowStep(name="visualization", status="skipped"))
                
                step_start = time.perf_counter()
                try:
                    insight = await business_insight_service.generate_impossible_insight(
                        question=internal_query,
                        schema=schema_response
                    )
                    steps.append(WorkflowStep(
                        name="insight_generation",
                        status="done",
                        duration_ms=(time.perf_counter() - step_start) * 1000
                    ))
                except Exception as insight_exc:
                    steps.append(WorkflowStep(
                        name="insight_generation",
                        status="error",
                        detail=str(insight_exc)
                    ))
                    raise AnalyticsWorkflowError(f"Insight generation failed for impossible query: {insight_exc}", stage="insight", original_error=insight_exc, steps=steps) from insight_exc
                
                return AnalyzeResponse(
                    question=question,
                    intent=intent_result.intent,
                    sql=None,
                    execution=None,
                    visualization=None,
                    insight=insight,
                    confidence_score="Low",
                    steps=steps
                )
            except Exception as retry_exc:
                steps.append(WorkflowStep(
                    name="sql_generation",
                    status="error",
                    detail=str(retry_exc)
                ))
                if isinstance(retry_exc, ModelHTTPError) and (retry_exc.status_code == 429 or "rate_limit_exceeded" in str(retry_exc).lower()):
                    logger.exception("[%s] Workflow failed at SQL generation retry due to rate limit: %s", request_id, retry_exc)
                    raise AnalyticsWorkflowError(f"Rate limit exceeded: {retry_exc}", stage="rate_limited", original_error=retry_exc, steps=steps) from retry_exc
                logger.exception("[%s] Workflow failed at SQL generation retry: %s | Type: %s", request_id, retry_exc, type(retry_exc).__name__)
                raise AnalyticsWorkflowError(f"SQL generation failed on retry: {retry_exc}", stage="sql_generation", original_error=retry_exc, steps=steps) from retry_exc
        except Exception as exc:
            steps.append(WorkflowStep(
                name="sql_generation",
                status="error",
                detail=str(exc)
            ))
            if isinstance(exc, ModelHTTPError) and (exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower()):
                logger.exception("[%s] Workflow failed at SQL generation due to rate limit: %s", request_id, exc)
                raise AnalyticsWorkflowError(f"Rate limit exceeded: {exc}", stage="rate_limited", original_error=exc, steps=steps) from exc
            logger.exception("[%s] Workflow failed at SQL generation: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"SQL generation failed: {exc}", stage="sql_generation", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # 3. SQL Execution
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Executing SQL...", request_id)
            execution_response = await sql_executor_service.execute_sql(sql_response.sql, user_id=user_id, user_question=internal_query)
            logger.info("[%s] Rows returned: %d", request_id, execution_response.row_count)
            steps.append(WorkflowStep(
                name="sql_execution",
                status="done",
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
        except Exception as exc:
            steps.append(WorkflowStep(
                name="sql_execution",
                status="error",
                detail=str(exc)
            ))
            if isinstance(exc, ModelHTTPError) and (exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower()):
                logger.exception("[%s] Workflow failed at SQL execution due to rate limit: %s", request_id, exc)
                raise AnalyticsWorkflowError(f"Rate limit exceeded: {exc}", stage="rate_limited", original_error=exc, steps=steps) from exc
            logger.exception("[%s] Workflow failed at SQL execution: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"SQL execution failed: {exc}", stage="sql_execution", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # 4. Visualization Recommendation
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Recommending visualization...", request_id)
            vis_response = chart_intelligence_service.select_chart(
                question=internal_query, execution_result=execution_response
            )
            logger.info("[%s] Visualization recommended: %s | confidence: %s | reason: %s | row_count: %s", 
                        request_id, vis_response.chart, vis_response.confidence, vis_response.reason, execution_response.row_count)
            if vis_response.metadata:
                logger.info("[%s] Metadata: title='%s', subtitle='%s'", request_id, vis_response.metadata.title, vis_response.metadata.subtitle)
            steps.append(WorkflowStep(
                name="visualization",
                status="done",
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
        except Exception as exc:
            steps.append(WorkflowStep(
                name="visualization",
                status="error",
                detail=str(exc)
            ))
            if isinstance(exc, ModelHTTPError) and (exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower()):
                logger.exception("[%s] Workflow failed at visualization recommendation due to rate limit: %s", request_id, exc)
                raise AnalyticsWorkflowError(f"Rate limit exceeded: {exc}", stage="rate_limited", original_error=exc, steps=steps) from exc
            logger.exception("[%s] Workflow failed at visualization recommendation: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"Visualization recommendation failed: {exc}", stage="visualization", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # 5. Business Insight Generation
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Generating insights...", request_id)
            insight_response = await business_insight_service.generate_insight(
                question=internal_query,
                execution_result=execution_response,
                visualization=vis_response,
            )
            logger.info("[%s] Finished", request_id)
            steps.append(WorkflowStep(
                name="insight_generation",
                status="done",
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
        except Exception as exc:
            steps.append(WorkflowStep(
                name="insight_generation",
                status="error",
                detail=str(exc)
            ))
            if isinstance(exc, ModelHTTPError) and (exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower()):
                logger.exception("[%s] Workflow failed at insight generation due to rate limit: %s", request_id, exc)
                raise AnalyticsWorkflowError(f"Rate limit exceeded: {exc}", stage="rate_limited", original_error=exc, steps=steps) from exc
            logger.exception("[%s] Workflow failed at insight generation: %s | Type: %s", request_id, exc, type(exc).__name__)
            raise AnalyticsWorkflowError(f"Insight generation failed: {exc}", stage="insight", original_error=exc, steps=steps) from exc

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
            chart_metadata=vis_response.metadata.model_dump() if vis_response and vis_response.metadata else None,
            visualization_confidence=vis_response.confidence,
            confidence_score=confidence_score,
            steps=steps
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
analytics_orchestrator = AnalyticsOrchestratorService()
