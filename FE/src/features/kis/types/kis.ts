export interface KISSearchRequest {query: string;top_k?: number;}

export interface KISCandidate {rank: number;video_id: string;frame_id: number;score: number;}

export interface KISSearchResponse {query: string;count: number;results: KISCandidate[];}