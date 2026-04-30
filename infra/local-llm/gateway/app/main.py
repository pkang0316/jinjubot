import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
EXTRACTOR_MODEL = os.getenv("OLLAMA_EXTRACTOR_MODEL", "jinjubot-extractor")
PLANNER_MODEL = os.getenv("OLLAMA_PLANNER_MODEL", "jinjubot-planner")

app = FastAPI(title="jinjubot-local-gateway", version="0.1.0")


class ExtractRequest(BaseModel):
  content: str = Field(..., min_length=1)
  source_url: str | None = None
  schema_hint: str | None = None
  additional_instructions: str | None = None


class PlanRequest(BaseModel):
  context: str = Field(..., min_length=1)
  budget: int | None = Field(default=None, ge=1)
  additional_instructions: str | None = None


def extract_json_block(raw_text: str) -> Any | None:
  text = raw_text.strip()

  if text.startswith("```"):
    lines = text.splitlines()
    if len(lines) >= 3:
      end_index = None
      for index in range(1, len(lines)):
        if lines[index].strip().startswith("```"):
          end_index = index
          break
      if end_index is not None:
        text = "\n".join(lines[1:end_index]).strip()

  try:
    return json.loads(text)
  except json.JSONDecodeError:
    start_object = text.find("{")
    end_object = text.rfind("}")

    if start_object != -1 and end_object != -1 and end_object > start_object:
      candidate = text[start_object : end_object + 1]
      try:
        return json.loads(candidate)
      except json.JSONDecodeError:
        return None

    return None


async def call_ollama(model: str, prompt: str) -> str:
  payload = {
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0,
  }

  async with httpx.AsyncClient(timeout=120.0) as client:
    try:
      response = await client.post(f"{OLLAMA_BASE_URL}/v1/chat/completions", json=payload)
      response.raise_for_status()
    except httpx.HTTPError as exc:
      raise HTTPException(status_code=502, detail=f"Ollama request failed: {exc}") from exc

  data = response.json()
  return data["choices"][0]["message"]["content"]


@app.get("/health")
async def health() -> dict[str, Any]:
  async with httpx.AsyncClient(timeout=5.0) as client:
    try:
      response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
      response.raise_for_status()
      tags = response.json()
    except httpx.HTTPError as exc:
      raise HTTPException(status_code=502, detail=f"Ollama healthcheck failed: {exc}") from exc

  available_models = [model["name"] for model in tags.get("models", [])]
  required_models = [f"{EXTRACTOR_MODEL}:latest", f"{PLANNER_MODEL}:latest"]
  missing_models = [model for model in required_models if model not in available_models]

  if missing_models:
    raise HTTPException(
      status_code=503,
      detail={
        "status": "initializing",
        "missing_models": missing_models,
        "available_models": available_models,
      },
    )

  return {
    "status": "ok",
    "ollama_base_url": OLLAMA_BASE_URL,
    "extractor_model": EXTRACTOR_MODEL,
    "planner_model": PLANNER_MODEL,
    "available_models": available_models,
  }


@app.post("/extract")
async def extract(request: ExtractRequest) -> dict[str, Any]:
  prompt = "\n\n".join(
    part
    for part in [
      "Extract high-signal structured findings from the following web content.",
      "Return valid JSON only.",
      (
        f"Schema hint:\n{request.schema_hint}"
        if request.schema_hint
        else 'Schema hint:\n{"records":[{"title":"","description":"","url":"","category":"","tags":[],"reason":""}]}'
      ),
      f"Source URL: {request.source_url}" if request.source_url else None,
      f"Additional instructions:\n{request.additional_instructions}" if request.additional_instructions else None,
      f"Content:\n{request.content}",
    ]
    if part
  )

  raw = await call_ollama(EXTRACTOR_MODEL, prompt)
  parsed = extract_json_block(raw)

  return {
    "model": EXTRACTOR_MODEL,
    "raw": raw,
    "parsed": parsed,
  }


@app.post("/plan")
async def plan(request: PlanRequest) -> dict[str, Any]:
  prompt = "\n\n".join(
    part
    for part in [
      "Create the next discovery plan for a web research agent.",
      "Return valid JSON only.",
      'Output shape:\n{"tasks":[{"action":"","target":"","reason":""}],"notes":""}',
      f"Budget: {request.budget}" if request.budget else None,
      f"Additional instructions:\n{request.additional_instructions}" if request.additional_instructions else None,
      f"Context:\n{request.context}",
    ]
    if part
  )

  raw = await call_ollama(PLANNER_MODEL, prompt)
  parsed = extract_json_block(raw)

  return {
    "model": PLANNER_MODEL,
    "raw": raw,
    "parsed": parsed,
  }
