import { NavLink, Route, Routes } from 'react-router-dom'
import { CampaignList } from './pages/CampaignList'
import { CreateCampaign } from './pages/CreateCampaign'
import { EditCampaign } from './pages/EditCampaign'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <div className="brand">Adrobot</div>
        <nav>
          <NavLink to="/" end>
            Campaigns
          </NavLink>
          <NavLink to="/create">Create</NavLink>
        </nav>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<CampaignList />} />
          <Route path="/create" element={<CreateCampaign />} />
          <Route path="/campaigns/:id" element={<EditCampaign />} />
        </Routes>
      </main>
    </div>
  )
}
