/**
 * OpsPulse Live API Client.
 *
 * Connects the Next.js frontend to the FastAPI Python analytical backend.
 * Never stores or transmits database credentials to the browser.
 */

const RAW_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export interface ApiResponse<T> {
  data: T;
  timestamp: string;
  source: "production" | "mock";
}

function resolveBaseUrl(): string {
  if (RAW_API_BASE_URL.startsWith("http://") || RAW_API_BASE_URL.startsWith("https://")) {
    return RAW_API_BASE_URL;
  }
  // If relative path (e.g., "/api"), resolve against current window origin in browser
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${window.location.origin}${RAW_API_BASE_URL.startsWith("/") ? "" : "/"}${RAW_API_BASE_URL}`;
  }
  return `http://127.0.0.1:8000${RAW_API_BASE_URL.startsWith("/") ? "" : "/"}${RAW_API_BASE_URL}`;
}

async function fetchApi<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
  const baseUrl = resolveBaseUrl();
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  
  let url: URL;
  try {
    url = new URL(`${baseUrl}${cleanEndpoint}`);
  } catch {
    // Fallback URL resolution
    url = new URL(`http://127.0.0.1:8000/api${cleanEndpoint}`);
  }

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.append(key, String(value));
      }
    });
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout

  try {
    const res = await fetch(url.toString(), {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      cache: "no-store",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorDetail = "";
      try {
        const errorJson = await res.json();
        errorDetail = errorJson.message || errorJson.error || JSON.stringify(errorJson);
      } catch {
        errorDetail = await res.text();
      }
      throw new Error(`HTTP ${res.status}: ${errorDetail || res.statusText}`);
    }

    return await res.json();
  } catch (err: any) {
    clearTimeout(timeoutId);

    if (err.name === "AbortError") {
      throw new Error(`API request timed out (15s) while contacting ${cleanEndpoint}`);
    }

    if (err.message && err.message.startsWith("HTTP ")) {
      throw err;
    }

    // Classify genuine network / connection refused errors
    const target = url ? url.origin : baseUrl;
    throw new Error(
      `Cannot reach backend API at ${target}. Ensure FastAPI is running on port 8000. (${err.message})`
    );
  }
}

export const opspulseApi = {
  getOverview: async (params?: { year?: number; quarter?: number } | number) => {
    if (typeof params === "number") {
      return fetchApi<any>("/overview", { year: params });
    }
    return fetchApi<any>("/overview", {
      year: params?.year || 2025,
      quarter: params?.quarter,
    });
  },

  getSales: async (params?: { year?: number; quarter?: number } | number) => {
    if (typeof params === "number") {
      return fetchApi<any>("/sales", { year: params });
    }
    return fetchApi<any>("/sales", {
      year: params?.year || 2025,
      quarter: params?.quarter,
    });
  },

  getSalesTransactions: async (params: {
    page?: number;
    pageSize?: number;
    search?: string;
    channel?: string;
    branch?: string;
    year?: number;
    quarter?: number;
  }) => {
    return fetchApi<any>("/sales/transactions", {
      page: params.page || 1,
      page_size: params.pageSize || 20,
      search: params.search,
      channel: params.channel,
      branch: params.branch,
      year: params.year || 2025,
      quarter: params.quarter,
    });
  },

  getInventory: async () => {
    return fetchApi<any>("/inventory");
  },

  getInventoryItems: async (params: {
    page?: number;
    pageSize?: number;
    search?: string;
    status?: string;
    warehouse?: string;
  }) => {
    return fetchApi<any>("/inventory/items", {
      page: params.page || 1,
      page_size: params.pageSize || 20,
      search: params.search,
      status: params.status,
      warehouse: params.warehouse,
    });
  },

  getProcurement: async () => {
    return fetchApi<any>("/procurement");
  },

  getProcurementOrders: async (params: {
    page?: number;
    pageSize?: number;
    search?: string;
    status?: string;
  }) => {
    return fetchApi<any>("/procurement/orders", {
      page: params.page || 1,
      page_size: params.pageSize || 20,
      search: params.search,
      status: params.status,
    });
  },

  getSuppliers: async () => {
    return fetchApi<any>("/suppliers");
  },

  getExpenses: async (params?: { year?: number; quarter?: number } | number) => {
    if (typeof params === "number") {
      return fetchApi<any>("/expenses", { year: params });
    }
    return fetchApi<any>("/expenses", {
      year: params?.year || 2025,
      quarter: params?.quarter,
    });
  },

  getMonitoring: async () => {
    return fetchApi<any>("/monitoring");
  },

  getDataQuality: async () => {
    return fetchApi<any>("/data-quality");
  },

  getHealth: async () => {
    return fetchApi<any>("/health");
  },
};
