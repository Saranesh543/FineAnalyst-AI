"""
Chart Intelligence Service

Rule-based engine to select the best visualization based on intent and SQL result shape.
"""

import logging
import re
from typing import Any
from dataclasses import dataclass

from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation, VisualizationMetadata

logger = logging.getLogger(__name__)

@dataclass
class VisualizationDecision:
    chart_type: str
    reason: str
    confidence: float


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
        # Strip any conversation history context that might have leaked
        match = re.search(r'New question:\s*"(.*?)"', question, re.IGNORECASE)
        if match:
            question = match.group(1).strip()
            
        q_lower = question.lower()
        
        # Template-based deterministic titles
        if "top" in q_lower and "revenue" in q_lower and "customer" in q_lower:
            return "Top 10 Customers by Revenue"
        elif "share" in q_lower and "category" in q_lower:
            return "Revenue Share by Category"
        elif "monthly revenue" in q_lower:
            return "Monthly Revenue"
        elif "revenue trend" in q_lower:
            return "Revenue Trend"
        elif "sales by country" in q_lower:
            return "Sales by Country"
        elif "revenue vs profit" in q_lower or ("revenue" in q_lower and "profit" in q_lower and "vs" in q_lower):
            return "Revenue vs Profit"
        elif "total revenue" in q_lower:
            return "Total Revenue"
        elif "category" in q_lower and "revenue" in q_lower and "top" in q_lower:
            return "Top Categories by Revenue"
        elif "category" in q_lower and "revenue" in q_lower:
            return "Revenue by Category"
            
        # Fallback to simple parsing
        q = re.sub(r'^(show me|tell me|give me|what is|what are|list|show)\s+(the\s+)?', '', question, flags=re.IGNORECASE)
        q = re.sub(r'(?i)^(Previous Context.*?:\s*|Conversation History.*?:\s*|User:\s*|Assistant:\s*|Question:\s*|New Question:\s*)', '', q).strip()
        
        small_words = {'by', 'and', 'or', 'in', 'of', 'for', 'to', 'with', 'on', 'at', 'from', 'vs'}
        words = q.split()
        capitalized = []
        for i, w in enumerate(words):
            if i == 0 or w.lower() not in small_words:
                capitalized.append(w.capitalize())
            else:
                capitalized.append(w.lower())
        title = " ".join(capitalized)
        return title if title else "Data Analysis"

    def _detect_intent(self, question: str) -> str:
        q_lower = question.lower()
        
        # Heatmap
        if "matrix" in q_lower or "heatmap" in q_lower:
            return "heatmap"
            
        # Scatter
        if "vs" in q_lower or "versus" in q_lower or "correlation" in q_lower or "correlate" in q_lower:
            return "scatter"
            
        # Area
        if "growth over time" in q_lower or "growth" in q_lower:
            return "area"
            
        # Line
        if any(kw in q_lower for kw in ["revenue over time", "monthly", "quarterly", "yearly", "trend", "history", "over time"]):
            return "line"
            
        # Bar (Ranking needs to override pie for "Top 5 categories")
        if any(kw in q_lower for kw in [
            "top", "highest", "lowest", "best", "worst", "largest", "smallest", 
            "ranking", "rank", "leaderboard", "compare", "comparison"
        ]):
            return "bar"
            
        # Pie / Donut
        if any(kw in q_lower for kw in [
            "revenue by category", "revenue by product category", "revenue by country", "revenue by region", 
            "market share", "category distribution", "percentage contribution",
            "share", "percent", "proportion", "distribution"
        ]):
            return "pie"
            
        # Catch generic "by category" if revenue is mentioned
        if "revenue" in q_lower and any(kw in q_lower for kw in ["category", "country", "region"]):
            return "pie"
            
        return "general"

    def select_chart(self, question: str, execution_result: SQLExecutionResponse) -> VisualizationRecommendation:
        if not execution_result.columns or execution_result.row_count == 0:
            return VisualizationRecommendation(
                chart="data_grid",
                confidence=1.0,
                reason="Empty dataset.",
                metadata=VisualizationMetadata(chart_type="data_grid", title="No Data", interactive=False)
            )

        row_count = execution_result.row_count
        columns = execution_result.columns
        rows = execution_result.rows
        first_row = rows[0]
        
        col_types = self._infer_types(columns, first_row)
        
        datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
        numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
        categorical_cols = [c for c, t in col_types.items() if t == "categorical"]

        intent = self._detect_intent(question)
        
        decision = VisualizationDecision(chart_type="data_grid", reason="Default fallback", confidence=0.5)
        x_axis = None
        y_axis = None
        
        # Determine X and Y axes defaults
        if categorical_cols:
            x_axis = categorical_cols[0]
        elif datetime_cols:
            x_axis = datetime_cols[0]
        elif numeric_cols:
            x_axis = numeric_cols[0]
            
        if numeric_cols:
            y_axis = numeric_cols[0]
            if x_axis == numeric_cols[0] and len(numeric_cols) > 1:
                y_axis = numeric_cols[1]
                
        # 1. KPI
        if row_count == 1 and len(numeric_cols) == 1 and len(categorical_cols) == 0 and intent not in ("line", "area"):
            decision = VisualizationDecision("kpi", "Single numeric value detected.", 1.0)
            
        # 2. Data Grid
        elif row_count > 1000:
            decision = VisualizationDecision("data_grid", "Dataset > 1000 rows is best presented as a data grid.", 1.0)
            
        # 3. Explicit Intent Matching (Based on Rules)
        elif intent == "heatmap":
            decision = VisualizationDecision("heatmap", "Matrix comparison intent detected.", 1.0)
            
        elif intent == "scatter":
            decision = VisualizationDecision("scatter", "Correlation intent detected.", 1.0)
            
        elif intent == "area":
            decision = VisualizationDecision("area", "Growth over time intent detected.", 1.0)
            
        elif intent == "line":
            decision = VisualizationDecision("line", "Time series / Trend intent detected.", 1.0)
            if datetime_cols: x_axis = datetime_cols[0]
            
        elif intent == "pie":
            chart = "donut" if "share" in question.lower() else "pie"
            decision = VisualizationDecision(chart, "Distribution intent detected.", 1.0)
            
        elif intent == "bar":
            max_label_length = 0
            if categorical_cols:
                x_axis_candidate = categorical_cols[0]
                if isinstance(rows[0], dict):
                    max_label_length = max([len(str(r.get(x_axis_candidate, ""))) for r in rows[:20]])
                else:
                    x_idx = columns.index(x_axis_candidate)
                    max_label_length = max([len(str(r[x_idx])) for r in rows[:20]])
            
            if max_label_length > 15:
                decision = VisualizationDecision("horizontal_bar", "Ranking intent with long labels.", 1.0)
            else:
                decision = VisualizationDecision("bar", "Ranking / Comparison intent detected.", 1.0)

        # 4. Fallbacks based on data shape if no explicit intent matched
        elif any(c.lower() in ["country", "city", "state", "region", "lat", "lon"] for c in categorical_cols):
            decision = VisualizationDecision("map", "Geographic columns detected.", 0.95)
            
        elif len(numeric_cols) == 2 and not categorical_cols and not datetime_cols:
            decision = VisualizationDecision("scatter", "Two numeric distributions detected.", 0.9)
            
        elif datetime_cols and numeric_cols:
            decision = VisualizationDecision("line", "Date columns detected.", 0.95)
            x_axis = datetime_cols[0]
            
        elif len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            max_label_length = 0
            if isinstance(rows[0], dict):
                max_label_length = max([len(str(r.get(x_axis, ""))) for r in rows[:20]])
            else:
                x_idx = columns.index(x_axis)
                max_label_length = max([len(str(r[x_idx])) for r in rows[:20]])
                
            if max_label_length > 15:
                decision = VisualizationDecision("horizontal_bar", "Long category labels require horizontal bar layout.", 0.95)
            else:
                decision = VisualizationDecision("bar", "Category vs Numeric data best shown as a bar chart.", 0.9)

        format_type = "compact"
        if y_axis:
            y_lower = y_axis.lower()
            if any(w in y_lower for w in ["revenue", "price", "cost", "sales", "profit", "amount", "total"]):
                format_type = "currency"
            elif any(w in y_lower for w in ["rate", "percent", "ratio", "margin"]):
                format_type = "percentage"
            
        title = self._generate_title(question)
            
        metadata = VisualizationMetadata(
            chart_type=decision.chart_type,
            title=title,
            subtitle="Based on recent query execution",
            x_axis=x_axis,
            y_axis=y_axis,
            x_label=x_axis.replace("_", " ").title() if x_axis else None,
            y_label=y_axis.replace("_", " ").title() if y_axis else None,
            number_format=format_type,
            interactive=True
        )
        
        logger.info("[CHART_METADATA_PIPELINE] Intent: %s | Selected Chart: %s | Reason: %s | Title: %s", intent, decision.chart_type, decision.reason, title)

        return VisualizationRecommendation(
            chart=decision.chart_type,
            confidence=decision.confidence,
            reason=decision.reason,
            x_axis=x_axis,
            y_axis=y_axis,
            metadata=metadata
        )

chart_intelligence_service = ChartIntelligenceService()
