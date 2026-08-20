import { useState } from "react";

import { useKISSearch } from "../features/kis/hooks/useKISSearch";

export function KISSearchPage() {
    const [query, setQuery] = useState("");
    const { data, loading, error, search } = useKISSearch();

    async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        if (!query.trim()) {
            return;
        }

        await search({
            query: query.trim(),
            top_k: 20,
        });
    }

    return (
        <main>
            <h1>KIS Search</h1>

            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Nhập nội dung cần tìm..."
                />

                <button type="submit" disabled={loading}>
                    {loading ? "Searching..." : "Search"}
                </button>
            </form>

            {error && <p>{error}</p>}

            {data && (
                <section>
                    <p>
                        Found {data.count} results for "{data.query}"
                    </p>

                    {data.results.map((item) => (
                        <div key={`${item.video_id}-${item.frame_id}`}>
                            <strong>#{item.rank}</strong>
                            <span> Video: {item.video_id}</span>
                            <span> Frame: {item.frame_id}</span>
                            <span> Score: {item.score}</span>
                        </div>
                    ))}
                </section>
            )}
        </main>
    );
}