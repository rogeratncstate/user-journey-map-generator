#!/usr/bin/env python3
"""Generate journey map personas from course documents using ChatGPT and commit them to GitHub.

This script automates the flow described in the project documentation:

1. Read course collateral (feasibility assessments, design docs, market research) from
   ``docs/<course>/``.
2. Ask the OpenAI Chat Completions API to draft persona journey maps that match the
   JSON schema consumed by the web app.
3. Upload the generated personas to the ``data/<Course_Name>/`` folder in GitHub,
   creating or updating JSON files as needed.
4. Optionally refresh the local ``data/manifest.json`` fallback when GitHub access is
   unavailable.

The script is intentionally self-contained so it can run from a developer workstation
or inside a CI workflow. It relies on a handful of environment variables for
credentials and repository metadata (see ``.env.example`` for the full list).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o"


class PersonaValidationError(Exception):
    """Raised when the generated persona payload does not match the expected schema."""


@dataclass
class Persona:
    slug: str
    data: Dict

    def to_json_bytes(self) -> bytes:
        return json.dumps(self.data, ensure_ascii=False, indent=2).encode("utf-8")


@dataclass
class CourseDocuments:
    course: str
    files: List[Path]

    @property
    def combined_prompt(self) -> str:
        sections: List[str] = []
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raise ValueError(f"File {path} is not UTF-8 text; convert it before running the generator.")
            sections.append(f"### {path.name}\n{text}\n")
        return "\n".join(sections)


@dataclass
class GitHubConfig:
    owner: str
    repo: str
    branch: str
    token: str

    @property
    def base_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }


# --------------------
# Prompt engineering
# --------------------

def build_prompt(course: str, document_bundle: CourseDocuments, persona_count: int) -> List[Dict[str, str]]:
    """Create the chat prompt that instructs the model to output persona JSON."""

    instructions = f"""
    You are an experienced learning-experience designer. Generate {persona_count} detailed user
    journey personas for the course "{course}". Use the provided course collateral to infer the
    target audiences, their motivations, pains, and opportunities.

    Output **only** valid JSON (no prose or markdown code fences). The JSON must be a list in which
    each element has the following structure:

    {{
      "slug": "lower_snake_case_identifier",
      "persona": "Display Name",
      "scenario": "Short paragraph setting the context",
      "expectations": ["list of learner expectations"],
      "phases": [
        {{
          "title": "Phase X | Label",
          "actions": ["learner actions"],
          "pains": ["learner pains"],
          "feelings": {{
            "score": integer 1-5,
            "quote": "Representative learner quote"
          }},
          "opportunities": ["ways the program can help"]
        }}
        // include exactly four phases: Awareness, Consideration, Decision, Retention (in that order)
      ]
    }}

    Requirements:
    * Use authentic names and scenarios grounded in the source documents.
    * Keep arrays between three and five items to maintain readability.
    * Ensure every persona has four phases labelled with the naming convention "Phase N | ...".
    * Make "slug" unique per persona and derived from the persona name.
    * Do not include markdown fences, explanations, or trailing commas.
    """

    system_message = {
        "role": "system",
        "content": "You create structured persona journey maps as clean JSON objects.",
    }
    user_message = {
        "role": "user",
        "content": instructions.strip() + "\n\n" + document_bundle.combined_prompt,
    }
    return [system_message, user_message]


# --------------------
# Persona validation helpers
# --------------------

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_{2,}", "_", value)
    return value.strip("_") or "persona"


def ensure_persona_schema(payload: Dict) -> None:
    """Validate a persona payload and raise PersonaValidationError on failure."""

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise PersonaValidationError(message)

    require(isinstance(payload, dict), "Persona must be a JSON object.")
    for key in ("persona", "scenario", "expectations", "phases"):
        require(key in payload, f"Missing required key: {key}")

    require(isinstance(payload["persona"], str) and payload["persona"].strip(), "'persona' must be a non-empty string.")
    require(isinstance(payload["scenario"], str) and payload["scenario"].strip(), "'scenario' must be a non-empty string.")
    require(isinstance(payload["expectations"], list) and payload["expectations"], "'expectations' must be a non-empty list.")
    require(all(isinstance(item, str) and item.strip() for item in payload["expectations"]), "'expectations' items must be strings.")

    phases = payload["phases"]
    require(isinstance(phases, list) and len(phases) == 4, "'phases' must contain exactly four entries.")

    for phase in phases:
        require(isinstance(phase, dict), "Each phase must be a JSON object.")
        for key in ("title", "actions", "pains", "feelings", "opportunities"):
            require(key in phase, f"Phase is missing required key: {key}")
        require(isinstance(phase["title"], str) and phase["title"].strip(), "Phase 'title' must be a non-empty string.")
        for key in ("actions", "pains", "opportunities"):
            require(isinstance(phase[key], list) and phase[key], f"Phase '{key}' must be a non-empty list.")
            require(all(isinstance(item, str) and item.strip() for item in phase[key]), f"Phase '{key}' entries must be strings.")

        feelings = phase["feelings"]
        require(isinstance(feelings, dict), "'feelings' must be an object.")
        require("score" in feelings and isinstance(feelings["score"], int), "'feelings.score' must be an integer.")
        require(1 <= feelings["score"] <= 5, "'feelings.score' must be between 1 and 5.")
        require("quote" in feelings and isinstance(feelings["quote"], str) and feelings["quote"].strip(), "'feelings.quote' must be a non-empty string.")


def parse_personas_from_response(response_text: str) -> List[Persona]:
    """Extract and validate persona JSON structures from the model response."""

    trimmed = response_text.strip()
    if trimmed.startswith("```"):
        # Remove optional Markdown code fences the model might add despite instructions.
        trimmed = re.sub(r"^```(?:json)?\n", "", trimmed)
        trimmed = re.sub(r"```$", "", trimmed)
        trimmed = trimmed.strip()

    try:
        raw_personas = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        raise PersonaValidationError(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(raw_personas, list) or not raw_personas:
        raise PersonaValidationError("Expected the model to return a non-empty JSON list of personas.")

    personas: List[Persona] = []
    slugs_seen = set()
    for entry in raw_personas:
        ensure_persona_schema(entry)
        slug_source = entry.get("slug") if isinstance(entry.get("slug"), str) else entry["persona"]
        slug = slugify(slug_source)
        if slug in slugs_seen:
            raise PersonaValidationError(f"Duplicate persona slug detected: {slug}")
        slugs_seen.add(slug)
        entry["slug"] = slug
        personas.append(Persona(slug=slug, data=entry))
    return personas


# --------------------
# GitHub helpers
# --------------------

def github_request(method: str, url: str, config: GitHubConfig, **kwargs) -> requests.Response:
    response = requests.request(method, url, headers=config.base_headers, **kwargs)
    if response.status_code == 401:
        raise PermissionError("GitHub authentication failed. Check GITHUB_TOKEN.")
    return response


def ensure_course_folder(config: GitHubConfig, course_folder: str) -> None:
    """Creating files in a new folder via the Contents API implicitly creates the folder."""
    # No-op placeholder kept for readability and future enhancement (e.g., README seeding).
    _ = config, course_folder


def github_get_file_sha(config: GitHubConfig, path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{config.owner}/{config.repo}/contents/{path}"
    response = github_request("GET", url, config, params={"ref": config.branch})
    if response.status_code == 200:
        payload = response.json()
        return payload.get("sha")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return None


def github_create_or_update_file(config: GitHubConfig, *, path: str, content: bytes, message: str) -> None:
    sha = github_get_file_sha(config, path)
    payload = {
        "message": message,
        "content": base64.b64encode(content).decode("utf-8"),
        "branch": config.branch,
    }
    if sha:
        payload["sha"] = sha
    url = f"https://api.github.com/repos/{config.owner}/{config.repo}/contents/{path}"
    response = github_request("PUT", url, config, json=payload)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"GitHub file upload failed for {path}: {response.status_code} {response.text}")


def fetch_remote_manifest(config: GitHubConfig, base_path: str = "data") -> Dict:
    """Construct a manifest dictionary by walking the GitHub data directory."""

    def list_directory(path: str) -> Iterable[Dict]:
        url = f"https://api.github.com/repos/{config.owner}/{config.repo}/contents/{path}"
        response = github_request("GET", url, config, params={"ref": config.branch})
        if response.status_code != 200:
            raise RuntimeError(f"Failed to list GitHub directory {path}: {response.status_code} {response.text}")
        return response.json()

    courses: List[Dict] = []
    for entry in list_directory(base_path):
        if entry["type"] != "dir":
            continue
        course_folder = entry["name"]
        files = [item["name"] for item in list_directory(f"{base_path}/{course_folder}") if item["type"] == "file" and item["name"].endswith(".json")]
        files.sort()
        course_name = course_folder.replace("_", " ").title()
        courses.append({
            "name": course_name,
            "folder": course_folder,
            "files": files,
        })
    courses.sort(key=lambda item: item["name"].lower())
    return {"courses": courses}


# --------------------
# High level workflow
# --------------------

def call_openai(messages: List[Dict[str, str]], *, model: str, temperature: float) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is required.")

    response = requests.post(
        OPENAI_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text}")

    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected OpenAI API response structure: {payload}") from exc


def load_course_documents(course: str, docs_root: Path) -> CourseDocuments:
    course_path = docs_root / course
    if not course_path.exists() or not course_path.is_dir():
        raise FileNotFoundError(f"Course collateral directory not found: {course_path}")

    text_files = sorted(
        [path for path in course_path.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"}],
        key=lambda path: path.name,
    )
    if not text_files:
        raise FileNotFoundError(f"No supported text documents found under {course_path}")

    return CourseDocuments(course=course, files=text_files)


def parse_github_repo(repo: str) -> (str, str):
    if "/" not in repo:
        raise ValueError("GITHUB_REPO must be in the format 'owner/repo'.")
    owner, name = repo.split("/", 1)
    return owner, name


def configure_github_from_env() -> GitHubConfig:
    repo = os.environ.get("GITHUB_REPO")
    token = os.environ.get("GITHUB_TOKEN")
    branch = os.environ.get("GITHUB_BRANCH", "main")

    if not repo or not token:
        raise EnvironmentError("GITHUB_REPO and GITHUB_TOKEN environment variables are required for GitHub uploads.")

    owner, name = parse_github_repo(repo)
    return GitHubConfig(owner=owner, repo=name, branch=branch, token=token)


def update_local_manifest(manifest_path: Path, manifest_payload: Dict) -> None:
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    print(f"Updated local manifest at {manifest_path}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate persona journey maps with ChatGPT and push to GitHub.")
    parser.add_argument("course", nargs="?", help="Course folder name (e.g., Introduction_to_Data_Science)")
    parser.add_argument("--docs-root", default="docs", help="Base directory containing course collateral (default: docs)")
    parser.add_argument("--personas", type=int, default=3, help="Number of personas to request from the model (default: 3)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature for the model (default: 0.7)")
    parser.add_argument("--dry-run", action="store_true", help="Generate personas but skip GitHub uploads")
    parser.add_argument("--output-dir", type=Path, default=Path("generated"), help="Directory to store generated JSON locally")
    parser.add_argument("--update-manifest", action="store_true", help="Refresh data/manifest.json after uploading to GitHub")
    parser.add_argument("--manifest-only", action="store_true", help="Skip OpenAI generation and only refresh the manifest")

    args = parser.parse_args(argv)

    if args.manifest_only:
        if not args.update_manifest:
            parser.error("--manifest-only requires --update-manifest")
        github_config = configure_github_from_env()
        manifest_payload = fetch_remote_manifest(github_config)
        manifest_path = Path("data/manifest.json")
        update_local_manifest(manifest_path, manifest_payload)
        print("Done.")
        return 0

    if not args.course:
        parser.error("course is required unless --manifest-only is used")

    course_docs = load_course_documents(args.course, Path(args.docs_root))
    messages = build_prompt(args.course, course_docs, args.personas)
    print(f"Generating {args.personas} personas for course '{args.course}' using model {args.model}...")
    response_text = call_openai(messages, model=args.model, temperature=args.temperature)

    personas = parse_personas_from_response(response_text)
    print(f"Received {len(personas)} personas from the model.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for persona in personas:
        output_path = args.output_dir / f"{args.course}__{persona.slug}.json"
        output_path.write_bytes(persona.to_json_bytes())
        print(f"Saved {output_path.relative_to(Path.cwd())}")

    if args.dry_run:
        print("Dry run mode enabled; skipping GitHub upload.")
    else:
        github_config = configure_github_from_env()
        ensure_course_folder(github_config, args.course)
        for persona in personas:
            remote_path = f"data/{args.course}/{persona.slug}.json"
            commit_message = f"Add persona {persona.data['persona']} for {args.course.replace('_', ' ')}"
            github_create_or_update_file(
                github_config,
                path=remote_path,
                content=persona.to_json_bytes(),
                message=commit_message,
            )
            print(f"Uploaded {remote_path} to GitHub")

        if args.update_manifest:
            manifest_payload = fetch_remote_manifest(github_config)
            manifest_path = Path("data/manifest.json")
            update_local_manifest(manifest_path, manifest_payload)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
