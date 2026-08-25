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
