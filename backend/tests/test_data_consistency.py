import pytest
from app.services.business_insight_service import BusinessInsightService
from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation

@pytest.mark.asyncio
async def test_insight_generator_strict_data_grounding():
    """
    Test that the insight generator strictly adheres to the provided dataset
    and does not hallucinate other entities.
    """
    service = BusinessInsightService()
    
    # Mock an execution response with highly specific fictitious data
    # so we can easily detect if the LLM hallucinates generic tech companies.
    mock_execution = SQLExecutionResponse(
        sql="SELECT company_name, revenue FROM customers ORDER BY revenue DESC LIMIT 2",
        columns=["company_name", "revenue"],
        rows=[
            ["Xylophone Enterprises", 998877],
            ["Zebra Logistics", 112233]
        ],
        row_count=2,
        execution_time_ms=10.0
    )
    
    mock_vis = VisualizationRecommendation(
        chart="Bar Chart",
        reason="Comparing revenue across companies.",
        confidence=0.95
    )
    
    question = "Top 2 companies by revenue"
    
    insight = await service.generate_insight(
        question=question,
        execution_result=mock_execution,
        visualization=mock_vis
    )
    
    summary_lower = insight.summary.lower()
    findings_lower = " ".join(insight.key_findings).lower()
    
    full_text = summary_lower + " " + findings_lower
    
    # Assert that the exact fictitious names appear in the LLM's response
    assert "xylophone enterprises" in full_text, f"Expected 'Xylophone Enterprises' in output, got: {insight.model_dump_json()}"
    assert "zebra logistics" in full_text, f"Expected 'Zebra Logistics' in output, got: {insight.model_dump_json()}"
    assert "998877" in full_text or "998,877" in full_text or "998.88" in full_text or "998k" in full_text or "112233" in full_text, f"Expected numeric values in output, got: {insight.model_dump_json()}"
    
    # Assert that it did NOT hallucinate Apple, Microsoft, Amazon, etc.
    assert "apple" not in full_text, "Hallucinated 'Apple'"
    assert "microsoft" not in full_text, "Hallucinated 'Microsoft'"
    assert "amazon" not in full_text, "Hallucinated 'Amazon'"
