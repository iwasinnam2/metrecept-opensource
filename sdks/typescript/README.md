# @at-utility/sdk (TypeScript)

Thin helper so the official OpenAI SDK becomes a one-line `baseURL` swap for **Metrecept**.

Package name remains `@at-utility/sdk` until first npm publish; then rename to `@ohm/sdk`.

## Install

```bash
cd sdks/typescript
npm install
```

## Publish to npm

Only after `https://api.withohm.dev/v1` answers chat — see [docs/PLATFORM.md](../../docs/PLATFORM.md).

```bash
cd sdks/typescript
npm publish --access public
```

## Usage

```ts
import OpenAI from "openai";
import { openaiArgs, LOCAL_BASE_URL, DEFAULT_BASE_URL } from "@at-utility/sdk";

const client = new OpenAI(openaiArgs("sk-at-dev", LOCAL_BASE_URL));
// After cutover: openaiArgs("sk-at-...", DEFAULT_BASE_URL)
```

Framework recipes: `examples/templates/`.

## Put the receipt where the work lands

```ts
import OpenAI from "openai";
import { openaiArgs, receiptTrailer } from "@at-utility/sdk";

const client = new OpenAI(openaiArgs("sk-at-..."));
const { data, response } = await client.chat.completions
  .create({ model: "mock", messages: [{ role: "user", content: "summarise the ticket" }] })
  .withResponse();
const prBody = `${data.choices[0].message.content}\n\n${receiptTrailer(response.headers)}`;
```

`receiptTrailer` returns `Receipt: https://metrecept.co.uk/verify#<jws>` or `""`
when the response carried no receipt. It also accepts the body of
`GET /v1/sessions/{id}`. The reader checks the Ed25519 signature in their
browser against the public JWKS, no account. The JWS rides the URL fragment.

A streamed MISS cannot carry its receipt in a header (the headers leave
before the provider has finished), so it rides as the last `data:` chunk
before `[DONE]`, with empty `choices`. Read it out of the stream you kept:

```ts
import { receiptFromSse, verifyUrl } from "@at-utility/sdk";

const jws = receiptFromSse(captured); // "" when the stream did not finish
const link = jws ? verifyUrl(jws) : "";
```
