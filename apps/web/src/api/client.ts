import { createLevelsClient } from "@levels/api-client";

import { getAccessToken } from "./tokenStore";

const RETRYABLE_STATUS = new Set([502, 503, 504]);

export interface RetryOptions {
  timeoutMs?: number;
  retries?: number;
  delay?: (attempt: number) => Promise<void>;
}

function requestMethod(input: RequestInfo | URL, init?: RequestInit) {
  return (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
}

async function delay(attempt: number) {
  await new Promise((resolve) => window.setTimeout(resolve, attempt * 750));
}

export function createColdStartFetch(
  fetchImplementation: typeof fetch,
  options: RetryOptions = {},
): typeof fetch {
  const timeoutMs = options.timeoutMs ?? 45_000;
  const retries = options.retries ?? 2;
  const wait = options.delay ?? delay;

  return async (input, init) => {
    const method = requestMethod(input, init);
    const maxAttempts = method === "GET" ? retries + 1 : 1;
    let lastError: unknown;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort("request-timeout"), timeoutMs);
      const originalSignal = init?.signal ?? (input instanceof Request ? input.signal : undefined);
      const abortFromOriginal = () => controller.abort(originalSignal?.reason);
      originalSignal?.addEventListener("abort", abortFromOriginal, { once: true });
      try {
        const response = await fetchImplementation(input, { ...init, signal: controller.signal });
        if (!RETRYABLE_STATUS.has(response.status) || attempt === maxAttempts) {
          return response;
        }
        lastError = new Error(`API returned ${response.status}`);
      } catch (error) {
        lastError = error;
        if (attempt === maxAttempts || originalSignal?.aborted) {
          throw error;
        }
      } finally {
        window.clearTimeout(timeout);
        originalSignal?.removeEventListener("abort", abortFromOriginal);
      }
      await wait(attempt);
    }
    throw lastError instanceof Error ? lastError : new Error("API request failed");
  };
}

export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

export const apiClient = createLevelsClient({
  baseUrl: apiBaseUrl,
  fetch: createColdStartFetch(globalThis.fetch.bind(globalThis)),
  getAccessToken,
});
