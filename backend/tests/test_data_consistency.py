import pytest
import asyncio
from unittest.mock import MagicMock
from app.services.business_insight_service import _build_insight_prompt
from app.services.chart_intelligence_service import ChartIntelligenceService
from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation, VisualizationMetadata

def test_business_insight_duplicate_aggregation_prevention():
    """
    Test that business_insight_service does NOT sum non-additive columns 
    like 'Total_Revenue' or 'Profit_Margin'.
    """
    # 3 rows of data
    rows = [
        ["Jan", 100, 1000, 0.1],
        ["Feb", 200, 1200, 0.2],
        ["Mar", 300, 1500, 0.15]
    ]
    columns = ["Month", "Revenue", "Total_Revenue", "Profit_Margin"]
    
    execution = SQLExecutionResponse(
        columns=columns,
        rows=rows,
        row_count=3,
        execution_time_ms=10.0
    )
    
    vis = VisualizationRecommendation(
        chart="line",
        confidence=0.9,
        reason="Test",
        metadata=VisualizationMetadata(chart_type="line", title="Test")
    )
    
    prompt = _build_insight_prompt("Test question", execution, [vis])
    
    assert "SUM=600.00" in prompt, "Additive column 'Revenue' should be summed"
    assert "Do NOT SUM this metric as it is non-additive" in prompt, "Non-additive metrics must contain the warning"
    
    # Assert Total_Revenue was NOT summed to 3700
    assert "SUM=3,700.00" not in prompt, "Total_Revenue should not be summed"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
