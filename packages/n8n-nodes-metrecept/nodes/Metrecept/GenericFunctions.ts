import { createHash, createPublicKey, verify as cryptoVerify } from 'crypto';
import type { IDataObject } from 'n8n-workflow';

/**
 * Ed25519 JWS receipt verification — a TypeScript port of
 * open-repo/demo/verify_receipt.py, kept in lockstep by hand (same
 * convention used across every verifier in this repo: each copy stands
 * alone, no shared import, so a reader of just this file can audit it
 * without pulling in the rest of the package). Uses only Node's built-in
 * `crypto` module — no external dependency, on purpose.
 */

const DIRECTORY_PATH = '/.well-known/http-message-signatures-directory';

export interface JwkEd25519 {
	kty: string;
	crv: string;
	x: string;
}

export interface VerifyReceiptResult {
	verified: boolean;
	kid: string;
	payload: Record<string, unknown> | null;
}

function b64uDecode(text: string): Buffer {
	return Buffer.from(text, 'base64url');
}

/**
 * RFC 7638 JWK thumbprint for an OKP/Ed25519 key. The canonical member
 * order for this key type is alphabetical — crv, kty, x — which is also
 * the exact order the object literal below is constructed in, so
 * JSON.stringify's insertion-order output already matches the canonical
 * form without a separate sort step.
 */
function jwkThumbprint(jwk: JwkEd25519): string {
	const canonical = JSON.stringify({ crv: jwk.crv, kty: jwk.kty, x: jwk.x });
	return createHash('sha256').update(canonical, 'ascii').digest().toString('base64url');
}

/**
 * Verify a Metrecept receipt (X-Ohm-Receipt / X-Metrecept-Receipt header
 * value — a compact Ed25519 JWS) against the gateway's public JWKS.
 * Never throws; failures resolve to { verified: false, ... }.
 */
export async function verifyReceipt(receipt: string, baseUrl: string): Promise<VerifyReceiptResult> {
	const parts = receipt.trim().split('.');
	if (parts.length !== 3) {
		return { verified: false, kid: '', payload: null };
	}

	let header: { alg?: string; kid?: string };
	try {
		header = JSON.parse(b64uDecode(parts[0]).toString('utf8'));
	} catch {
		return { verified: false, kid: '', payload: null };
	}
	if (header.alg !== 'EdDSA') {
		return { verified: false, kid: header.kid ?? '', payload: null };
	}
	const kid = header.kid ?? '';

	let verified = false;
	try {
		const directoryUrl = baseUrl.replace(/\/$/, '') + DIRECTORY_PATH;
		const res = await fetch(directoryUrl);
		const directory = (await res.json()) as { keys?: JwkEd25519[] };
		const jwk = (directory.keys ?? []).find(
			(k) => k.kty === 'OKP' && k.crv === 'Ed25519' && jwkThumbprint(k) === kid,
		);
		if (!jwk) {
			return { verified: false, kid, payload: null };
		}

		const publicKey = createPublicKey({ key: jwk as unknown as Record<string, string>, format: 'jwk' });
		const signingInput = Buffer.from(`${parts[0]}.${parts[1]}`, 'ascii');
		// Ed25519 is a "pure" EdDSA scheme — Node expects a null algorithm,
		// the hash is internal to the signature scheme itself.
		verified = cryptoVerify(null, signingInput, publicKey, b64uDecode(parts[2]));
	} catch {
		return { verified: false, kid, payload: null };
	}

	let payload: Record<string, unknown>;
	try {
		payload = JSON.parse(b64uDecode(parts[1]).toString('utf8'));
	} catch {
		return { verified: false, kid, payload: null };
	}
	return { verified, kid, payload };
}

/**
 * GET /v1/usage — a live snapshot of cache hits/misses, tokens, and pipe
 * spend for the authenticated tenant. Returned as-is (the gateway's own
 * field names) rather than remapped, so the node's output always matches
 * whatever metrecept.co.uk/docs documents at the time it's called.
 */
export async function metreceptGetUsage(baseUrl: string, apiKey: string): Promise<IDataObject> {
	const url = baseUrl.replace(/\/$/, '') + '/v1/usage';
	const res = await fetch(url, {
		headers: { Authorization: `Bearer ${apiKey}` },
	});
	const json = (await res.json()) as IDataObject;
	if (!res.ok) {
		throw new Error(`Metrecept gateway returned HTTP ${res.status}: ${JSON.stringify(json)}`);
	}
	return json;
}

export interface MetreceptChatResult {
	content: string;
	model: string;
	cache: string | null;
	billedUsd: string | null;
	receiptRaw: string | null;
	receipt: VerifyReceiptResult | null;
}

/**
 * POST an OpenAI-shaped chat/completions request to the Metrecept gateway
 * and pull the cache + receipt evidence straight off the HTTP response —
 * the same headers any generic HTTP client already sees
 * (X-AT-Cache, X-AT-Billed-USD, X-Ohm-Receipt / X-Metrecept-Receipt).
 * If a receipt header is present, verify it inline so the node's output
 * carries a parsed, checked result rather than a bare string.
 */
export async function metreceptChatCompletion(
	baseUrl: string,
	apiKey: string,
	body: Record<string, unknown>,
): Promise<MetreceptChatResult> {
	const url = baseUrl.replace(/\/$/, '') + '/v1/chat/completions';
	const res = await fetch(url, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${apiKey}`,
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(body),
	});

	const json = (await res.json()) as {
		choices?: Array<{ message?: { content?: string } }>;
		model?: string;
	};
	if (!res.ok) {
		throw new Error(`Metrecept gateway returned HTTP ${res.status}: ${JSON.stringify(json)}`);
	}

	const receiptRaw = res.headers.get('x-ohm-receipt') ?? res.headers.get('x-metrecept-receipt');
	const receipt = receiptRaw ? await verifyReceipt(receiptRaw, baseUrl) : null;

	return {
		content: json.choices?.[0]?.message?.content ?? '',
		model: json.model ?? (body.model as string) ?? '',
		cache: res.headers.get('x-at-cache'),
		billedUsd: res.headers.get('x-at-billed-usd'),
		receiptRaw,
		receipt,
	};
}
