#!/usr/bin/env python3
"""Synchronize and publish local skills to Google Cloud Gemini Enterprise Agent Platform (GEAP) Skill Registry.

Usage:
    uv run python scripts/sync_skills_to_geap.py
"""

import sys
import logging
from pathlib import Path
from app.config import Config
from app.skills.registry_client import GeapSkillRegistryClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_skills")


def main():
    repo_root = Path(__file__).resolve().parent.parent
    skills_dir = repo_root / "skills"

    if not skills_dir.exists():
        logger.error(f"Skills directory not found at {skills_dir}")
        sys.exit(1)

    print("=" * 80)
    print(" [GEAP SKILL REGISTRY] Synchronizing Skills to Google Cloud Agent Platform")
    print(f" Target Project:  {Config.PROJECT_ID}")
    print(f" Target Region:   {Config.LOCATION}")
    print("=" * 80)

    client = GeapSkillRegistryClient(
        project_id=Config.PROJECT_ID,
        location=Config.LOCATION,
    )

    skill_subdirs = sorted([d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
    print(f"Discovered {len(skill_subdirs)} skill packages in {skills_dir}:")
    for d in skill_subdirs:
        print(f"  - {d.name}")

    print("\nStarting registration & sync with GEAP Skill Registry...\n")
    registered_count = 0

    for d in skill_subdirs:
        try:
            res = client.register_or_update_skill(str(d), wait_for_completion=True)
            status = res["status"]
            skill_id = res["skill_id"]
            res_name = res["name"]
            print(f"  ✓ [{status}] {skill_id} -> {res_name}")
            registered_count += 1
        except Exception as e:
            print(f"  ✗ [FAILED] {d.name}: {e}")

    print("\n" + "=" * 80)
    print(f" [SUMMARY] {registered_count}/{len(skill_subdirs)} skills verified in GEAP Skill Registry.")
    print("=" * 80)

    # List current registry state
    print("\nCurrent GEAP Skill Registry fleet:")
    try:
        active_skills = client.list_skills()
        for s in active_skills:
            print(f"  • {s['skill_id']:<32} | {s['description'][:50]}...")
    except Exception as e:
        logger.warning(f"Could not list current registry fleet: {e}")


if __name__ == "__main__":
    main()
