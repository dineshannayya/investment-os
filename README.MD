You are an investment analysis assistant for Investment OS.

Your task is to perform a structured qualitative analysis of a startup
using only the information supplied in the startup input.

Do not invent facts, assumptions, financial figures, market data, founder
information, traction, or other information.

If information is not provided, do not infer it as fact. Identify it as
missing information where appropriate.

The deterministic financial metrics supplied in the input have already been
calculated deterministically. Treat these metrics as supplied facts.
Do not recalculate or modify them.

Your analysis should interpret the supplied information and identify:
- strengths
- risks
- missing information
- key observations
- investment thesis
- preliminary recommendation

Return only valid JSON matching the specified output schema.
Do not use Markdown code fences.

                 Startup Input
                      │
                      ▼
             ┌─────────────────┐
             │ Financial       │
             │ Metrics Service │
             └────────┬────────┘
                      │
             deterministic metrics
                      │
                      ▼
              ┌───────────────┐
              │ Prompt Builder│
              └───────┬───────┘
                      │
                      ▼
                    LLM
                      │
                      ▼
            Qualitative Analysis

| Artifact                                  | Source of truth                          | Responsibility                                       |
| ----------------------------------------- | ---------------------------------------- | ---------------------------------------------------- |
| **Startup / company data**                | `Startup` + related entities + documents | Original startup information/evidence                |
| **Analysis input**                        | `AnalysisInputBuilder`                   | Defines exactly what startup data enters an analysis |
| **Financial metrics**                     | `FinancialMetricsService`                | Deterministic financial calculations                 |
| **Generation configuration**              | `StartupAnalysisConfig`                  | Mode, thinking, model, tokens, temperature           |
| **Prompt**                                | Prompt Builder                           | Converts analysis input + metrics into LLM messages  |
| **Qualitative assessment**                | `QwenProvider` + `StartupAnalysisParser` | LLM generation + structured validation               |
| **LLM execution metadata**                | `LLMResponse`                            | Model, finish reason, token usage, generated text    |
| **Historical persistence representation** | `StartupAnalysisMapper`                  | Combines execution artifacts into persistence model  |
| **Database access**                       | `StartupAnalysisRepository`              | Save/load/query historical analyses                  |
| **Overall orchestration**                 | `StartupAnalysisOrchestrator`            | Coordinates the above; owns no analysis data         |

C.6.x framework implementation

                         Document
                            │
                            ▼
                  DocumentProcessingService
                            │
                            ▼
                 DocumentContent + Chunks
                            │
                            ▼
              InvestmentIntelligenceService
                            │
                            ▼
                 IntelligenceFactory
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
         Metadata        Entities       Financials
             │              │              │
             ├──────────────┼──────────────┤
             ▼              ▼              ▼
          Signals          Risks        Future...
             │
             ▼
       InvestmentProfile
             │
       ┌─────┴───────────────┐
       ▼                     ▼
 component confidence    quality/coverage
       │                     │
       └──────────┬──────────┘
                  ▼
       Startup Analysis Input
                  │
                  ▼
             Qwen Analysis
