# AI provider: DeepSeek V4 Flash (0731) via OpenAI-compatible API

The standardized patient and the scorer use DeepSeek V4 Flash (model id `deepseek-v4-flash`, serving the 0731 release) through the OpenAI-compatible endpoint at `https://api.deepseek.com`. The API key is read from the `DEEPSEEK_API_KEY` environment variable and never hardcoded. No budget cap is set initially; usage and cost visibility must be added before real student rollout. DeepSeek was chosen over other providers for cost and campus-network accessibility; the OpenAI-compatible adapter keeps the provider swappable.
