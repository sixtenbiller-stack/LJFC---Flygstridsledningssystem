# Tactical Copilot Schemas

This document defines the schemas used for communication between the LJFC COMMAND backend and the AI Copilot (LM Studio / Gemini).

## 1. Tactical context Schema (LLM Input)

The following schema is injected into every prompt to give the AI a complete, structured view of the tactical situation.

```json
{
  "tracks": [
    {
      "id": "track_id",
      "side": "hostile | friendly | neutral",
      "class": "e.g., su-57, cruise_missile",
      "pos": [x_km, y_km],
      "speed": "slow | medium | fast",
      "alt": "low | medium | high",
      "threat_score": 0.0 to 1.0,
      "eta_s": seconds_to_nearest_zone
    }
  ],
  "assets": [
    {
      "id": "asset_id",
      "type": "e.g., jas-39, sam_battery",
      "status": "ready | active | recovering",
      "readiness": 0.0 to 1.0,
      "pos": [x_km, y_km],
      "munitions": {
        "air_to_air": 4,
        "sam_missile": 8
      }
    }
  ],
  "zones": [
    {
      "id": "zone_id",
      "priority": "critical | high | medium",
      "location": {"x": 0, "y": 0}
    }
  ]
}
```

## 2. Decision Output Schema (LLM Output)

When the Copilot recommends actions, it is instructed to include the following structured JSON block in its response. The backend extracts this block and places it in the `data.decisions` field of the API response.

```json
{
  "recommendation_summary": "English summary of the tactical recommendation",
  "decisions": [
    {
      "action": "INTERCEPT | MONITOR | REDEPLOY",
      "actor_id": "asset_id",
      "target_ids": ["track_id_1", "track_id_2"],
      "priority": "high | medium | low",
      "rationale": "Direct explanation of why this action is recommended"
    }
  ]
}
```

## How to use on the Map

1. **Prompt the Copilot**: Ask "What should I do about the new tracks?"
2. **Review Recommendations**: The Copilot will reply with text and a structured decision block.
3. **Map Interaction**: The UI can use the `target_ids` and `actor_id` to highlight relevant units on the map, allowing for rapid operator validation and execution through the standard COA approval flow.
