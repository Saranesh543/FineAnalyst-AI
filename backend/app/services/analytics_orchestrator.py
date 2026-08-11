"""
Analytics Orchestrator Service

Orchestrates the complete analytics workflow by chaining all individual modules:
Schema Discovery -> SQL Generation -> SQL Execution -> Visualization -> Insight.
"""

from __future__ import annotations

import logging
import time

from app.schemas.analyze import AnalyzeResponse, WorkflowStep
from app.schemas.sql import SQLGenerationResponse
from app.schemas.insight import BusinessInsightResponse
from app.schemas.intent import QueryPlan, Intent
from app.schemas.agent import MessageTurn
from app.services.business_insight_service import business_insight_service
from app.services.chart_intelligence_service import chart_intelligence_service
from app.services.mermaid_generation_service import mermaid_generation_service
from app.services.query_understanding_service import query_understanding_service
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
        
        # -----------------------------------------------------------------------
        # 0. Inline Data Extraction
        # -----------------------------------------------------------------------
        from app.services.inline_data_extractor import extract_inline_data
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncio
        
        clean_question, inline_df, has_inline_data = extract_inline_data(question)
        custom_engine = None
        inline_columns = None
        # Recover inline data from history if missing
        if not has_inline_data and history:
            for turn in reversed(history):
                if turn.role.value == "user":
                    _, prev_df, prev_has_inline = extract_inline_data(turn.content)
                    if prev_has_inline:
                        inline_df = prev_df
                        has_inline_data = True
                        logger.info("[%s] Recovered inline data from previous conversation history", request_id)
                        break
        
        if has_inline_data and inline_df is not None:
            logger.info("[%s] Inline data detected. Creating in-memory SQLite engine.", request_id)
            logger.info(
                "\n[Analytics] Data Source: user_inline_data\n"
                "[Analytics] Inline Data Detected: true\n"
                "[Analytics] Inline Rows: %d\n"
                "[Analytics] Inline Columns: %s\n"
                "[Analytics] Clean Question: %s\n"
                "[Analytics] Database Fallback: false",
                len(inline_df),
                ", ".join(inline_df.columns),
                clean_question
            )
            custom_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with custom_engine.connect() as conn:
                await conn.run_sync(lambda sync_conn: inline_df.to_sql('user_inline_data', sync_conn, index=False))
            
            # Do NOT overwrite question with clean_question so intent routing has full context
            inline_columns = [str(c) for c in inline_df.columns]
        
        # Fetch file attachments if session_id is provided
        attachments = []
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
            except Exception as e:
                logger.error("Failed to fetch attachments for orchestrator context: %s", e)

        # -----------------------------------------------------------------------
        # 1. Query Understanding
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        
        previous_query_plan = None
        if history:
            # Active Dataset Isolation: If a new inline dataset is provided, scrub old SQL and QueryPlans
            # to prevent the AI from hallucinating columns from previous datasets.
            if inline_columns:
                import re
                for turn in history:
                    if turn.role.value == "assistant":
                        turn.content = re.sub(r'\[Previous QueryPlan:.*?\]', '', turn.content, flags=re.DOTALL)
                        turn.content = re.sub(r'\[Previous SQL Query Executed:.*?\]', '', turn.content, flags=re.DOTALL)
                        turn.content = turn.content.strip()

            import json
            for turn in reversed(history):
                if turn.role.value == "assistant" and "[Previous QueryPlan:" in turn.content:
                    start_idx = turn.content.find("[Previous QueryPlan:")
                    if start_idx != -1:
                        json_str_part = turn.content[start_idx + len("[Previous QueryPlan:"):].strip()
                        if json_str_part.endswith("]"):
                            json_str_part = json_str_part[:-1].strip()
                        else:
                            last_bracket = json_str_part.rfind("]")
                            if last_bracket != -1:
                                json_str_part = json_str_part[:last_bracket].strip()
                        try:
                            previous_query_plan_data = json.loads(json_str_part)
                            previous_query_plan = QueryPlan(**previous_query_plan_data)
                            logger.info("[%s] Recovered previous QueryPlan from history", request_id)
                            break
                        except Exception as e:
                            logger.warning("[%s] Failed to parse previous QueryPlan: %s", request_id, e)
                            continue
        
        try:
            query_plan = await query_understanding_service.understand(
                question, 
                history=history, 
                inline_columns=inline_columns,
                previous_query_plan=previous_query_plan
            )
            
            # Use corrected message internally if available, else original
            internal_query = query_plan.corrected_message if query_plan.corrected_message else question
            
            logger.info("[%s] QueryPlan intent: %s | internal_query: %r", request_id, query_plan.intent, internal_query)
            logger.info("[%s] QueryPlan: %s", request_id, query_plan.model_dump_json())
            
            # Clarification Check
            if query_plan.clarification_needed and query_plan.clarification_question:
                logger.info("[%s] Clarification needed: %s", request_id, query_plan.clarification_question)
                return AnalyzeResponse(
                    question=question,
                    intent=query_plan.intent,
                    query_plan=query_plan.model_dump(mode="json"),
                    clarification_question=query_plan.clarification_question,
                    sql=None,
                    execution=None,
                    visualization=None,
                    insight=None,
                    steps=[WorkflowStep(
                        name="intent_routing",
                        status="done",
                        detail=query_plan.model_dump_json(),
                        duration_ms=(time.perf_counter() - step_start) * 1000
                    )]
                )
            
            if query_plan.intent in (Intent.CONVERSATION, Intent.KNOWLEDGE):
                return AnalyzeResponse(
                    question=question,
                    intent=query_plan.intent,
                    query_plan=query_plan.model_dump(mode="json"),
                    clarification_question=query_plan.clarification_question,
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
                
            if query_plan.requested_visualization and (isinstance(query_plan.requested_visualization, dict) and query_plan.requested_visualization.get("visualization") == "mermaid") or (hasattr(query_plan.requested_visualization, "visualization") and query_plan.requested_visualization.visualization == "mermaid"):
                logger.info("[MERMAID DECISION] %s", json.dumps({
                    "visualization": "mermaid",
                    "diagramType": (query_plan.requested_visualization.get("diagramType") if isinstance(query_plan.requested_visualization, dict) else getattr(query_plan.requested_visualization, "diagramType", None)),
                    "requires_db": getattr(query_plan, "requires_database", False)
                }))

            steps.append(WorkflowStep(
                name="intent_routing",
                status="done",
                detail=query_plan.model_dump_json(),
                duration_ms=(time.perf_counter() - step_start) * 1000
            ))
                
            if query_plan.intent == Intent.SCHEMA:
                logger.info("[%s] Fetching schema for SCHEMA intent...", request_id)
                step_start = time.perf_counter()
                schema_response = await schema_service.get_schema(user_id=user_id, session_id=session_id, custom_engine=custom_engine)
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
                    intent=query_plan.intent,
                    query_plan=query_plan.model_dump(mode="json"),
                    sql=None,
                    execution=None,
                    visualization=None,
                    insight=insight,
                    confidence_score="High",
                    steps=steps
                )
        except Exception as exc:
            logger.exception("[%s] Query understanding failed: %s", request_id, exc)
            raise AnalyticsWorkflowError(f"Query understanding failed: {exc}", stage="intent_routing", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # 2. Schema Discovery
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Discovering schema...", request_id)
            schema_response = await schema_service.get_schema(user_id=user_id, session_id=session_id, custom_engine=custom_engine)
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
        # SQL Generation & Execution with 3-Attempt Retry Loop
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        sql_response = None
        execution_response = None
        last_error = None
        
        att_file = attachments[0].filename if attachments else "None"
        att_id = attachments[0].id if attachments else "None"
        att_table = attachments[0].table_name if attachments else "None"
        att_type = attachments[0].file_type if attachments else "None"
        
        if has_inline_data:
            selected_table = "user_inline_data"
        elif attachments:
            selected_table = att_table
        else:
            selected_table = "application_db"
            
        logger.info(
            "\n[Analytics] PreviousContext: %s\n"
            "[Analytics] NewQuestion: %s\n"
            "[Analytics] MergedQueryPlan: %s\n"
            "[Analytics] SelectedTable: %s\n"
            "[Analytics] Schema: %s",
            "Found" if previous_query_plan else "None",
            internal_query,
            query_plan.model_dump_json(),
            selected_table,
            [t.name for t in schema_response.tables]
        )

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("[%s] SQL Generation Attempt %d/%d...", request_id, attempt, max_attempts)
                
                if attempt == 1:
                    sql_response = await sql_generator_service.generate(internal_query, schema_response, query_plan=query_plan, history=history)
                else:
                    logger.warning("[%s] Retrying SQL generation due to previous error...", request_id)
                    from app.services.sql_validator_service import SQLSchemaValidationError
                    
                    if not isinstance(last_error, SQLSchemaValidationError):
                        # Wrap generic execution errors in a schema validation error so the prompt works
                        error_to_pass = SQLSchemaValidationError(
                            message=str(last_error),
                            type_="execution_error",
                            suggestions=[]
                        )
                    else:
                        error_to_pass = last_error

                    sql_response = await sql_generator_service.generate_retry(
                        question=internal_query,
                        schema=schema_response,
                        query_plan=query_plan,
                        previous_sql=sql_response.sql if sql_response else getattr(last_error, "sql", ""),
                        validation_error=error_to_pass
                    )
                    
                logger.info("[Analytics] SQL: %s", sql_response.sql)
                
                logger.info("[%s] Executing SQL Attempt %d/%d...", request_id, attempt, max_attempts)
                execution_response = await sql_executor_service.execute_sql(sql_response.sql, user_id=user_id, custom_engine=custom_engine, user_question=internal_query)
                logger.info("[%s] Rows returned: %d", request_id, execution_response.row_count)
                
                # If execution succeeds, break out of the retry loop
                steps.append(WorkflowStep(
                    name="sql_generation",
                    status="done",
                    detail=sql_response.sql,
                    duration_ms=(time.perf_counter() - step_start) * 1000
                ))
                steps.append(WorkflowStep(
                    name="sql_execution",
                    status="done",
                    duration_ms=(time.perf_counter() - step_start) * 1000
                ))
                break
                
            except Exception as exc:
                last_error = exc
                if isinstance(exc, ModelHTTPError) and (exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower()):
                    logger.exception("[%s] Rate limit exceeded during SQL loop: %s", request_id, exc)
                    raise AnalyticsWorkflowError(f"Rate limit exceeded: {exc}", stage="rate_limited", original_error=exc, steps=steps) from exc
                
                logger.error("[%s] SQL generation or execution failed on attempt %d: %s", request_id, attempt, str(exc))
                
                if attempt == max_attempts:
                    steps.append(WorkflowStep(
                        name="sql_generation_execution",
                        status="error",
                        detail=str(exc)
                    ))
                    logger.exception("[%s] All %d attempts failed. Last error: %s", request_id, max_attempts, exc)
                    
                    # -----------------------------------------------------------
                    # DETERMINISTIC FALLBACK
                    # -----------------------------------------------------------
                    logger.info("[%s] Triggering deterministic fallback.", request_id)
                    fallback_sql = f"SELECT * FROM {selected_table} LIMIT 100;"
                    try:
                        execution_response = await sql_executor_service.execute_sql(fallback_sql, user_id=user_id, custom_engine=custom_engine, user_question=internal_query)
                        sql_response = SQLGenerationResponse(sql=fallback_sql, question=internal_query, dialect=schema_response.dialect)
                        steps.append(WorkflowStep(
                            name="sql_generation",
                            status="done",
                            detail=fallback_sql,
                            duration_ms=(time.perf_counter() - step_start) * 1000
                        ))
                        break # Successfully recovered via fallback
                    except Exception as fallback_exc:
                        raise AnalyticsWorkflowError(f"SQL generation/execution and fallback failed: {exc}. Fallback error: {fallback_exc}", stage="sql_execution", original_error=exc, steps=steps) from exc

        # -----------------------------------------------------------------------
        # 4. Visualization Recommendation
        # -----------------------------------------------------------------------
        step_start = time.perf_counter()
        try:
            logger.info("[%s] Recommending visualization...", request_id)
            vis_responses = chart_intelligence_service.select_charts(
                question=internal_query, execution_result=execution_response, query_plan=query_plan
            )
            logger.info("[%s] %d visualizations recommended", request_id, len(vis_responses))
            
            # Post-process mermaid generation
            for v in vis_responses:
                if v.chart == "mermaid":
                    try:
                        logger.info("[%s] Generating Mermaid syntax for chart", request_id)
                        mermaid_code = await mermaid_generation_service.generate_mermaid(
                            question=internal_query,
                            execution_result=execution_response
                        )
                        if v.metadata:
                            v.metadata.mermaid_code = mermaid_code
                    except Exception as e:
                        logger.warning("[%s] Failed to generate mermaid: %s", request_id, e)
                        v.chart = "data_grid"
                        if v.metadata:
                            v.metadata.chart_type = "data_grid"
            
            for v in vis_responses:
                logger.info("[%s] Chart: %s | Title: %s", request_id, v.chart, getattr(v.metadata, 'title', None))
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
                visualizations=vis_responses,
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
        base_confidence = (sum(v.confidence for v in vis_responses) / len(vis_responses)) if vis_responses else 0.8
        
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
            intent=query_plan.intent,
            query_plan=query_plan.model_dump(mode="json"),
            sql=sql_response.sql,
            execution=execution_response,
            visualizations=vis_responses,
            insight=insight_response,
            chart_metadata=[v.metadata.model_dump() for v in vis_responses if v.metadata],
            visualization_confidence=vis_responses[0].confidence if vis_responses else 0.0,
            confidence_score=confidence_score,
            steps=steps
        )
        
        # Log MERMAID RESPONSE if applicable
        if vis_responses and any(v.chart == "mermaid" for v in vis_responses):
            logger.info("[MERMAID RESPONSE] %s", json.dumps([v.model_dump() for v in vis_responses if v.chart == "mermaid"]))

        return final_response


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
analytics_orchestrator = AnalyticsOrchestratorService()
