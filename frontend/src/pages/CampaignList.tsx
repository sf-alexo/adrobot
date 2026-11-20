import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Campaign } from '../api/client'

export function CampaignList() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .listCampaigns()
      .then(setCampaigns)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="muted">Loading campaigns…</p>
  if (error) return <p className="error">{error}</p>

  if (campaigns.length === 0) {
    return (
      <div className="empty">
        <p>No campaigns yet.</p>
        <Link className="button" to="/create">
          Create campaign
        </Link>
      </div>
    )
  }

  return (
    <div className="stack">
      <div className="row between">
        <h2>Campaigns</h2>
        <Link className="button" to="/create">
          Create campaign
        </Link>
      </div>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Geo</th>
            <th>Keitaro ID</th>
            <th>Alias</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{c.geo}</td>
              <td>{c.keitaro_campaign_id}</td>
              <td>
                <code>{c.alias}</code>
              </td>
              <td>
                <Link to={`/campaigns/${c.id}`}>Edit streams</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
