"""
JSON Resume Schema Models (Pydantic)

Implements the JSON Resume open standard (https://jsonresume.org) v1.0.0
with internal extensions for ATS tracking.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# JSON Resume Standard Schema (v1.0.0)
# https://jsonresume.org/schema
# ═══════════════════════════════════════════════════════════════════════════════


class Location(BaseModel):
    """Physical location information."""

    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None


class Profile(BaseModel):
    """Social media or professional network profile."""

    network: str  # e.g., "LinkedIn", "GitHub", "Twitter"
    username: Optional[str] = None
    url: Optional[str] = None


class Basics(BaseModel):
    """Basic personal and contact information."""

    name: str
    label: Optional[str] = None  # e.g., "Software Engineer"
    image: Optional[str] = None  # URL to photo
    email: str
    phone: Optional[str] = None
    url: Optional[str] = None  # Personal website
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: list[Profile] = Field(default_factory=list)


class Work(BaseModel):
    """Work experience entry."""

    name: str  # Company name
    position: str  # Job title
    url: Optional[str] = None  # Company website
    startDate: str  # ISO format: YYYY-MM-DD
    endDate: Optional[str] = None  # None = "Present"
    summary: Optional[str] = None  # Role description
    highlights: list[str] = Field(default_factory=list)  # Achievement bullets


class Volunteer(BaseModel):
    """Volunteer experience entry."""

    organization: str
    position: str
    url: Optional[str] = None
    startDate: str
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """Education entry."""

    institution: str
    url: Optional[str] = None
    area: Optional[str] = None  # Field of study
    studyType: Optional[str] = None  # e.g., "Bachelor", "Master", "PhD"
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None  # GPA or grade
    courses: list[str] = Field(default_factory=list)


class Award(BaseModel):
    """Award or honor entry."""

    title: str
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class Certificate(BaseModel):
    """Professional certification entry."""

    name: str
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class Publication(BaseModel):
    """Publication entry."""

    name: str
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Skill(BaseModel):
    """Skill category with keywords."""

    name: str  # Category name, e.g., "Programming Languages"
    level: Optional[str] = None  # e.g., "Expert", "Intermediate"
    keywords: list[str] = Field(default_factory=list)  # Specific skills


class Language(BaseModel):
    """Language proficiency."""

    language: str
    fluency: Optional[str] = None  # e.g., "Native", "Professional", "Conversational"


class Interest(BaseModel):
    """Personal interest or hobby."""

    name: str
    keywords: list[str] = Field(default_factory=list)


class Reference(BaseModel):
    """Professional reference."""

    name: str
    reference: Optional[str] = None  # Testimonial text


class Project(BaseModel):
    """Personal or professional project."""

    name: str
    description: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    url: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    entity: Optional[str] = None  # Company/organization
    type: Optional[str] = None  # e.g., "application", "library", "research"


class Meta(BaseModel):
    """Resume metadata."""

    canonical: Optional[str] = None  # URL to latest version
    version: Optional[str] = None
    lastModified: Optional[str] = None
    theme: Optional[str] = None  # JSON Resume theme name


# ═══════════════════════════════════════════════════════════════════════════════
# Internal Extensions for ATS Tracking
# ═══════════════════════════════════════════════════════════════════════════════


class ATSScoreRecord(BaseModel):
    """Historical ATS score record."""

    timestamp: str
    job_description_hash: str
    score: float
    breakdown: dict


class ResumeExtensions(BaseModel):
    """Internal extensions for ATS optimization (not exported to standard JSON Resume)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    industry: Optional[str] = None  # User's target industry (passed to LLM)
    target_roles: list[str] = Field(default_factory=list)  # Target job titles
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    ats_score_history: list[ATSScoreRecord] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Complete JSON Resume with Extensions
# ═══════════════════════════════════════════════════════════════════════════════


class JSONResume(BaseModel):
    """
    Full JSON Resume schema with internal extensions.
    
    Follows the JSON Resume open standard v1.0.0 with additional fields
    for ATS tracking that are stripped when exporting.
    """

    # Standard JSON Resume fields
    basics: Basics
    work: list[Work] = Field(default_factory=list)
    volunteer: list[Volunteer] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    awards: list[Award] = Field(default_factory=list)
    certificates: list[Certificate] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    meta: Optional[Meta] = None

    # Internal extensions (stripped on export)
    extensions: ResumeExtensions = Field(default_factory=ResumeExtensions)

    def to_standard_json(self) -> dict:
        """Export as standard JSON Resume format (without internal extensions)."""
        data = self.model_dump(exclude={"extensions"})
        return data

    def get_id(self) -> str:
        """Get the internal resume ID."""
        return self.extensions.id

    def get_industry(self) -> Optional[str]:
        """Get the target industry."""
        return self.extensions.industry

    def set_industry(self, industry: str) -> None:
        """Set the target industry."""
        self.extensions.industry = industry
        self.extensions.updated_at = datetime.now().isoformat()

    def get_full_text(self) -> str:
        """Get all resume text for NLP analysis."""
        parts = []

        # Basics
        if self.basics.summary:
            parts.append(self.basics.summary)

        # Work experience
        for work in self.work:
            parts.append(f"{work.position} at {work.name}")
            if work.summary:
                parts.append(work.summary)
            parts.extend(work.highlights)

        # Education
        for edu in self.education:
            parts.append(f"{edu.studyType or ''} {edu.area or ''} at {edu.institution}")
            parts.extend(edu.courses)

        # Skills
        for skill in self.skills:
            parts.append(skill.name)
            parts.extend(skill.keywords)

        # Projects
        for project in self.projects:
            parts.append(project.name)
            if project.description:
                parts.append(project.description)
            parts.extend(project.highlights)
            parts.extend(project.keywords)

        # Certifications
        for cert in self.certificates:
            parts.append(f"{cert.name} from {cert.issuer or 'Unknown'}")

        return " ".join(filter(None, parts))
