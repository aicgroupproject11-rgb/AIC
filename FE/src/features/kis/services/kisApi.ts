import { apiRequest } from "../../../lib/api/client";

import type {
    KISSearchRequest,
    KISSearchResponse,
    KISVideoUploadResponse,
} from "../types/kis";

export async function searchKIS(
    request: KISSearchRequest,
): Promise<KISSearchResponse> {
    return apiRequest<KISSearchResponse>("/kis/search/", {
        method: "POST",
        body: JSON.stringify(request),
    });
}

export async function uploadKISVideos(
    videos: File[],
): Promise<KISVideoUploadResponse> {
    const formData = new FormData();
    videos.forEach((video) => formData.append("videos", video));

    return apiRequest<KISVideoUploadResponse>("/kis/videos/upload/", {
        method: "POST",
        body: formData,
    });
}
