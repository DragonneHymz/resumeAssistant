"""
Resume Storage Module

Handles JSON file-based storage with versioning for resume data.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import JSONResume, ResumeExtensions


class ResumeStorage:
    """File-based JSON storage for resumes with versioning."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize storage.
        
        Args:
            data_dir: Directory to store resume JSON files.
                      Defaults to ./data/resumes relative to package.
        """
        if data_dir is None:
            # Default to data/resumes in the project root
            package_dir = Path(__file__).parent.parent.parent
            data_dir = package_dir / "data" / "resumes"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_resume_path(self, resume_id: str) -> Path:
        """Get the file path for a resume."""
        return self.data_dir / f"{resume_id}.json"

    def _get_version_path(self, resume_id: str, version: int) -> Path:
        """Get the file path for a specific resume version."""
        versions_dir = self.data_dir / "versions" / resume_id
        versions_dir.mkdir(parents=True, exist_ok=True)
        return versions_dir / f"v{version}.json"

    def save(self, resume: JSONResume) -> str:
        """
        Save a resume to storage.
        
        Creates a new version backup before overwriting.
        
        Args:
            resume: The resume to save
            
        Returns:
            The resume ID
        """
        resume_id = resume.get_id()
        resume_path = self._get_resume_path(resume_id)
        
        # Update timestamp
        resume.extensions.updated_at = datetime.now().isoformat()
        
        # If resume exists, create version backup
        if resume_path.exists():
            # Load existing to get version number
            with open(resume_path, "r") as f:
                existing = json.load(f)
            
            # Determine version number
            versions_dir = self.data_dir / "versions" / resume_id
            if versions_dir.exists():
                existing_versions = list(versions_dir.glob("v*.json"))
                version = len(existing_versions) + 1
            else:
                version = 1
            
            # Save version backup
            version_path = self._get_version_path(resume_id, version)
            with open(version_path, "w") as f:
                json.dump(existing, f, indent=2)
        
        # Save current version
        data = resume.model_dump(mode="json")
        with open(resume_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return resume_id

    def load(self, resume_id: str) -> Optional[JSONResume]:
        """
        Load a resume by ID.
        
        Args:
            resume_id: The resume ID
            
        Returns:
            The resume, or None if not found
        """
        resume_path = self._get_resume_path(resume_id)
        
        if not resume_path.exists():
            return None
        
        with open(resume_path, "r") as f:
            data = json.load(f)
        
        return JSONResume.model_validate(data)

    def load_version(self, resume_id: str, version: int) -> Optional[JSONResume]:
        """
        Load a specific version of a resume.
        
        Args:
            resume_id: The resume ID
            version: The version number
            
        Returns:
            The resume version, or None if not found
        """
        version_path = self._get_version_path(resume_id, version)
        
        if not version_path.exists():
            return None
        
        with open(version_path, "r") as f:
            data = json.load(f)
        
        return JSONResume.model_validate(data)

    def delete(self, resume_id: str) -> bool:
        """
        Delete a resume and all its versions.
        
        Args:
            resume_id: The resume ID
            
        Returns:
            True if deleted, False if not found
        """
        resume_path = self._get_resume_path(resume_id)
        
        if not resume_path.exists():
            return False
        
        # Delete main file
        os.remove(resume_path)
        
        # Delete versions directory
        versions_dir = self.data_dir / "versions" / resume_id
        if versions_dir.exists():
            import shutil
            shutil.rmtree(versions_dir)
        
        return True

    def list_all(self) -> list[dict]:
        """
        List all stored resumes with summary info.
        
        Returns:
            List of resume summaries with id, name, industry, updated_at
        """
        summaries = []
        
        for resume_file in self.data_dir.glob("*.json"):
            try:
                with open(resume_file, "r") as f:
                    data = json.load(f)
                
                # Extract summary info
                basics = data.get("basics", {})
                extensions = data.get("extensions", {})
                
                summaries.append({
                    "id": extensions.get("id", resume_file.stem),
                    "name": basics.get("name", "Unknown"),
                    "email": basics.get("email", ""),
                    "label": basics.get("label", ""),
                    "industry": extensions.get("industry"),
                    "target_roles": extensions.get("target_roles", []),
                    "updated_at": extensions.get("updated_at", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Sort by updated_at descending
        summaries.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return summaries

    def get_versions(self, resume_id: str) -> list[int]:
        """
        Get available version numbers for a resume.
        
        Args:
            resume_id: The resume ID
            
        Returns:
            List of version numbers
        """
        versions_dir = self.data_dir / "versions" / resume_id
        
        if not versions_dir.exists():
            return []
        
        versions = []
        for version_file in versions_dir.glob("v*.json"):
            try:
                version_num = int(version_file.stem[1:])  # Remove 'v' prefix
                versions.append(version_num)
            except ValueError:
                continue
        
        return sorted(versions)

    def export_standard(self, resume_id: str) -> Optional[dict]:
        """
        Export resume as standard JSON Resume format (without extensions).
        
        Args:
            resume_id: The resume ID
            
        Returns:
            Standard JSON Resume dict, or None if not found
        """
        resume = self.load(resume_id)
        
        if resume is None:
            return None
        
        return resume.to_standard_json()


# Global storage instance
_storage: Optional[ResumeStorage] = None


def get_storage() -> ResumeStorage:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = ResumeStorage()
    return _storage
