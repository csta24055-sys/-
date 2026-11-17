// 全レイアウトで共有するルーティング。レイアウトはこの要素を同じ位置に描くだけで、ページの中身・状態には関与しない。
import { Route, Routes } from 'react-router-dom'
import Dashboard from '../pages/Dashboard'
import Library from '../pages/Library'
import DataAnalysis from '../pages/DataAnalysis'
import Simulator from '../pages/Simulator'
import KnowledgeGraph from '../pages/KnowledgeGraph'
import ResearchPlan from '../pages/ResearchPlan'
import Report from '../pages/Report'
import Learning from '../pages/Learning'
import Cloud from '../pages/Cloud'
import Settings from '../pages/Settings'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/library" element={<Library />} />
      <Route path="/library/:id" element={<Library />} />
      <Route path="/data" element={<DataAnalysis />} />
      <Route path="/simulator" element={<Simulator />} />
      <Route path="/graph" element={<KnowledgeGraph />} />
      <Route path="/plan" element={<ResearchPlan />} />
      <Route path="/report" element={<Report />} />
      <Route path="/learn" element={<Learning />} />
      <Route path="/cloud" element={<Cloud />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<Dashboard />} />
    </Routes>
  )
}
