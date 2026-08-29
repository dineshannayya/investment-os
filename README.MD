
┌─────────────────────────────────────────────────────────────┐
│                    SOURCE / DATA LAYER                      │
│                                                             │
│ PDF / DOCX / XLS / TXT                                      │
│ startup.yaml / founders.yaml / deal data                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 3.7.x STARTUP ANALYSIS                      │
│                                                             │
│ StartupAnalysisApplication                                  │
│          ↓                                                  │
│ StartupAnalysisOrchestrator                                 │
│          ↓                                                  │
│ Input Builder                                               │
│ Document Intelligence                                       │
│ Source Reconciliation                                       │
│ Financial Metrics                                           │
│          ↓                                                  │
│ StartupAnalysisService                                      │
│          ↓                                                  │
│ StartupAnalysisExecution                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               INVESTMENT ANALYSIS LAYER                     │
│                                                             │
│ Investment Evidence Builder                                 │
│          ↓                                                  │
│ DimensionEvidenceSet                                        │
│          ↓                                                  │
│ InvestmentScorecardEvaluationService                        │
│          ↓                                                  │
│ MultiDimensionEvaluation                                    │
│          ↓                                                  │
│ InvestmentScoreAggregationService                           │
│          ↓                                                  │
│ InvestmentDecisionService                                   │
│          ↓                                                  │
│ InvestmentViewService                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTENCE / HISTORY                    │
│                                                             │
│ Startup Analysis                                            │
│ Investment Analysis                                         │
│ Evidence / scores / decision / view                         │
└─────────────────────────────────────────────────────────────┘
