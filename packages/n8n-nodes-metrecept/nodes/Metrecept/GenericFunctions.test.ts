import { generateKeyPairSync, sign as cryptoSign } from 'crypto';
import { verifyReceipt } from './GenericFunctions';

/**
 * Builds a real, correctly-signed compact JWS the same way the Metrecept
 * gateway does (see docs/RECEIPTS.md / open-repo/demo/verify_receipt.py),
 * using a throwaway keypair generated for this test only — never the
 * gateway's real signing key.
 */
function makeReceipt(payload: Record<string, unknown>) {
	const { publicKey, privateKey } = generateKeyPairSync('ed25519');
	const jwk = publicKey.export({ format: 'jwk' }) as { kty: string; crv: string; x: string };

	// Same RFC 7638 thumbprint construction as GenericFunctions.ts's
	// jwkThumbprint — recomputed here rather than imported, so the test
	// exercises verifyReceipt's own key-resolution path end to end instead
	// of assuming its internals.
	const canonical = JSON.stringify({ crv: jwk.crv, kty: jwk.kty, x: jwk.x });
	const kid = require('crypto').createHash('sha256').update(canonical, 'ascii').digest().toString('base64url');

	const header = { alg: 'EdDSA', kid };
	const headerB64 = Buffer.from(JSON.stringify(header)).toString('base64url');
	const payloadB64 = Buffer.from(JSON.stringify(payload)).toString('base64url');
	const signingInput = Buffer.from(`${headerB64}.${payloadB64}`, 'ascii');
	const signature = cryptoSign(null, signingInput, privateKey).toString('base64url');

	return {
		jws: `${headerB64}.${payloadB64}.${signature}`,
		jwk,
		kid,
	};
}

function mockJwksDirectory(jwk: unknown) {
	global.fetch = jest.fn(async () => ({
		ok: true,
		json: async () => ({ keys: [jwk] }),
	})) as unknown as typeof fetch;
}

describe('verifyReceipt', () => {
	afterEach(() => {
		jest.restoreAllMocks();
	});

	it('verifies a correctly-signed receipt and returns the decoded payload', async () => {
		const payload = { kind: 'cache_hit', model: 'mock', pipe_usd: 0.0001 };
		const { jws, jwk, kid } = makeReceipt(payload);
		mockJwksDirectory(jwk);

		const result = await verifyReceipt(jws, 'https://fake.example');

		expect(result.verified).toBe(true);
		expect(result.kid).toBe(kid);
		expect(result.payload).toEqual(payload);
	});

	it('rejects a receipt whose payload was tampered with after signing', async () => {
		const { jws, jwk } = makeReceipt({ kind: 'cache_hit', pipe_usd: 0.0001 });
		mockJwksDirectory(jwk);

		const [headerB64, , signatureB64] = jws.split('.');
		const tamperedPayload = Buffer.from(JSON.stringify({ kind: 'cache_hit', pipe_usd: 99 })).toString(
			'base64url',
		);
		const tampered = `${headerB64}.${tamperedPayload}.${signatureB64}`;

		const result = await verifyReceipt(tampered, 'https://fake.example');

		expect(result.verified).toBe(false);
	});

	it('fails closed when no key in the directory matches the kid', async () => {
		const { jws } = makeReceipt({ kind: 'cache_hit' });
		// A directory with an unrelated key — the receipt's kid won't match.
		const { publicKey: otherKey } = generateKeyPairSync('ed25519');
		mockJwksDirectory(otherKey.export({ format: 'jwk' }));

		const result = await verifyReceipt(jws, 'https://fake.example');

		expect(result.verified).toBe(false);
		expect(result.payload).toBeNull();
	});

	it('rejects structurally invalid input without throwing', async () => {
		const result = await verifyReceipt('not-a-jws', 'https://fake.example');
		expect(result).toEqual({ verified: false, kid: '', payload: null });
	});

	it('rejects a header with an unexpected alg', async () => {
		const header = Buffer.from(JSON.stringify({ alg: 'HS256', kid: 'x' })).toString('base64url');
		const payload = Buffer.from(JSON.stringify({ kind: 'cache_hit' })).toString('base64url');
		const result = await verifyReceipt(`${header}.${payload}.sig`, 'https://fake.example');
		expect(result.verified).toBe(false);
		expect(result.payload).toBeNull();
	});
});
