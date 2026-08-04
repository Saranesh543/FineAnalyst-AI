import { render, screen } from '@testing-library/react';
import { EvidenceArtifactRenderer } from '../components/evidence/EvidenceArtifactRenderer';
import { EvidenceArtifact } from '@/lib/types/chat';

jest.mock('../components/evidence/charts/PieChartWidget', () => ({
  PieChartWidget: () => <div data-testid="pie-widget" />
}));
jest.mock('../components/evidence/charts/BarChartWidget', () => ({
  BarChartWidget: ({ isHorizontal }: { isHorizontal?: boolean }) => <div data-testid={isHorizontal ? "horizontal-bar-widget" : "bar-widget"} />
}));
jest.mock('../components/evidence/charts/AreaChartWidget', () => ({
  AreaChartWidget: () => <div data-testid="area-widget" />
}));
jest.mock('../components/evidence/charts/KpiCard', () => ({
  KpiCard: () => <div data-testid="kpi-widget" />
}));

const mockArtifact = (chartType: string): EvidenceArtifact => ({
  id: '1',
  kind: 'chart',
  chartType: chartType as any,
  data: [{ x: 'a', y: 1 }],
  sql: 'SELECT * FROM test',
  rowCountTotal: 1,
  rowSample: [{ x: 'a', y: 1 }],
  title: 'Test',
  metadata: {
    chart_type: chartType,
    title: 'Test',
    x_axis: 'x',
    y_axis: 'y'
  }
});

describe('EvidenceArtifactRenderer Dispatcher', () => {
  it('renders PieChartWidget for chart_type="pie"', () => {
    render(<EvidenceArtifactRenderer evidence={[mockArtifact('pie')]} />);
    expect(screen.getByTestId('pie-widget')).toBeInTheDocument();
  });

  it('renders HorizontalBarWidget for chart_type="horizontal-bar"', () => {
    render(<EvidenceArtifactRenderer evidence={[mockArtifact('horizontal-bar')]} />);
    expect(screen.getByTestId('horizontal-bar-widget')).toBeInTheDocument();
  });

  it('renders AreaChartWidget for chart_type="area"', () => {
    render(<EvidenceArtifactRenderer evidence={[mockArtifact('area')]} />);
    expect(screen.getByTestId('area-widget')).toBeInTheDocument();
  });

  it('renders KPIWidget for chart_type="kpi"', () => {
    render(<EvidenceArtifactRenderer evidence={[mockArtifact('kpi')]} />);
    expect(screen.getByTestId('kpi-widget')).toBeInTheDocument();
  });
});
