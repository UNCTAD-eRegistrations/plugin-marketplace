# Voice Agent Plugin

Tools for managing and debugging voice agent deployments built with `@unctad-ai/voice-agent-kit`.

## Skills

### feedback-triage

Triage end-user feedback by correlating complaints with session traces. Fetches feedback entries, reconstructs conversations turn-by-turn, and classifies root causes.

```
/feedback-triage kenya
/feedback-triage https://custom-deploy.example.com --from 2026-03-01
```

## Requirements

- Voice agent deployment with kit v5.1.0+ (feedback and trace APIs)
- Deployment must be reachable via HTTPS
