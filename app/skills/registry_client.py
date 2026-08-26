"""Gemini Enterprise Agent Platform (GEAP) Skill Registry Client.

Grounded in Google Cloud GEAP & Agent Registry documentation:
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/skill-registry
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/skill-registry/create-manage
- https://docs.cloud.google.com/agent-registry/overview

Provides native client methods for publishing, listing, and retrieving skills
directly from Google Cloud Vertex AI / Agent Platform Skill Registry.
"""

import io
import os
import re
import yaml
import zipfile
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    import agentplatform
    from agentplatform._genai.types.common import CreateSkillConfig, RetrieveSkillsConfig
    HAS_AGENTPLATFORM = True
except ImportError:
    agentplatform = None
    CreateSkillConfig = None
    RetrieveSkillsConfig = None
    HAS_AGENTPLATFORM = False

from app.config import Config

logger = logging.getLogger(__name__)


class GeapSkillRegistryClient:
    """Client for Google Cloud Gemini Enterprise Agent Platform (GEAP) Skill Registry."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
    ):
        self.project_id = project_id or Config.PROJECT_ID
        loc = location or Config.LOCATION
        self.location = loc if loc and loc != "global" else "us-central1"
        if HAS_AGENTPLATFORM and agentplatform is not None:
            self._client = agentplatform.Client(
                project=self.project_id,
                location=self.location,
            )
        else:
            self._client = None

    def list_skills(self) -> List[Dict[str, Any]]:
        """Lists all skills registered in the GEAP Skill Registry."""
        try:
            skills_pager = self._client.skills.list()
            results = []
            for s in skills_pager:
                results.append({
                    "name": s.name,
                    "skill_id": s.name.split("/")[-1] if s.name else "",
                    "display_name": getattr(s, "display_name", ""),
                    "description": getattr(s, "description", ""),
                    "create_time": str(getattr(s, "create_time", "")),
                    "update_time": str(getattr(s, "update_time", "")),
                })
            return results
        except Exception as e:
            logger.error(f"Failed to list skills from GEAP Skill Registry: {e}")
            raise

    def retrieve_skills(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic search retrieval against the GEAP Skill Registry.
        
        Uses the official GEAP RetrieveSkills API endpoint to find relevant skills
        based on natural language intent.
        """
        try:
            config = RetrieveSkillsConfig()
            config.top_k = top_k
            response = self._client.skills.retrieve(
                query=query,
                config=config,
            )
            results = []
            for item in getattr(response, "retrieved_skills", []) or []:
                results.append({
                    "skill_name": getattr(item, "skill_name", ""),
                    "display_name": getattr(item, "display_name", ""),
                    "description": getattr(item, "description", ""),
                    "score": getattr(item, "score", 0.0),
                })
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve skills from GEAP Skill Registry: {e}")
            raise

    def register_or_update_skill(
        self,
        skill_dir: str,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """Validates, packages, and registers a local skill directory with GEAP Skill Registry.
        
        Args:
            skill_dir: Local path to the skill directory containing SKILL.md.
            wait_for_completion: Whether to block until the long-running operation finishes.
            
        Returns:
            Dictionary containing the registered skill's resource name and details.
        """
        skill_path = Path(skill_dir)
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")

        content = skill_md.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError(f"SKILL.md in {skill_dir} is missing valid YAML frontmatter")

        frontmatter = yaml.safe_load(match.group(1)) or {}
        skill_id = frontmatter.get("name", skill_path.name).lower().strip()
        display_name = skill_id
        description = frontmatter.get("description", f"Skill package for {skill_id}").strip()

        # GEAP Skill Registry Validation Constraints
        if len(skill_id) > 63 or not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", skill_id):
            raise ValueError(
                f"Invalid skill_id '{skill_id}': Must be 1-63 chars, lowercase/numbers/hyphens only, "
                "starting and ending with alphanumeric character."
            )
        if len(description) > 1024:
            description = description[:1021] + "..."

        logger.info(f"Registering skill '{skill_id}' to GEAP Skill Registry (Project: {self.project_id}, Region: {self.location})...")

        config = CreateSkillConfig(
            local_path=str(skill_path),
            wait_for_completion=wait_for_completion,
        )

        try:
            skill_result = self._client.skills.create(
                skill_id=skill_id,
                display_name=display_name,
                description=description,
                config=config,
            )
            return {
                "status": "SUCCESS",
                "skill_id": skill_id,
                "name": getattr(skill_result, "name", f"projects/{self.project_id}/locations/{self.location}/skills/{skill_id}"),
                "display_name": display_name,
                "description": description,
            }
        except Exception as e:
            err_msg = str(e)
            if "ALREADY_EXISTS" in err_msg or "409" in err_msg:
                logger.info(f"Skill '{skill_id}' already registered in GEAP Skill Registry. Resource exists.")
                return {
                    "status": "ALREADY_EXISTS",
                    "skill_id": skill_id,
                    "name": f"projects/{self.project_id}/locations/{self.location}/skills/{skill_id}",
                    "display_name": display_name,
                    "description": description,
                }
            logger.error(f"Error registering skill {skill_id} to GEAP: {e}")
            raise
