<div align="center">

# Free Claude Code

### Use Claude Code CLI & VSCode for free. No Anthropic API key required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python 3.14](https://img.shields.io/badge/python-3.14-3776ab.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=for-the-badge)](https://github.com/astral-sh/uv)
[![Tested with Pytest](https://img.shields.io/badge/testing-Pytest-00c0ff.svg?style=for-the-badge)](https://github.com/Rishurajgautam24/free-claude-code/actions/workflows/tests.yml)
[![Type checking: Ty](https://img.shields.io/badge/type%20checking-ty-ffcc00.svg?style=for-the-badge)](https://pypi.org/project/ty/)
[![Code style: Ruff](https://img.shields.io/badge/code%20formatting-ruff-f5a623.svg?style=for-the-badge)](https://github.com/astral-sh/ruff)
[![Logging: Loguru](https://img.shields.io/badge/logging-loguru-4ecdc4.svg?style=for-the-badge)](https://github.com/Delgan/loguru)

A lightweight proxy that routes Claude Code's Anthropic API calls to **NVIDIA NIM** (40 req/min free), **OpenRouter** (hundreds of models), or **LM Studio** (fully local).

[Features](#features) · [Quick Start](#quick-start) · [How It Works](#how-it-works) · [Discord Bot](#discord-bot) · [Configuration](#configuration)

---

</div>

<div align="center">
  <img src="pic.png" alt="Free Claude Code in action" width="700">
  <p><em>Claude Code running via NVIDIA NIM, completely free</em></p>
</div>

## Features

| Feature                    | Description                                                                                                          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Zero Cost**              | 40 req/min free on NVIDIA NIM. Free models on OpenRouter. Fully local with LM Studio                                 |
| **Drop-in Replacement**    | Set 2 env vars. No modifications to Claude Code CLI or VSCode extension needed                                       |
| **10 Providers**           | NVIDIA NIM, OpenRouter, LM Studio, Ollama, Groq, Gemini, Cerebras, Mistral, DeepSeek, Together + any OpenAI-compatible API |
| **Per-Model Mapping**      | Route Opus / Sonnet / Haiku requests to different models and providers. Mix providers freely per model               |
| **Model Picker**           | Your configured models appear in Claude Code’s `/model` picker; switch backend models mid-session without restarting |
| **Thinking Token Support** | Parses `<think>` tags and `reasoning_content` into native Claude thinking blocks                                     |
| **Robust Tool Calls**      | Native and text-written tool calls become real tool use, even when providers stream ids and names in pieces          |
| **Image Input**            | Pasted screenshots reach vision models; text-only models automatically get the request without images                |
| **Request Optimization**   | 5 categories of trivial API calls intercepted locally, saving quota and latency                                      |
| **Discord Bot**            | Remote autonomous coding with tree-based threading, session persistence, and live progress (Telegram also supported) |
| **Fallback Chains**        | `MODEL_SONNET="a,b,c"`: if a model fails before answering, the next one takes over, seamlessly                       |
| **Smart Rate Limiting**    | Rolling-window throttle, 429 backoff and a concurrency cap, separately per provider                                  |
| **Stream Keepalive**       | SSE pings while a slow model thinks, so Claude Code never drops a quiet stream                                       |
| **Secure by Default**      | Listens on localhost only; optional `PROXY_AUTH_TOKEN`; bots ignore everyone not on the allowlist                    |
| **Subagent Control**       | Task tool interception forces `run_in_background=False`. No runaway subagents                                        |
| **Extensible**             | Clean `BaseProvider` and `MessagingPlatform` ABCs. Add new providers or platforms easily                             |

## Quick Start

### Prerequisites

1. Get an API key (or use LM Studio locally):
   - **NVIDIA NIM**: [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys)
   - **OpenRouter**: [openrouter.ai/keys](https://openrouter.ai/keys)
   - **LM Studio**: No API key needed. Run locally with [LM Studio](https://lmstudio.ai)
2. Install [Claude Code](https://github.com/anthropics/claude-code)
3. Install [uv](https://github.com/astral-sh/uv)
4. Update uv if already installed: `uv self update`

### Clone & Configure

```bash
git clone https://github.com/Rishurajgautam24/free-claude-code.git
cd free-claude-code
cp .env.example .env
```

Choose your provider and edit `.env`:

<details>
<summary><b>NVIDIA NIM</b> (40 req/min free, recommended)</summary>

```dotenv
NVIDIA_NIM_API_KEY="nvapi-your-key-here"

MODEL_OPUS="nvidia_nim/z-ai/glm4.7"
MODEL_SONNET="nvidia_nim/moonshotai/kimi-k2-thinking"
MODEL_HAIKU="nvidia_nim/stepfun-ai/step-3.5-flash"
MODEL="nvidia_nim/z-ai/glm4.7"                     # fallback
```

</details>

<details>
<summary><b>OpenRouter</b> (hundreds of models)</summary>

```dotenv
OPENROUTER_API_KEY="sk-or-your-key-here"

MODEL_OPUS="open_router/deepseek/deepseek-r1-0528:free"
MODEL_SONNET="open_router/openai/gpt-oss-120b:free"
MODEL_HAIKU="open_router/stepfun/step-3.5-flash:free"
MODEL="open_router/stepfun/step-3.5-flash:free"     # fallback
```

</details>

<details>
<summary><b>LM Studio</b> (fully local, no API key)</summary>

```dotenv
MODEL_OPUS="lmstudio/unsloth/MiniMax-M2.5-GGUF"
MODEL_SONNET="lmstudio/unsloth/Qwen3.5-35B-A3B-GGUF"
MODEL_HAIKU="lmstudio/unsloth/GLM-4.7-Flash-GGUF"
MODEL="lmstudio/unsloth/GLM-4.7-Flash-GGUF"         # fallback
```

</details>

<details>
<summary><b>Groq, Gemini, Ollama & any OpenAI-compatible API</b></summary>

Built-in presets only need an API key; use the provider name as the `MODEL` prefix:

```dotenv
GROQ_API_KEY="gsk_..."            # also: CEREBRAS_, GEMINI_, MISTRAL_, DEEPSEEK_, TOGETHER_API_KEY
MODEL="groq/llama-3.3-70b-versatile"
MODEL_HAIKU="gemini/gemini-2.5-flash"   # needs GEMINI_API_KEY
```

Local Ollama needs no key (`OLLAMA_BASE_URL` defaults to `http://localhost:11434/v1`):

```dotenv
MODEL="ollama/qwen3-coder"
```

Anything else that speaks the OpenAI chat API (vLLM, llama.cpp server, a company gateway, ...):

```dotenv
CUSTOM_BASE_URL="https://llm.example.com/v1"
CUSTOM_API_KEY="..."              # optional
MODEL="custom/my-model"
```

</details>

<details>
<summary><b>Mix providers</b> (use multiple providers together)</summary>

Each `MODEL_*` variable can use a different provider. `MODEL` is the default for Claude models without their own setting.

```dotenv
NVIDIA_NIM_API_KEY="nvapi-your-key-here"
OPENROUTER_API_KEY="sk-or-your-key-here"

MODEL_OPUS="nvidia_nim/moonshotai/kimi-k2.5"
MODEL_SONNET="open_router/deepseek/deepseek-r1-0528:free"
MODEL_HAIKU="lmstudio/unsloth/GLM-4.7-Flash-GGUF"
MODEL="nvidia_nim/z-ai/glm4.7"                      # default
```

</details>

<details>
<summary><b>Fallback chains</b> (never get stuck on a down or rate-limited model)</summary>

Any `MODEL*` variable can list several models, separated by commas. They are tried in order: if a model fails **before it sends any output** (server error, rate limit after retries, timeout, connection error), the request is replayed on the next one. Claude Code just sees a normal answer.

```dotenv
MODEL_SONNET="nvidia_nim/z-ai/glm4.7,open_router/arcee-ai/trinity-large-preview:free,lmstudio/qwen3-coder"
```

- Mix providers freely: each one keeps its own rate limits, so a 429 on NIM doesn't slow down OpenRouter.
- An error after the answer has started, or on the last model, is shown as usual.
- The proxy logs every switch as `MODEL_FALLBACK` in `server.log`.

</details>

### Run It

**Terminal 1:** Start the proxy server:

```bash
uv run uvicorn server:app --port 8082
```

**Terminal 2:** Run Claude Code:

```bash
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude
```

That's it! Claude Code now uses your configured provider for free.

**Something not working?** Run the doctor. It checks your `.env`, that every configured model's provider has a key, is reachable and really offers that model, that Claude Code is installed, that the proxy is running, and common security mistakes:

```bash
uv run python doctor.py
```

```
 ✓ .env found
 ✓ nvidia_nim/z-ai/glm4.7 is available
 ✗ groq: GROQ_API_KEY is not set. Add it to your .env file. Get a key at https://console.groq.com/keys
 ✓ Claude Code 2.1.292 (Claude Code)
 ✓ proxy is running on port 8082
 ✓ no security issues found
```

<details>
<summary><b>Run with Docker</b></summary>

With your `.env` in place:

```bash
docker compose up -d --build
```

The proxy is then at `http://localhost:8082`, published on this machine only. Point Claude Code at it as above.

- LM Studio or Ollama running on your machine (not in Docker) is reached through `host.docker.internal`, e.g. `LM_STUDIO_BASE_URL="http://host.docker.internal:1234/v1"`.
- The image runs the proxy only; the Discord/Telegram bot needs the Claude Code CLI and runs outside Docker.

</details>

<details>
<summary><b>Remote access & security</b> (WSL, Docker, another machine)</summary>

By default the proxy only accepts connections from this machine. To reach it from elsewhere:

```dotenv
PROXY_AUTH_TOKEN="pick-a-long-random-string"
```

```bash
uv run uvicorn server:app --host 0.0.0.0 --port 8082
ANTHROPIC_AUTH_TOKEN="pick-a-long-random-string" ANTHROPIC_BASE_URL="http://<proxy-ip>:8082" claude
```

When `PROXY_AUTH_TOKEN` is set, every API call must send it (`Authorization: Bearer` or `x-api-key`); `/health` stays open. Never expose the proxy without it: anyone who can reach it could spend your provider quota.

</details>

<details>
<summary><b>VSCode Extension Setup</b></summary>

1. Start the proxy server (same as above).
2. Open Settings (`Ctrl + ,`) and search for `claude-code.environmentVariables`.
3. Click **Edit in settings.json** and add:

```json
"claude-code.environmentVariables": [
  { "name": "ANTHROPIC_BASE_URL", "value": "http://localhost:8082" },
  { "name": "ANTHROPIC_AUTH_TOKEN", "value": "freecc" }
]
```

4. Reload extensions.
5. **If you see the login screen** ("How do you want to log in?"): Click **Anthropic Console**, then authorize. The extension will start working. You may be redirected to buy credits in the browser; ignore it, the extension already works.

To switch back to Anthropic models, comment out the added block and reload extensions.

</details>

<details>
<summary><b>Switch models inside Claude Code</b> (<code>/model</code> picker)</summary>

The proxy lists every model from your `MODEL*` settings (fallback chains included) at `/v1/models`. Turn on Claude Code's gateway model discovery and they show up in `/model`, labelled with the setting that uses them:

```bash
CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1 ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude
```

Picking one (its ID looks like `claude-fcc/groq/llama-3.3-70b-versatile`) sends that session's requests straight to that model; you can also start with it: `claude --model claude-fcc/<provider>/<model>`. Claude Code refreshes the list at each startup.

</details>

<details>
<summary><b>Multi-Model Support (Model Picker)</b></summary>

`claude-pick` lets you choose any model a provider offers, its full catalog, each time you launch Claude, without editing `MODEL` in `.env`. It works with every provider (NIM, OpenRouter, LM Studio, Ollama, Groq, Gemini, …): the running proxy fetches the list with the key from your `.env`.

https://github.com/user-attachments/assets/9a33c316-90f8-4418-9650-97e7d33ad645

**1. Install [fzf](https://github.com/junegunn/fzf)** (required for the interactive picker):

```bash
brew install fzf        # macOS/Linux
```

**2. Add the alias to `~/.zshrc` or `~/.bashrc`:**

```bash
# Use the absolute path to your cloned repo
alias claude-pick="/absolute/path/to/free-claude-code/claude-pick"
```

Then reload your shell (`source ~/.zshrc` or `source ~/.bashrc`), start the proxy, and run:

```bash
claude-pick              # models of the provider in your MODEL setting
claude-pick groq         # or name a provider: groq, gemini, open_router, ollama, ...
claude-pick gemini -c    # extra arguments go to claude
```

It launches `claude --model claude-fcc/<provider>/<model>`, which the proxy routes to that model.

**Skip the picker with a fixed model** (no picker needed):

```bash
alias claude-kimi='ANTHROPIC_BASE_URL="http://localhost:8082" ANTHROPIC_AUTH_TOKEN="freecc:nvidia_nim/moonshotai/kimi-k2.5" claude'
```

</details>

---

## How It Works

```
┌─────────────────┐        ┌──────────────────────┐        ┌──────────────────┐
│  Claude Code    │───────>│  Free Claude Code    │───────>│  LLM Provider    │
│  CLI / VSCode   │<───────│  Proxy (:8082)       │<───────│  NIM / OR / LMS  │
└─────────────────┘        └──────────────────────┘        └──────────────────┘
   Anthropic API                     │                       OpenAI-compatible
   format (SSE)              ┌───────┴────────┐                format (SSE)
                             │ Optimizations  │
                             ├────────────────┤
                             │ Quota probes   │
                             │ Title gen skip │
                             │ Prefix detect  │
                             │ Suggestion skip│
                             │ Filepath mock  │
                             └────────────────┘
```

- **Transparent proxy**: Claude Code sends standard Anthropic API requests to the proxy server
- **Per-model routing**: Opus / Sonnet / Haiku requests are resolved to their model-specific backend and provider, with the default `MODEL` as fallback
- **Request optimization**: 5 categories of trivial requests (quota probes, title generation, prefix detection, suggestions, filepath extraction) are intercepted and responded to instantly without using API quota
- **Format translation**: real requests are translated from Anthropic format to the provider's OpenAI-compatible format and streamed back. Mid-conversation `system` messages that current Claude Code sends become user turns, since many models only accept a leading system prompt
- **Thinking tokens**: `<think>` tags and `reasoning_content` fields are converted into native Claude thinking blocks so Claude Code renders them correctly. Reasoning is only switched on (NIM, OpenRouter) when Claude Code asks for thinking (`adaptive` or `enabled`), so side requests like compaction don't spend reasoning tokens
- **Output limits**: Claude Code asks for up to 128k output tokens, more than many models allow. When a provider rejects that and states its limit (Groq, DeepSeek, OpenAI-style errors), the request is retried with that limit and the model is remembered. To pick a lower value yourself, set `CLAUDE_CODE_MAX_OUTPUT_TOKENS` when starting Claude Code
- **Images**: pasted images are sent as OpenAI `image_url` parts. If a model rejects them, the request is retried once without images and that model is remembered as text-only. Images inside tool results (e.g. `Read` on a PNG) become a short placeholder instead of raw base64
- **Tool calls**: native tool calls and tool calls a model writes as text become Anthropic `tool_use` blocks; a turn with tool calls always ends with `stop_reason: tool_use`
- **Fallback chains**: a model that fails before answering is skipped for the next model in its `MODEL*` chain
- **Errors**: provider failures reach Claude Code as real Anthropic errors (an SSE `error` event, or an HTTP error status for `stream: false`), so Claude Code's own retries kick in instead of the error being shown as model output
- **Keepalive**: the stream carries an SSE `ping` every 15s, so Claude Code's idle watchdog never cuts off a slow model

---

## Providers

| Provider                                                | Cost              | Rate Limit | Models                            | Best For                             |
| ------------------------------------------------------- | ----------------- | ---------- | --------------------------------- | ------------------------------------ |
| **NVIDIA NIM**                                          | Free              | 40 req/min | Kimi K2, GLM5, Devstral, MiniMax  | Daily driver, generous free tier     |
| **OpenRouter**                                          | Free / Paid       | Varies     | 200+ (GPT-4o, Claude, Step, etc.) | Model variety, fallback options      |
| **LM Studio**                                           | Free (local)      | Unlimited  | Any GGUF model                    | Privacy, offline use, no rate limits |
| **Ollama**                                              | Free (local)      | Unlimited  | Any Ollama model                  | Local models with a simple CLI       |
| **Groq, Gemini, Cerebras, Mistral, DeepSeek, Together** | Free tiers / Paid | Varies     | Each provider's catalog           | Fast inference, fallback chains      |

Switch providers by changing `MODEL` in `.env`. Use the prefix format `provider/model/name`. Invalid prefix causes an error. A provider whose key is missing answers with a clear error naming the variable to set.

| Provider              | MODEL prefix      | API Key Variable            | Base URL                                          |
| --------------------- | ----------------- | --------------------------- | ------------------------------------------------- |
| NVIDIA NIM            | `nvidia_nim/...`  | `NVIDIA_NIM_API_KEY`        | `integrate.api.nvidia.com/v1`                     |
| OpenRouter            | `open_router/...` | `OPENROUTER_API_KEY`        | `openrouter.ai/api/v1`                            |
| LM Studio             | `lmstudio/...`    | (none)                      | `localhost:1234/v1` (`LM_STUDIO_BASE_URL`)        |
| Ollama                | `ollama/...`      | (none)                      | `localhost:11434/v1` (`OLLAMA_BASE_URL`)          |
| Groq                  | `groq/...`        | `GROQ_API_KEY`              | `api.groq.com/openai/v1`                          |
| Cerebras              | `cerebras/...`    | `CEREBRAS_API_KEY`          | `api.cerebras.ai/v1`                              |
| Google Gemini         | `gemini/...`      | `GEMINI_API_KEY`            | `generativelanguage.googleapis.com/v1beta/openai` |
| Mistral               | `mistral/...`     | `MISTRAL_API_KEY`           | `api.mistral.ai/v1`                               |
| DeepSeek              | `deepseek/...`    | `DEEPSEEK_API_KEY`          | `api.deepseek.com/v1`                             |
| Together AI           | `together/...`    | `TOGETHER_API_KEY`          | `api.together.xyz/v1`                             |
| Any OpenAI-compatible | `custom/...`      | `CUSTOM_API_KEY` (optional) | `CUSTOM_BASE_URL`                                 |

LM Studio runs locally. Start the server in the Developer tab or via `lms server start`, load a model, and set `MODEL` to the model identifier.

---

## Discord Bot

Control Claude Code remotely from Discord. Send tasks, watch live progress, and manage multiple concurrent sessions. Telegram is also supported.

**Capabilities:**

- Tree-based message threading: reply to a message to fork the conversation
- Session persistence across server restarts, crash-safe: `sessions.json` (in `CLAUDE_WORKSPACE`) is written atomically, and an unreadable file is kept as `sessions.json.corrupt-<time>` instead of being overwritten
- Live streaming of thinking tokens, tool calls, and results
- Many conversations in parallel; at most `MAX_CONCURRENT_CLI` Claude Code processes run at once (default 4), further tasks wait for a free slot
- **Voice notes**: send voice messages; they are transcribed and processed like regular prompts (see [Voice Notes](#voice-notes))
- Commands: `/stop` (cancel tasks; reply to a message to stop only that task), `/clear` (standalone: reset all sessions; reply to a message to clear that branch downwards), `/stats`

### Setup

1. **Create a Discord Bot**: Go to [Discord Developer Portal](https://discord.com/developers/applications), create an application, add a bot, and copy the token. Enable **Message Content Intent** under Bot settings.

2. **Edit `.env`:**

```dotenv
MESSAGING_PLATFORM="discord"
DISCORD_BOT_TOKEN="your_discord_bot_token"
ALLOWED_DISCORD_CHANNELS="123456789,987654321"
```

> Enable Developer Mode in Discord (Settings → Advanced), then right-click a channel and "Copy ID" to get channel IDs. Comma-separate multiple channels. If empty, no channels are allowed.

3. **Configure the workspace** (where Claude will operate):

```dotenv
CLAUDE_WORKSPACE="./agent_workspace"
ALLOWED_DIR="C:/Users/yourname/projects"
```

4. **Start the server:**

```bash
uv run uvicorn server:app --port 8082
```

5. **Invite the bot** (OAuth2 URL Generator, scopes: `bot`, permissions: Read Messages, Send Messages, Manage Messages, Read Message History). Send a task to an allowed channel and Claude responds with live thinking tokens and tool calls. Use commands above to cancel or clear.

### Telegram (Alternative)

To use Telegram instead, set `MESSAGING_PLATFORM=telegram` and configure:

```dotenv
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"
ALLOWED_TELEGRAM_USER_ID="your_telegram_user_id"
```

Get a token from [@BotFather](https://t.me/BotFather); find your user ID via [@userinfobot](https://t.me/userinfobot).

### Voice Notes

Send voice messages on Telegram or Discord; they are transcribed to text and processed as regular prompts. Two transcription backends are available:

- **Local Whisper** (default): Uses [Hugging Face transformers Whisper](https://huggingface.co/openai/whisper-large-v3-turbo) — free, no API key, works offline, CUDA compatible. No ffmpeg required.
- **NVIDIA NIM**: Uses NVIDIA NIM Whisper/Parkeet models via gRPC — requires `NVIDIA_NIM_API_KEY`.

Install the optional voice extras:

```bash
# For local Whisper (cpu/cuda)
uv sync --extra voice_local

# For NVIDIA NIM transcription
uv sync --extra voice

# Install both
uv sync --extra voice --extra voice_local
```

**Configuration:**

| Variable             | Description                                                                 | Default |
| -------------------- | --------------------------------------------------------------------------- | ------- |
| `VOICE_NOTE_ENABLED` | Enable voice note handling                                                  | `true`  |
| `WHISPER_DEVICE`     | `cpu` \| `cuda` \| `nvidia_nim`                                             | `cpu`   |
| `WHISPER_MODEL`      | See supported models below                                                  | `base`  |
| `HF_TOKEN`           | Hugging Face token for faster model downloads (optional, for local Whisper) | —       |
| `NVIDIA_NIM_API_KEY` | API key for NVIDIA NIM (required for `nvidia_nim` device)                   | —       |

**Supported `WHISPER_MODEL` values:**

| Model                                                                       | Device         | Description                            |
| --------------------------------------------------------------------------- | -------------- | -------------------------------------- |
| `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`, `large-v3-turbo` | `cpu` / `cuda` | Local Whisper (Hugging Face)           |
| `openai/whisper-large-v3`                                                   | `nvidia_nim`   | Auto language detection (best overall) |
| `nvidia/parakeet-ctc-1.1b-asr`                                              | `nvidia_nim`   | English-only                           |
| `nvidia/parakeet-ctc-0.6b-asr`                                              | `nvidia_nim`   | English-only                           |
| `nvidia/parakeet-ctc-0.6b-zh-cn`                                            | `nvidia_nim`   | Mandarin Chinese                       |
| `nvidia/parakeet-ctc-0.6b-zh-tw`                                            | `nvidia_nim`   | Traditional Chinese                    |
| `nvidia/parakeet-ctc-0.6b-es`                                               | `nvidia_nim`   | Spanish                                |
| `nvidia/parakeet-ctc-0.6b-vi`                                               | `nvidia_nim`   | Vietnamese                             |
| `nvidia/parakeet-1.1b-rnnt-multilingual-asr`                                | `nvidia_nim`   | Multilingual RNNT                      |

---

## Models

<details>
<summary><b>NVIDIA NIM</b></summary>

Full list in [`nvidia_nim_models.json`](nvidia_nim_models.json).

Popular models:

- `nvidia_nim/minimaxai/minimax-m2.5`
- `nvidia_nim/qwen/qwen3.5-397b-a17b`
- `nvidia_nim/z-ai/glm5`
- `nvidia_nim/stepfun-ai/step-3.5-flash`
- `nvidia_nim/moonshotai/kimi-k2.5`

Browse: [build.nvidia.com](https://build.nvidia.com/explore/discover)

Update model list:

```bash
curl "https://integrate.api.nvidia.com/v1/models" > nvidia_nim_models.json
```

</details>

<details>
<summary><b>OpenRouter</b></summary>

Hundreds of models from StepFun, OpenAI, Anthropic, Google, and more.

Popular models:

- `open_router/stepfun/step-3.5-flash:free`
- `open_router/deepseek/deepseek-r1-0528:free`
- `open_router/openai/gpt-oss-120b:free`

Browse: [openrouter.ai/models](https://openrouter.ai/models)

Browse free models: [https://openrouter.ai/collections/free-models](https://openrouter.ai/collections/free-models)

</details>

<details>
<summary><b>LM Studio</b></summary>

Run models locally with [LM Studio](https://lmstudio.ai). Load a model in the Chat or Developer tab, then set `MODEL` to its identifier.

Examples (native tool-use support):

- `LiquidAI/LFM2-24B-A2B-GGUF`
- `unsloth/MiniMax-M2.5-GGUF`
- `unsloth/GLM-4.7-Flash-GGUF`
- `unsloth/Qwen3.5-35B-A3B-GGUF`
- `LocoreMind/LocoOperator-4B`

Browse: [model.lmstudio.ai](https://model.lmstudio.ai)

</details>

---

## Configuration

| Variable                            | Description                                                                                     | Default                                           |
| ----------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `MODEL`                             | Default model (`provider/model/name`); comma-separate a chain to fall back on errors            | `nvidia_nim/stepfun-ai/step-3.5-flash`            |
| `MODEL_OPUS`                        | Model for Claude Opus requests (optional, falls back to `MODEL`)                                | `nvidia_nim/z-ai/glm4.7`                          |
| `MODEL_SONNET`                      | Model for Claude Sonnet requests (optional, falls back to `MODEL`)                              | `open_router/arcee-ai/trinity-large-preview:free` |
| `MODEL_HAIKU`                       | Model for Claude Haiku requests (optional, falls back to `MODEL`)                               | `open_router/stepfun/step-3.5-flash:free`         |
| `NVIDIA_NIM_API_KEY`                | NVIDIA API key (NIM provider)                                                                   | required                                          |
| `OPENROUTER_API_KEY`                | OpenRouter API key (OpenRouter provider)                                                        | required                                          |
| `LM_STUDIO_BASE_URL`                | LM Studio server URL                                                                            | `http://localhost:1234/v1`                        |
| `OLLAMA_BASE_URL`                   | Ollama server URL                                                                               | `http://localhost:11434/v1`                       |
| `GROQ_API_KEY` … `TOGETHER_API_KEY` | Keys for the Groq, Cerebras, Gemini, Mistral, DeepSeek and Together presets                     | `""`                                              |
| `CUSTOM_BASE_URL`                   | Any OpenAI-compatible endpoint, used as `custom/<model>`                                        | `""`                                              |
| `CUSTOM_API_KEY`                    | API key for `CUSTOM_BASE_URL` (optional)                                                        | `""`                                              |
| `HOST`                              | Interface the proxy listens on (`python server.py`); use `0.0.0.0` only with `PROXY_AUTH_TOKEN` | `127.0.0.1`                                       |
| `PROXY_AUTH_TOKEN`                  | Token clients must send as `ANTHROPIC_AUTH_TOKEN` (empty = no check)                            | `""`                                              |
| `LOG_LEVEL`                         | `server.log` level; `DEBUG` also logs full request payloads (prompts, files)                    | `INFO`                                            |
| `PROVIDER_RATE_LIMIT`               | LLM API requests per window, per provider                                                       | `40`                                              |
| `PROVIDER_RATE_WINDOW`              | Rate limit window (seconds)                                                                     | `60`                                              |
| `PROVIDER_MAX_CONCURRENCY`          | Max simultaneous open streams, per provider                                                     | `5`                                               |
| `HTTP_READ_TIMEOUT`                 | Read timeout for provider API requests (seconds)                                                | `120`                                             |
| `HTTP_WRITE_TIMEOUT`                | Write timeout for provider API requests (seconds)                                               | `10`                                              |
| `HTTP_CONNECT_TIMEOUT`              | Connect timeout for provider API requests (seconds)                                             | `2`                                               |
| `FAST_PREFIX_DETECTION`             | Enable fast prefix detection                                                                    | `true`                                            |
| `ENABLE_NETWORK_PROBE_MOCK`         | Enable network probe mock                                                                       | `true`                                            |
| `ENABLE_TITLE_GENERATION_SKIP`      | Skip title generation                                                                           | `true`                                            |
| `ENABLE_SUGGESTION_MODE_SKIP`       | Skip suggestion mode                                                                            | `true`                                            |
| `ENABLE_FILEPATH_EXTRACTION_MOCK`   | Enable filepath extraction mock                                                                 | `true`                                            |
| `MESSAGING_PLATFORM`                | Messaging platform: `discord` or `telegram`                                                     | `discord`                                         |
| `DISCORD_BOT_TOKEN`                 | Discord Bot Token                                                                               | `""`                                              |
| `ALLOWED_DISCORD_CHANNELS`          | Comma-separated channel IDs (empty = none allowed)                                              | `""`                                              |
| `TELEGRAM_BOT_TOKEN`                | Telegram Bot Token                                                                              | `""`                                              |
| `ALLOWED_TELEGRAM_USER_ID`          | Allowed Telegram User ID (empty = nobody allowed)                                               | `""`                                              |
| `VOICE_NOTE_ENABLED`                | Enable voice note handling                                                                      | `true`                                            |
| `WHISPER_MODEL`                     | Local Whisper model size                                                                        | `base`                                            |
| `WHISPER_DEVICE`                    | `cpu` \                                                                                         | `cuda`                                            |
| `MESSAGING_RATE_LIMIT`              | Messaging messages per window                                                                   | `1`                                               |
| `MESSAGING_RATE_WINDOW`             | Messaging window (seconds)                                                                      | `1`                                               |
| `MAX_CONCURRENT_CLI`                | Claude Code processes the bot runs at once; more tasks wait                                     | `4`                                               |
| `CLAUDE_WORKSPACE`                  | Directory for agent workspace                                                                   | `./agent_workspace`                               |
| `ALLOWED_DIR`                       | Allowed directories for agent                                                                   | `""`                                              |

See [`.env.example`](.env.example) for all supported parameters.

---

## Development

### Project Structure

```
free-claude-code/
├── server.py              # Entry point
├── api/                   # FastAPI routes, request detection, optimization handlers
├── providers/             # BaseProvider, OpenAICompatibleProvider, NIM, OpenRouter, LM Studio
│   └── common/            # Shared utils (SSE builder, message converter, parsers, error mapping)
├── messaging/             # MessagingPlatform ABC + Discord/Telegram bots, session management
├── config/                # Settings, NIM config, logging
├── cli/                   # CLI session and process management
└── tests/                 # Pytest test suite
```

### Commands

```bash
uv run ruff format     # Format code
uv run ruff check      # Code style checking
uv run ty check        # Type checking
uv run pytest          # Run tests
```

---

## Extending

### Adding a Provider

For **OpenAI-compatible APIs** (Groq, Together AI, etc.), extend `OpenAICompatibleProvider`:

```python
from providers.openai_compat import OpenAICompatibleProvider
from providers.base import ProviderConfig

class MyProvider(OpenAICompatibleProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_name="MYPROVIDER",
                         base_url="https://api.example.com/v1", api_key=config.api_key)

    def _build_request_body(self, request):
        return build_request_body(request)  # Your request builder
```

For **fully custom APIs**, extend `BaseProvider` directly:

```python
from providers.base import BaseProvider, ProviderConfig

class MyProvider(BaseProvider):
    async def stream_response(self, request, input_tokens=0, *, request_id=None):
        # Yield Anthropic SSE format events
        ...
```

### Adding a Messaging Platform

Extend `MessagingPlatform` in `messaging/` to add Slack or other platforms:

```python
from messaging.base import MessagingPlatform

class MyPlatform(MessagingPlatform):
    async def start(self):
        # Initialize connection
        ...

    async def stop(self):
        # Cleanup
        ...

    async def send_message(self, chat_id, text, reply_to=None, parse_mode=None, message_thread_id=None):
        # Send a message
        ...

    async def edit_message(self, chat_id, message_id, text, parse_mode=None):
        # Edit an existing message
        ...

    def on_message(self, handler):
        # Register callback for incoming messages
        ...
```

---

## Contributing

- Report bugs or suggest features via [Issues](https://github.com/Rishurajgautam24/free-claude-code/issues)
- Add new LLM providers (Groq, Together AI, etc.)
- Add new messaging platforms (Slack, etc.)
- Improve test coverage
- Not accepting Docker Integration for now
- New and interesting features

```bash
# Fork the repo, then:
git checkout -b my-feature
# Make your changes
uv run ruff format && uv run ruff check && uv run ty check && uv run pytest
# Open a pull request
```

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

Built with [FastAPI](https://fastapi.tiangolo.com/), [OpenAI Python SDK](https://github.com/openai/openai-python), [discord.py](https://github.com/Rapptz/discord.py), and [python-telegram-bot](https://python-telegram-bot.org/).
