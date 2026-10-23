import type { RouteObject } from 'react-router-dom';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { PortfolioPage } from '@/features/portfolio/PortfolioPage';
import { replayRoute } from '@/features/graph/routes';
import { CaseLayout } from './CaseLayout';
import { NotFound } from './NotFound';

export function createAppRoutes(): RouteObject[] {
  return [
    { path: '/', element: <PortfolioPage /> },
    { path: '/ui', element: <DashboardPage /> },
    { path: '/case/:caseId', element: <CaseLayout /> },
    ...replayRoute(),
    { path: '*', element: <NotFound /> },
  ];
}
