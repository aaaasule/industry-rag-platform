import { api } from '@/lib/http';
import type { components } from '@/types/openapi.gen';

export type ModelConnection = components['schemas']['ModelConnectionOut'];
export type ModelConnectionCreate = components['schemas']['ModelConnectionCreate'];
export type ModelConnectionUpdate = components['schemas']['ModelConnectionUpdate'];
export type ConnectionTestResult = components['schemas']['ConnectionTestResult'];
export type RoutesOut = components['schemas']['RoutesOut'];
export type Purpose = 'chat' | 'embedding' | 'rerank' | 'title';

export const CONNECTION_LIST_KEY = ['model-connections'] as const;
export const ROUTES_KEY = ['model-connections', 'routes'] as const;

export function listConnections(): Promise<ModelConnection[]> {
  return api.get('/model-connections');
}

export function createConnection(body: ModelConnectionCreate): Promise<ModelConnection> {
  return api.post('/model-connections', body);
}

export function updateConnection(
  id: string,
  body: ModelConnectionUpdate,
): Promise<ModelConnection> {
  return api.patch(`/model-connections/${id}`, body);
}

export function updateCredential(id: string, apiKey: string): Promise<ModelConnection> {
  return api.put(`/model-connections/${id}/credential`, { api_key: apiKey });
}

export function testConnection(id: string): Promise<ConnectionTestResult> {
  return api.post(`/model-connections/${id}/test`);
}

export function deleteConnection(id: string): Promise<void> {
  return api.delete(`/model-connections/${id}`);
}

export function listRoutes(): Promise<RoutesOut> {
  return api.get('/model-connections/routes');
}
