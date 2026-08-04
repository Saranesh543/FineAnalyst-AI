"""
Chart Intelligence Service

Rule-based engine to select the best visualization based on intent and SQL result shape.
"""

import logging
import re
from typing import Any

from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation, VisualizationMetadata

logger = logging.getLogger(__name__)


class ChartIntelligenceService:
    def __init__(self) -> None:
        pass

    def _infer_types(self, columns: list[str], row: dict[str, Any] | list[Any]) -> dict[str, str]:
        col_types = {}
        for i, col in enumerate(columns):
            val = row[col] if isinstance(row, dict) else row[i]
            if val is None:
                col_types[col] = "categorical"
                continue

            if isinstance(val, (int, float)):
                col_types[col] = "numeric"
            elif isinstance(val, str):
                val_lower = val.lower()
                # Basic date heuristic
                if len(val) >= 4 and any(sep in val for sep in ["-", "/"]):
                    col_types[col] = "datetime"
                else:
                    col_types[col] = "categorical"
            else:
                col_types[col] = "categorical"
        return col_types

    def _generate_title(self, question: str) -> str:
        q = re.sub(r'^(show me|tell me|give me|what is|what are|list|show)\s+(the\s+)?', '', question, flags=re.IGNORECASE)
        small_words = {'by', 'and', 'or', 'in', 'of', 'for', 'to', 'with', 'on', 'at', 'from', 'vs'}
        words = q.split()
        capitalized = []
        for i, w in enumerate(words):
            if i == 0 or w.lower() not in small_words:
                # Handle cases like "10" not being capitalized, which is fine
                capitalized.append(w.capitalize())
            else:
                capitalized.append(w.lower())
        title = " ".join(capitalized)
        return title if title else "Data Analysis"

    def select_chart(self, question: str, execution_result: SQLExecutionResponse) -> VisualizationRecommendation:
        if not execution_result.columns or execution_result.row_count == 0:
            return VisualizationRecommendation(
                chart="table",
                confidence=1.0,
                reason="Empty dataset.",
                metadata=VisualizationMetadata(chart_type="table", title="No Data", interactive=False)
            )

        row_count = execution_result.row_count
        columns = execution_result.columns
        rows = execution_result.rows
        first_row = rows[0]
        
        col_types = self._infer_types(columns, first_row)
        
        datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
        numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
        categorical_cols = [c for c, t in col_types.items() if t == "categorical"]

        chart_type = "table"
        confidence = 0.5
        reason = "Default fallback"
        x_axis = None
        y_axis = None
        
        q_lower = question.lower()
        
        has_pie_intent = any(kw in q_lower for kw in ["share", "percent", "proportion", "distribution"])
        has_trend_intent = any(kw in q_lower for kw in ["trend", "history", "growth", "over time"])
        has_top_intent = any(kw in q_lower for kw in ["top", "ranking", "worst", "bottom"])
        has_geo_intent = any(kw in q_lower for kw in ["country", "city", "state", "region"])
        
        # Determine X and Y axes defaults
        if categorical_cols:
            x_axis = categorical_cols[0]
        elif datetime_cols:
            x_axis = datetime_cols[0]
        elif numeric_cols:
            x_axis = numeric_cols[0]
            
        if numeric_cols:
            y_axis = numeric_cols[0]
            # If x_axis is the first numeric, use the second for y if it exists
            if x_axis == numeric_cols[0] and len(numeric_cols) > 1:
                y_axis = numeric_cols[1]
                
        # Rule evaluation (order matters for precedence)
        
        if row_count > 1000:
            chart_type = "data_grid"
            confidence = 1.0
            reason = "Dataset > 1000 rows is best presented as a data grid."
            
        elif has_geo_intent or any(c.lower() in ["country", "city", "state", "region", "lat", "lon"] for c in categorical_cols):
            chart_type = "map"
            confidence = 0.95
            reason = "Geographic intent or columns detected."
            
        elif row_count == 1 and len(numeric_cols) == 1 and len(categorical_cols) == 0:
            chart_type = "kpi"
            confidence = 1.0
            reason = "Single numeric value detected."
            
        elif len(numeric_cols) == 2 and not categorical_cols and not datetime_cols:
            chart_type = "scatter"
            confidence = 0.9
            reason = "Two numeric distributions detected (vs comparison)."
            
        elif has_pie_intent and categorical_cols and numeric_cols:
            chart_type = "pie" if "share" not in q_lower else "donut"
            confidence = 0.95
            reason = "User explicitly asked for share/distribution."
            
        elif (has_trend_intent or datetime_cols) and numeric_cols:
            if has_trend_intent and "share" not in q_lower:
                chart_type = "area"
            else:
                chart_type = "line" if len(numeric_cols) == 1 else "multi-line"
            confidence = 0.95
            reason = "Trend intent or date columns detected."
            if datetime_cols: x_axis = datetime_cols[0]
            
        elif has_top_intent and categorical_cols and numeric_cols:
            chart_type = "horizontal-bar"
            confidence = 0.95
            reason = "User asked for ranking/top N."
            
        elif len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            max_label_length = 0
            if isinstance(rows[0], dict):
                max_label_length = max([len(str(r.get(x_axis, ""))) for r in rows[:20]])
            else:
                x_idx = columns.index(x_axis)
                max_label_length = max([len(str(r[x_idx])) for r in rows[:20]])
                
            if max_label_length > 15:
                chart_type = "horizontal-bar"
                confidence = 0.95
                reason = "Long category labels require horizontal bar layout."
            elif row_count <= 8:
                chart_type = "pie"
                confidence = 0.9
                reason = "Small number of categories (<=8) fits well in a pie chart."
            else:
                chart_type = "bar"
                confidence = 0.9
                reason = "Category vs Numeric data best shown as a bar chart."

        format_type = "compact"
        if y_axis:
            y_lower = y_axis.lower()
            if any(w in y_lower for w in ["revenue", "price", "cost", "sales", "profit", "amount", "total"]):
                format_type = "currency"
            elif any(w in y_lower for w in ["rate", "percent", "ratio", "margin"]):
                format_type = "percentage"
            
        title = self._generate_title(question)
            
        metadata = VisualizationMetadata(
            chart_type=chart_type,
            title=title,
            subtitle="Based on recent query execution",
            x_axis=x_axis,
            y_axis=y_axis,
            x_label=x_axis.replace("_", " ").title() if x_axis else None,
            y_label=y_axis.replace("_", " ").title() if y_axis else None,
            number_format=format_type,
            interactive=True
        )
        
        logger.info("[CHART_METADATA_PIPELINE] Selected Chart: %s | Reason: %s | Title: %s", chart_type, reason, title)

        return VisualizationRecommendation(
            chart=chart_type,
            confidence=confidence,
            reason=reason,
            x_axis=x_axis,
            y_axis=y_axis,
            metadata=metadata
        )

chart_intelligence_service = ChartIntelligenceService()
