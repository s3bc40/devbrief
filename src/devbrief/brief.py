import os
import anthropic


def build_prompt(repo: dict, readme: str, file_tree: list[str]) -> str:
    readme_snippet = readme[:3000] if readme else "No README found."
    tree_str = "\n".join(file_tree) if file_tree else "No file tree available."
    topics_str = ", ".join(repo["topics"]) if repo["topics"] else "none"

    return f"""You are a senior developer writing a concise project brief for a technical audience.

Repository: {repo['name']}
Description: {repo['description'] or 'No description provided.'}
Stars: {repo['stars']}
Primary language: {repo['language'] or 'unknown'}
Topics: {topics_str}

Top-level file tree:
{tree_str}

README (first 3000 chars):
{readme_snippet}

Write a structured project brief with exactly these sections:
1. **One-line description** – A single crisp sentence summarizing the project.
2. **Problem it solves** – 2-3 sentences on the core problem addressed.
3. **Tech stack** – Bullet list of detected technologies/frameworks.
4. **Getting started** – 3-5 steps extracted or inferred from the README.
5. **Who would find it useful** – 2-3 sentences on the target audience.
6. **Limitations / potential improvements** – 3-5 bullet points.

Be concise. Do not repeat the section headers verbatim — use them as guidance only."""


def generate_brief(repo: dict, readme: str, file_tree: list[str]) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_prompt(repo, readme, file_tree)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
