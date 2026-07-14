import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./schema";

export type AccessTokenProvider = () => Promise<string | undefined> | string | undefined;

export interface LevelsClientOptions {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
  getAccessToken?: AccessTokenProvider;
}

export type LevelsClient = Client<paths>;

export function createLevelsClient(options: LevelsClientOptions): LevelsClient {
  const clientOptions: Parameters<typeof createClient<paths>>[0] = {
    baseUrl: options.baseUrl.replace(/\/$/, ""),
  };

  if (options.fetch) {
    clientOptions.fetch = options.fetch;
  }

  const client = createClient<paths>(clientOptions);

  if (options.getAccessToken) {
    client.use({
      async onRequest({ request }) {
        const accessToken = await options.getAccessToken?.();
        if (accessToken) {
          request.headers.set("Authorization", `Bearer ${accessToken}`);
        }
        return request;
      },
    });
  }

  return client;
}

export type { components, operations, paths } from "./schema";
