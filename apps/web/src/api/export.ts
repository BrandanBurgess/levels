import { apiClient } from "./client";

export async function downloadExport(format: "json" | "csv") {
  const { data, error } = await apiClient.GET("/export", {
    params: { query: { format } },
  });
  if (data == null || error) throw new Error("Export request failed");
  const contents = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  const blob = new Blob([contents], {
    type: format === "csv" ? "text/csv;charset=utf-8" : "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `levels-export-${new Date().toISOString().slice(0, 10)}.${format}`;
  link.click();
  URL.revokeObjectURL(url);
}
