"use client";

import { useState } from "react";

import { GameCard, type Gem } from "../components/GameCard";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [genre, setGenre] = useState("indie");
  const [maxPrice, setMaxPrice] = useState("");
  const [gems, setGems] = useState<Gem[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const params = new URLSearchParams({ genre });
    if (maxPrice) params.set("max_price_cents", String(Number(maxPrice) * 100));
    const response = await fetch(`${API_BASE}/games/gems?${params.toString()}`);
    const data: Gem[] = await response.json();
    setGems(data);
    setLoading(false);
  }

  return (
    <main>
      <h1>스팀 저평가 게임 발굴</h1>
      <form onSubmit={handleSearch}>
        <label>
          장르
          <select value={genre} onChange={(e) => setGenre(e.target.value)}>
            <option value="indie">인디</option>
            <option value="roguelike">로그라이크</option>
            <option value="simulation">시뮬레이션</option>
          </select>
        </label>
        <label>
          최대 예산 (USD)
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "검색 중..." : "검색"}
        </button>
      </form>
      <section>
        {gems.map((gem) => (
          <GameCard key={gem.app_id} gem={gem} />
        ))}
      </section>
    </main>
  );
}
