import { apiRequest } from "../../../lib/api/client";

import type {
    KISSearchRequest,
    KISSearchResponse,
} from "../types/kis";

export async function searchKIS(
    request: KISSearchRequest,
): Promise<KISSearchResponse> {
    return apiRequest<KISSearchResponse>("/kis/search/", {
        method: "POST",
        body: JSON.stringify(request),
    });
}
