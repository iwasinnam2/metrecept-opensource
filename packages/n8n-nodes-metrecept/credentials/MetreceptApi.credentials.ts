import type { ICredentialTestRequest, ICredentialType, INodeProperties } from 'n8n-workflow';

/**
 * Metrecept API credential — an API key plus the gateway base URL.
 *
 * Note: n8n's own "OpenAI Chat Model" / "Anthropic Chat Model" nodes already
 * have an Advanced "Base URL" field that can be pointed at Metrecept's
 * gateway directly (Metrecept is OpenAI-compatible) — this credential does
 * not replace that, it exists for the Metrecept node in this package
 * (Chat + Receipt-verify), which is discoverable by name and returns a
 * parsed, pre-verified receipt inline instead of a bare header string.
 */
export class MetreceptApi implements ICredentialType {
	name = 'metreceptApi';

	displayName = 'Metrecept API';

	documentationUrl = 'https://metrecept.co.uk/docs';

	properties: INodeProperties[] = [
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: { password: true },
			default: '',
			required: true,
			description:
				'Metrecept API key. A free, no-card membership key is available at metrecept.co.uk/billing/intermediate.',
		},
		{
			displayName: 'Base URL',
			name: 'baseUrl',
			type: 'string',
			default: 'https://api.metrecept.co.uk',
			description:
				'Metrecept gateway base URL. Only change this for a self-hosted or staging deployment.',
		},
	];

	// Lets n8n's credential UI show a real "Connection tested successfully"
	// (or a real error) the moment the API key is saved, before it's ever
	// wired into a workflow node — GET /v1/usage is authenticated but has no
	// side effects, so it's a safe connectivity + auth check.
	test: ICredentialTestRequest = {
		request: {
			baseURL: '={{$credentials.baseUrl}}',
			url: '/v1/usage',
			method: 'GET',
			headers: {
				Authorization: '=Bearer {{$credentials.apiKey}}',
			},
		},
	};
}
