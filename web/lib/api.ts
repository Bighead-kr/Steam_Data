import type { Facet, Filters, Gem } from "./types";
import { buildApiQuery } from "./filterQuery";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** A failed request, already phrased for the reader.
 *
 * The old page had no failure path at all: it awaited fetch().json() with no
 * try/catch and no response.ok check, so a cold-started API (the free Render
 * plan sleeps, and the first request can take the better part of a minute or
 * simply fail) left the button stuck on "검색 중..." forever with an
 * unhandled rejection in the console and nothing on screen. */
export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { signal });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError("서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.");
  }
  if (!response.ok) {
    throw new ApiError(`서버가 ${response.status} 오류를 반환했습니다.`);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("서버 응답을 읽지 못했습니다.");
  }
}

function expectArray<T>(value: unknown): T[] {
  // A 200 carrying something other than a list (a proxy's error page, say)
  // used to reach the render path and crash on .slice/.map.
  if (!Array.isArray(value)) throw new ApiError("서버 응답 형식이 올바르지 않습니다.");
  return value as T[];
}

export async function fetchGems(
  filters: Filters,
  limit: number,
  signal?: AbortSignal
): Promise<Gem[]> {
  const query = buildApiQuery(filters, limit);
  return expectArray<Gem>(await getJson(`/games/gems?${query.toString()}`, signal));
}

export async function fetchGenres(signal?: AbortSignal): Promise<Facet[]> {
  return expectArray<Facet>(await getJson("/genres", signal));
}

export async function fetchTags(genre: string, signal?: AbortSignal): Promise<Facet[]> {
  const query = new URLSearchParams(genre ? { genre } : {});
  return expectArray<Facet>(await getJson(`/tags?${query.toString()}`, signal));
}
