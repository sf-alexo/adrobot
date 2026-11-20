import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Campaign, type MetaItem, type Stream, type StreamOffer } from '../api/client'

export function EditCampaign() {
  const { id } = useParams()
  const campaignId = Number(id)
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [catalog, setCatalog] = useState<MetaItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function reload() {
    const [c, offers] = await Promise.all([api.getCampaign(campaignId), api.offers()])
    setCampaign(c)
    setCatalog(offers)
  }

  useEffect(() => {
    if (!Number.isFinite(campaignId)) {
      setError('Invalid campaign id')
      return
    }
    reload().catch((err: Error) => setError(err.message))
  }, [campaignId])

  async function run(action: () => Promise<Campaign>) {
    setBusy(true)
    setError(null)
    try {
      setCampaign(await action())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  if (error && !campaign) {
    return (
      <div className="stack">
        <p className="error">{error}</p>
        <Link to="/">Back to list</Link>
      </div>
    )
  }

  if (!campaign) return <p className="muted">Loading campaign…</p>

  return (
    <div className="stack">
      <div className="row between">
        <div>
          <h2>{campaign.name}</h2>
          <p className="muted">
            Keitaro #{campaign.keitaro_campaign_id} · geo {campaign.geo} · alias{' '}
            <code>{campaign.alias}</code>
          </p>
        </div>
        <div className="row">
          <button
            type="button"
            className="button"
            disabled={busy}
            onClick={() => run(() => api.fetchStreams(campaign.id))}
          >
            Fetch streams
          </button>
          <Link to="/">All campaigns</Link>
        </div>
      </div>

      {campaign.streams.length === 0 && (
        <p className="muted">
          No local streams yet. Click <strong>Fetch streams</strong> to pull from Keitaro.
        </p>
      )}

      {campaign.streams.map((stream) => (
        <StreamCard
          key={stream.id}
          campaignId={campaign.id}
          stream={stream}
          catalog={catalog}
          busy={busy}
          onChange={(next) => setCampaign(next)}
          onError={setError}
          setBusy={setBusy}
        />
      ))}

      {error && <p className="error">{error}</p>}
    </div>
  )
}

function StreamCard({
  campaignId,
  stream,
  catalog,
  busy,
  onChange,
  onError,
  setBusy,
}: {
  campaignId: number
  stream: Stream
  catalog: MetaItem[]
  busy: boolean
  onChange: (c: Campaign) => void
  onError: (msg: string | null) => void
  setBusy: (v: boolean) => void
}) {
  const [offerId, setOfferId] = useState('')
  const [lookup, setLookup] = useState<MetaItem | null>(null)
  const [shareDrafts, setShareDrafts] = useState<Record<number, string>>({})

  useEffect(() => {
    const next: Record<number, string> = {}
    for (const offer of stream.offers) {
      next[offer.offer_id] = String(offer.share)
    }
    setShareDrafts(next)
  }, [stream])

  async function run(action: () => Promise<Campaign>) {
    setBusy(true)
    onError(null)
    try {
      onChange(await action())
      setOfferId('')
      setLookup(null)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  async function onLookup() {
    if (!offerId) return
    setBusy(true)
    onError(null)
    try {
      setLookup(await api.getOffer(Number(offerId)))
    } catch (err) {
      setLookup(null)
      onError(err instanceof Error ? err.message : 'Offer not found')
    } finally {
      setBusy(false)
    }
  }

  function draftShare(offer: StreamOffer): number {
    const raw = shareDrafts[offer.offer_id]
    const parsed = Number(raw)
    if (!Number.isFinite(parsed)) return offer.share
    return Math.max(0, Math.min(100, Math.round(parsed)))
  }

  if (!stream.has_offers) {
    return (
      <section className="panel stream-plain">
        <div className="row between">
          <div>
            <h3>{stream.name}</h3>
            <p className="muted">
              #{stream.keitaro_stream_id} · {stream.stream_type} · no offers
            </p>
          </div>
        </div>
      </section>
    )
  }

  const used = new Set(stream.offers.filter((o) => o.status === 'active').map((o) => o.offer_id))
  const available = catalog.filter((o) => !used.has(o.id))
  const activeTotal = stream.offers
    .filter((o) => o.status === 'active')
    .reduce((sum, o) => sum + o.share, 0)

  return (
    <section className={`panel ${stream.is_dirty ? 'stream-dirty' : ''}`}>
      <div className="row between">
        <div>
          <h3>{stream.name}</h3>
          <p className="muted">
            #{stream.keitaro_stream_id} · {stream.stream_type}
            {stream.is_dirty ? ' · unpublished changes' : ''}
            {' · '}
            <span className={activeTotal === 100 ? 'share' : 'error'}>total {activeTotal}%</span>
          </p>
        </div>
        <div className="row">
          <button
            type="button"
            className="button"
            disabled={busy || !stream.is_dirty || activeTotal !== 100}
            onClick={() => run(() => api.pushStream(campaignId, stream.id))}
          >
            Push to Keitaro
          </button>
          <button
            type="button"
            className="button ghost"
            disabled={busy || !stream.is_dirty}
            onClick={() => run(() => api.cancelStream(campaignId, stream.id))}
          >
            Cancel
          </button>
        </div>
      </div>

      <ul className="offer-list">
        {stream.offers.map((offer) => {
          const removed = offer.status === 'removed'
          return (
            <li key={offer.id} className={removed ? 'offer-removed' : undefined}>
              <div className="offer-main">
                <span>
                  {offer.offer_name ?? `Offer #${offer.offer_id}`}{' '}
                  <span className="muted">#{offer.offer_id}</span>
                </span>
                {!removed ? (
                  <label className="share-edit">
                    <input
                      className="share-input"
                      type="number"
                      min={0}
                      max={100}
                      disabled={busy}
                      value={shareDrafts[offer.offer_id] ?? String(offer.share)}
                      onChange={(e) =>
                        setShareDrafts((prev) => ({
                          ...prev,
                          [offer.offer_id]: e.target.value,
                        }))
                      }
                    />
                    <span className={offer.pinned ? 'share pinned' : 'share'}>
                      %{offer.pinned ? ' pinned' : ''}
                    </span>
                  </label>
                ) : (
                  <span className="share muted">0%</span>
                )}
              </div>
              <div className="row">
                {!removed && (
                  <>
                    <button
                      type="button"
                      className="button ghost"
                      disabled={busy}
                      onClick={() =>
                        run(() =>
                          api.pinOffer(
                            campaignId,
                            stream.id,
                            offer.offer_id,
                            !offer.pinned,
                            offer.pinned ? undefined : draftShare(offer),
                          ),
                        )
                      }
                    >
                      {offer.pinned ? 'Unpin' : 'Pin'}
                    </button>
                    {offer.pinned && draftShare(offer) !== offer.share && (
                      <button
                        type="button"
                        className="button ghost"
                        disabled={busy}
                        onClick={() =>
                          run(() =>
                            api.pinOffer(
                              campaignId,
                              stream.id,
                              offer.offer_id,
                              true,
                              draftShare(offer),
                            ),
                          )
                        }
                      >
                        Apply %
                      </button>
                    )}
                    <button
                      type="button"
                      className="button ghost"
                      disabled={busy}
                      onClick={() =>
                        run(() => api.removeOffer(campaignId, stream.id, offer.offer_id))
                      }
                    >
                      Remove
                    </button>
                  </>
                )}
                {removed && (
                  <button
                    type="button"
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      run(() => api.bringBackOffer(campaignId, stream.id, offer.offer_id))
                    }
                  >
                    Bring back
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      <form
        className="form inline"
        onSubmit={(e: FormEvent) => {
          e.preventDefault()
          if (!offerId) return
          run(() => api.addOffer(campaignId, stream.id, Number(offerId)))
        }}
      >
        {available.length > 0 ? (
          <select value={offerId} onChange={(e) => setOfferId(e.target.value)}>
            <option value="">Select offer</option>
            {available.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} (#{item.id})
              </option>
            ))}
          </select>
        ) : (
          <input
            type="number"
            min={1}
            placeholder="Offer ID"
            value={offerId}
            onChange={(e) => {
              setOfferId(e.target.value)
              setLookup(null)
            }}
          />
        )}
        {available.length === 0 && (
          <button type="button" className="button ghost" disabled={busy || !offerId} onClick={onLookup}>
            Lookup
          </button>
        )}
        <button className="button" type="submit" disabled={busy || !offerId}>
          Add
        </button>
      </form>
      {lookup && (
        <p className="muted">
          Found: {lookup.name} <code>#{lookup.id}</code>
        </p>
      )}
    </section>
  )
}
