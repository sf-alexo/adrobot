import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type MetaItem } from '../api/client'

type FormState = {
  name: string
  geo: string
  offer_id: string
  domain_id: string
  group_id: string
  traffic_source_id: string
}

const emptyForm: FormState = {
  name: '',
  geo: '',
  offer_id: '',
  domain_id: '',
  group_id: '',
  traffic_source_id: '',
}

export function CreateCampaign() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(emptyForm)
  const [domains, setDomains] = useState<MetaItem[]>([])
  const [groups, setGroups] = useState<MetaItem[]>([])
  const [sources, setSources] = useState<MetaItem[]>([])
  const [offers, setOffers] = useState<MetaItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [metaError, setMetaError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    Promise.all([api.domains(), api.groups(), api.trafficSources(), api.offers()])
      .then(([d, g, s, o]) => {
        setDomains(d)
        setGroups(g)
        setSources(s)
        setOffers(o)
      })
      .catch((err: Error) => setMetaError(err.message))
  }, [])

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const campaign = await api.createCampaign({
        name: form.name.trim(),
        geo: form.geo.trim().toUpperCase(),
        offer_id: Number(form.offer_id),
        domain_id: Number(form.domain_id),
        group_id: Number(form.group_id),
        traffic_source_id: Number(form.traffic_source_id),
      })
      navigate(`/campaigns/${campaign.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create campaign')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="stack narrow">
      <h2>Create campaign</h2>
      <p className="muted">
        Creates a Keitaro campaign with a geo→Google stream and a default offer stream.
      </p>
      {metaError && (
        <p className="error">
          Failed to load Keitaro meta lists. Check <code>KEITARO_BASE_URL</code> /{' '}
          <code>KEITARO_API_KEY</code>. {metaError}
        </p>
      )}
      <form className="form" onSubmit={onSubmit}>
        <label>
          Campaign name
          <input
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="DE Facebook Test"
          />
        </label>
        <label>
          Country geo code
          <input
            required
            maxLength={8}
            value={form.geo}
            onChange={(e) => update('geo', e.target.value)}
            placeholder="DE"
          />
        </label>
        <label>
          Domain
          <select
            required
            value={form.domain_id}
            onChange={(e) => update('domain_id', e.target.value)}
          >
            <option value="">Select domain</option>
            {domains.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Group
          <select
            required
            value={form.group_id}
            onChange={(e) => update('group_id', e.target.value)}
          >
            <option value="">Select group</option>
            {groups.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Traffic source
          <select
            required
            value={form.traffic_source_id}
            onChange={(e) => update('traffic_source_id', e.target.value)}
          >
            <option value="">Select source</option>
            {sources.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Offer ID
          <input
            required
            type="number"
            min={1}
            list="offer-catalog"
            value={form.offer_id}
            onChange={(e) => update('offer_id', e.target.value)}
            placeholder="Keitaro offer id"
          />
          <datalist id="offer-catalog">
            {offers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </datalist>
        </label>
        {error && <p className="error">{error}</p>}
        <button className="button" type="submit" disabled={submitting || !!metaError}>
          {submitting ? 'Creating…' : 'Create campaign'}
        </button>
      </form>
    </div>
  )
}
