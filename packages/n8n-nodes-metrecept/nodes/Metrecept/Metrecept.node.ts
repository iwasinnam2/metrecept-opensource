import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeConnectionTypes, NodeOperationError } from 'n8n-workflow';

import { metreceptChatCompletion, metreceptGetUsage, verifyReceipt } from './GenericFunctions';

export class Metrecept implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Metrecept',
		name: 'metrecept',
		icon: 'file:metrecept.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["resource"] + ": " + $parameter["operation"]}}',
		description:
			'Cached, receipted LLM calls and standalone receipt verification via Metrecept (metrecept.co.uk)',
		defaults: {
			name: 'Metrecept',
		},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		usableAsTool: true,
		credentials: [
			{
				name: 'metreceptApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Resource',
				name: 'resource',
				type: 'options',
				noDataExpression: true,
				options: [
					{ name: 'Chat', value: 'chat' },
					{ name: 'Receipt', value: 'receipt' },
					{ name: 'Usage', value: 'usage' },
				],
				default: 'chat',
			},
			// --- Chat resource ---
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['chat'] } },
				options: [
					{
						name: 'Send Message',
						value: 'sendMessage',
						action: 'Send a chat message',
						description:
							'POST an OpenAI-shaped chat/completions request through the Metrecept gateway; identical repeated calls return from cache with a signed, verified receipt attached',
					},
				],
				default: 'sendMessage',
			},
			{
				displayName: 'Model',
				name: 'model',
				type: 'string',
				default: 'mock',
				required: true,
				displayOptions: { show: { resource: ['chat'] } },
				description:
					'Model name. "mock" needs no upstream provider key and proves cache/receipt behavior end to end; a real model (e.g. gpt-4o-mini) requires BYOK per metrecept.co.uk/docs.',
			},
			{
				displayName: 'Prompt',
				name: 'prompt',
				type: 'string',
				typeOptions: { rows: 4 },
				default: '',
				required: true,
				displayOptions: { show: { resource: ['chat'] } },
				description: 'Sent as a single user-role chat message',
			},
			// --- Receipt resource ---
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['receipt'] } },
				options: [
					{
						name: 'Verify',
						value: 'verify',
						action: 'Verify a receipt',
						description:
							'Verify an Ed25519 JWS receipt (e.g. captured from an X-Ohm-Receipt header by an HTTP Request node elsewhere in the workflow) against the gateway\'s public JWKS',
					},
				],
				default: 'verify',
			},
			{
				displayName: 'Receipt (JWS)',
				name: 'receipt',
				type: 'string',
				default: '',
				required: true,
				displayOptions: { show: { resource: ['receipt'] } },
				description: 'The X-Ohm-Receipt / X-Metrecept-Receipt header value to verify',
			},
			// --- Usage resource ---
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: { show: { resource: ['usage'] } },
				options: [
					{
						name: 'Get',
						value: 'get',
						action: 'Get current usage',
						description:
							'Live cache hits/misses, tokens, and pipe spend for this API key — the same numbers billed, not an estimate',
					},
				],
				default: 'get',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		const credentials = await this.getCredentials('metreceptApi');
		const baseUrl = ((credentials.baseUrl as string) || 'https://api.metrecept.co.uk').trim();
		const apiKey = credentials.apiKey as string;

		const resource = this.getNodeParameter('resource', 0) as string;

		for (let i = 0; i < items.length; i++) {
			try {
				if (resource === 'chat') {
					const model = this.getNodeParameter('model', i) as string;
					const prompt = this.getNodeParameter('prompt', i) as string;
					const result = await metreceptChatCompletion(baseUrl, apiKey, {
						model,
						messages: [{ role: 'user', content: prompt }],
					});
					returnData.push({
						json: {
							content: result.content,
							model: result.model,
							cache: result.cache,
							billedUsd: result.billedUsd,
							receiptVerified: result.receipt?.verified ?? null,
							receiptKid: result.receipt?.kid ?? null,
							receiptPayload: result.receipt?.payload ?? null,
							receiptRaw: result.receiptRaw,
						},
						pairedItem: { item: i },
					});
				} else if (resource === 'receipt') {
					const receipt = this.getNodeParameter('receipt', i) as string;
					const result = await verifyReceipt(receipt, baseUrl);
					returnData.push({
						json: {
							verified: result.verified,
							kid: result.kid,
							payload: result.payload,
						},
						pairedItem: { item: i },
					});
				} else if (resource === 'usage') {
					const usage = await metreceptGetUsage(baseUrl, apiKey);
					returnData.push({ json: usage, pairedItem: { item: i } });
				} else {
					throw new NodeOperationError(this.getNode(), `Unknown resource: ${resource}`);
				}
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: { error: (error as Error).message },
						pairedItem: { item: i },
					});
					continue;
				}
				throw error;
			}
		}

		return [returnData];
	}
}
