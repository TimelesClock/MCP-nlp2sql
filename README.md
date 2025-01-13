# NLP2SQL API

To build the docker image, run the following command:

```bash
docker buildx build --platform linux/amd64 -t nlp2sql-api:test .
```

Client -> API -> OpenAI -> MCP Tool -> OpenAI -> MCP Tool -> OpenAI -> Client-side Tool
└─────────────── Single API call (1-5 iterations) ───────────┘
                                                            Client handles tool
                                                            └── Makes new API call ──┘