import { apiClient } from "./client";

export function listRecords<T>(resource: string): Promise<T[]> {
  return apiClient(`/records/${resource}`);
}

export function createRecord<T>(
  resource: string,
  payload: Record<string, unknown>
): Promise<T> {
  return apiClient(`/records/${resource}`, {
    method: "POST",
    body: JSON.stringify({ payload }),
  });
}

export function updateRecord<T>(
  resource: string,
  id: string,
  payload: Record<string, unknown>
): Promise<T> {
  return apiClient(`/records/${resource}/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify({ payload }),
  });
}

export function deleteRecord(resource: string, id: string): Promise<void> {
  return apiClient(`/records/${resource}/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
