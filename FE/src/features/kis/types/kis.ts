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
  timestamp_ms: number
  image_path: string
  video_path: string
  score: number
}

export interface KISSearchResponse {
  query: string
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
