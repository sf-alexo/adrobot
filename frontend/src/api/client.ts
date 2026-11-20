export type MetaItem = {
  id: number
  name: string
}

export type StreamOffer = {
  id: number
  offer_id: number
  offer_name?: string | null
  share: number
  pinned: boolean
  status: 'active' | 'removed' | string
}

export type Stream = {
  id: number
  keitaro_stream_id: number
  name: string
  stream_type: string
  has_offers: boolean
  is_dirty: boolean
  offers: StreamOffer[]
}

export type Campaign = {
  id: number
  name: string
  geo: string
  keitaro_campaign_id: number
  offer_stream_id: number
  google_stream_id: number
  domain_id: number
  group_id: number
  traffic_source_id: number
  alias: string
  created_at: string
  streams: Stream[]
}

export type CampaignCreatePayload = {
  name: string
  geo: string
  offer_id: number
  domain_id: number
  group_id: number
  traffic_source_id: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail ?? JSON.stringify(body)
    } catch {
      // ignore
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const api = {
  listCampaigns: () => request<Campaign[]>('/api/campaigns'),
  getCampaign: (id: number) => request<Campaign>(`/api/campaigns/${id}`),
  createCampaign: (payload: CampaignCreatePayload) =>
    request<Campaign>('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  fetchStreams: (campaignId: number) =>
    request<Campaign>(`/api/campaigns/${campaignId}/fetch-streams`, { method: 'POST' }),
  addOffer: (campaignId: number, streamId: number, offerId: number) =>
    request<Campaign>(`/api/campaigns/${campaignId}/streams/${streamId}/offers`, {
      method: 'POST',
      body: JSON.stringify({ offer_id: offerId }),
    }),
  removeOffer: (campaignId: number, streamId: number, offerId: number) =>
    request<Campaign>(
      `/api/campaigns/${campaignId}/streams/${streamId}/offers/${offerId}/remove`,
      { method: 'POST' },
    ),
  bringBackOffer: (campaignId: number, streamId: number, offerId: number) =>
    request<Campaign>(
      `/api/campaigns/${campaignId}/streams/${streamId}/offers/${offerId}/bring-back`,
      { method: 'POST' },
    ),
  pinOffer: (
    campaignId: number,
    streamId: number,
    offerId: number,
    pinned: boolean,
    share?: number,
  ) =>
    request<Campaign>(
      `/api/campaigns/${campaignId}/streams/${streamId}/offers/${offerId}/pin`,
      {
        method: 'POST',
        body: JSON.stringify({ pinned, share }),
      },
    ),
  pushStream: (campaignId: number, streamId: number) =>
    request<Campaign>(`/api/campaigns/${campaignId}/streams/${streamId}/push`, {
      method: 'POST',
    }),
  cancelStream: (campaignId: number, streamId: number) =>
    request<Campaign>(`/api/campaigns/${campaignId}/streams/${streamId}/cancel`, {
      method: 'POST',
    }),
  domains: () => request<MetaItem[]>('/api/meta/domains'),
  groups: () => request<MetaItem[]>('/api/meta/groups'),
  trafficSources: () => request<MetaItem[]>('/api/meta/traffic-sources'),
  offers: () => request<MetaItem[]>('/api/meta/offers'),
  getOffer: (offerId: number) => request<MetaItem>(`/api/meta/offers/${offerId}`),
}
