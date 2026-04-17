const DEFAULT_API_BASE_URL = 'http://localhost:8000';

function normalizeBaseUrl(baseUrl: string): string {
	return baseUrl.replace(/\/$/, '');
}

function normalizePath(path: string): string {
	return path.startsWith('/') ? path : `/${path}`;
}

function normalizeWebSocketBaseUrl(baseUrl: string): string {
	const normalized = normalizeBaseUrl(baseUrl);

	if (normalized.startsWith('http://')) {
		return normalized.replace(/^http:\/\//, 'ws://');
	}

	if (normalized.startsWith('https://')) {
		return normalized.replace(/^https:\/\//, 'wss://');
	}

	return normalized;
}

export const API_BASE_URL = normalizeBaseUrl(
	process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL
);

export const WS_BASE_URL = normalizeWebSocketBaseUrl(
	process.env.NEXT_PUBLIC_WS_BASE_URL ?? API_BASE_URL.replace(/^http/, 'ws')
);

export function getApiUrl(path: string): string {
	return `${API_BASE_URL}${normalizePath(path)}`;
}

export function getWebSocketUrl(path: string): string {
	return `${WS_BASE_URL}${normalizePath(path)}`;
}