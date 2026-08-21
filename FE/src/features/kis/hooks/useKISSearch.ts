import { useState } from "react";

import { searchKIS } from "../services/kisApi";

import type {KISSearchRequest,KISSearchResponse,} from "../types/kis";

export function useKISSearch() {
    const [data, setData] = useState<KISSearchResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function search(request: KISSearchRequest) {
        setLoading(true);
        setError(null);

        try {
            const response = await searchKIS(request);
            setData(response);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "KIS search failed",
            );
        } finally {
            setLoading(false);
        }
    }

    return {
        data,
        loading,
        error,
        search,
    };
}  