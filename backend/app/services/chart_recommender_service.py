"""
Chart Recommender Service

Analyzes a user's question and the resulting data to recommend the most
appropriate visualization format.

Rules:
  - Large datasets (>1000 rows) -> table
  - Time-series -> line
  - Category vs Number -> bar
  - Percentage / Distribution -> pie
  - Two numeric columns -> scatter
  - Single numeric distribution -> histogram
  - Unknown -> table
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime
from typing import Any

from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation

logger = logging.getLogger(__name__)


class ChartRecommenderService:
    """Stateless service for visualization recommendations."""

    def __init__(self) -> None:
        logger.debug("ChartRecommenderService initialised.")

    def recommend(
        self, question: str, execution_result: SQLExecutionResponse
    ) -> VisualizationRecommendation:
        """
        Analyze the question and data to recommend a chart.

        Args:
            question: The original user question.
            execution_result: The SQL execution result to visualize.

        Returns:
            VisualizationRecommendation indicating the best chart type.

        Raises:
            ValueError: If the execution result is entirely empty (no columns).
        """
        t_start = time.perf_counter()
        request_id = f"vis-{int(time.time() * 1000)}"

        logger.info("[%s] Chart recommendation analysis started", request_id)

        if not execution_result.columns:
            raise ValueError("Cannot recommend a chart for an empty result set.")

        row_count = execution_result.row_count
        columns = execution_result.columns
        rows = execution_result.rows

        # --- Rule 1: Large datasets ---
        if row_count > 1000:
            return self._build_recommendation(
                request_id,
                t_start,
                chart="table",
                confidence=1.0,
                reason="Large datasets (>1000 rows) are best presented as a table.",
            )

        # --- Rule 2: Empty data (but has columns) ---
        if row_count == 0:
            return self._build_recommendation(
                request_id,
                t_start,
                chart="table",
                confidence=1.0,
                reason="Result set is empty, rendering as an empty table.",
            )

        # Basic type inference using the first row of data
        first_row = rows[0]
        col_types = self._infer_types(columns, first_row)
        
        datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
        numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
        categorical_cols = [c for c, t in col_types.items() if t == "categorical"]

        q_lower = question.lower()

        # --- Rule 3: Time-series (Line) ---
        # Detect time intent from question or presence of datetime columns
        time_keywords = {"trend", "over time", "history", "monthly", "yearly", "daily"}
        has_time_intent = any(kw in q_lower for kw in time_keywords)
        
        if datetime_cols and (has_time_intent or numeric_cols):
            return self._build_recommendation(
                request_id,
                t_start,
                chart="line",
                confidence=0.95 if has_time_intent else 0.85,
                reason="Time-series detected. A line chart is best for showing trends over time.",
                x_axis=datetime_cols[0],
                y_axis=numeric_cols[0] if numeric_cols else None,
            )

        # --- Rule 4: Percentage / Distribution (Pie) ---
        pie_keywords = {"percentage", "share", "proportion", "breakdown", "pie"}
        has_pie_intent = any(kw in q_lower for kw in pie_keywords)
        
        # A pie chart works best with one categorical and one numeric, with a small number of categories.
        if has_pie_intent and len(categorical_cols) >= 1 and len(numeric_cols) >= 1 and row_count <= 20:
            return self._build_recommendation(
                request_id,
                t_start,
                chart="pie",
                confidence=0.9,
                reason="Proportional distribution requested. A pie chart shows parts of a whole.",
                x_axis=categorical_cols[0],
                y_axis=numeric_cols[0],
            )

        # --- Rule 5: Single numeric distribution (Histogram) ---
        hist_keywords = {"distribution", "histogram", "spread", "frequency"}
        has_hist_intent = any(kw in q_lower for kw in hist_keywords)

        if has_hist_intent and len(numeric_cols) == 1 and not categorical_cols:
            return self._build_recommendation(
                request_id,
                t_start,
                chart="histogram",
                confidence=0.95,
                reason="Distribution of a single variable detected.",
                x_axis=numeric_cols[0],
            )

        # --- Rule 6: Two numeric columns (Scatter) ---
        scatter_keywords = {"correlation", "relationship", "versus", "vs", "scatter"}
        has_scatter_intent = any(kw in q_lower for kw in scatter_keywords)

        if len(numeric_cols) >= 2 and (has_scatter_intent or len(columns) == 2):
            return self._build_recommendation(
                request_id,
                t_start,
                chart="scatter",
                confidence=0.9 if has_scatter_intent else 0.75,
                reason="Relationship between two numeric values detected.",
                x_axis=numeric_cols[0],
                y_axis=numeric_cols[1],
            )

        # --- Rule 7: Category vs Number (Bar) ---
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            return self._build_recommendation(
                request_id,
                t_start,
                chart="bar",
                confidence=0.85,
                reason="Comparing numerical values across categories is best done with a bar chart.",
                x_axis=categorical_cols[0],
                y_axis=numeric_cols[0],
            )

        # --- Fallback: Unknown / Default (Table) ---
        return self._build_recommendation(
            request_id,
            t_start,
            chart="table",
            confidence=0.5,
            reason="No specific pattern matched; a table is the safest fallback.",
        )

    def _infer_types(self, columns: list[str], row: list[Any]) -> dict[str, str]:
        """Infer high-level semantic types based on cell values and column names."""
        types = {}
        for col_name, val in zip(columns, row):
            col_lower = col_name.lower()
            
            # Explicit date/time objects
            if isinstance(val, (datetime, date)):
                types[col_name] = "datetime"
            # Booleans
            elif isinstance(val, bool):
                types[col_name] = "categorical"
            # Numbers
            elif isinstance(val, (int, float)):
                # If it's a number but looks like an ID or Year, treat as categorical or datetime
                if col_lower in {"year", "yr"}:
                    types[col_name] = "datetime"
                elif col_lower == "id" or col_lower.endswith("_id"):
                    types[col_name] = "categorical"
                else:
                    types[col_name] = "numeric"
            # Strings
            elif isinstance(val, str):
                # Check for ISO8601-ish strings (YYYY-MM-DD)
                if re.match(r"^\d{4}-\d{2}-\d{2}", val):
                    types[col_name] = "datetime"
                else:
                    # Also fallback on column name for time
                    time_names = {"date", "month", "day", "time", "created_at", "updated_at"}
                    if any(name in col_lower for name in time_names):
                        types[col_name] = "datetime"
                    else:
                        types[col_name] = "categorical"
            else:
                types[col_name] = "categorical"
        
        return types

    def _build_recommendation(
        self,
        request_id: str,
        t_start: float,
        chart: str,
        confidence: float,
        reason: str,
        x_axis: str | None = None,
        y_axis: str | None = None,
    ) -> VisualizationRecommendation:
        
        elapsed_ms = (time.perf_counter() - t_start) * 1_000
        
        logger.info(
            "[%s] Recommendation: chart=%s | conf=%.2f | elapsed=%.1f ms",
            request_id,
            chart,
            confidence,
            elapsed_ms,
        )

        return VisualizationRecommendation(
            chart=chart,
            confidence=confidence,
            reason=reason,
            x_axis=x_axis,
            y_axis=y_axis,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
chart_recommender_service = ChartRecommenderService()
