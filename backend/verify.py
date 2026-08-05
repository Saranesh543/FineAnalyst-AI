import asyncio
import sys
import os

from app.services.analytics_orchestrator import analytics_orchestrator

async def main():
    test_cases = [
        ("Show Total Revenue", "kpi"),
        ("Show Monthly Revenue", "line"),
        ("Revenue Trend", "area"),
        ("Revenue Share by Category", "donut"),
        ("Revenue by Category", "bar"),
        ("Top 5 Customers by Revenue", "horizontal_bar"),
        ("Revenue vs Profit", "scatter"),
        ("Sales by Country", "map"),
        ("Show All Orders", "data_grid"),
    ]

    print("Running Regression Tests...")
    all_passed = True
    for query, expected_chart in test_cases:
        try:
            res = await analytics_orchestrator.analyze(query)
            chart = res.visualization.chart if res.visualization else "None"
            if chart == expected_chart:
                print(f"✅ PASS: {query} -> {chart}")
            else:
                print(f"❌ FAIL: {query} -> Expected {expected_chart}, Got {chart}")
                all_passed = False
        except Exception as e:
            print(f"❌ ERROR: {query} -> Exception: {e}")
            all_passed = False

    if all_passed:
        print("\nAll regression tests passed successfully!")
    else:
        print("\nSome regression tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
