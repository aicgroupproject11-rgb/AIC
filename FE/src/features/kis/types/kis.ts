export interface KISSearchRequest {
  query: string
  collection_ids?: string[]
  top_k?: number
}

export interface KISCandidate {
  rank: number
  keyframe_id: string
  collection_id: string
  video_id: string
  frame_number: number
  frame_id: number
  timestamp_ms: number
  image_path: string
  video_path: string
  image_url: string
  video_url: string
  score: number
  domains?: string[]
  routed_domains?: string[]
  matched_objects?: string[]
  score_components?: {
    clip: number
    object_bow: number
    domain: number
  }
}

export interface KISSearchResponse {
  query: string
  parsed_keys: string[]
  filters: {
    collection_ids: string[]
  }
  count: number
  results: KISCandidate[]
}

export interface KISUploadedVideo {
  original_name: string
  stored_name: string
  size: number
  url: string
}

export interface KISVideoUploadResponse {
  count: number
  videos: KISUploadedVideo[]
}
