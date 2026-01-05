"""
Advanced ATS Optimization Engine

Enterprise-level ATS scoring and optimization with multi-option generation.
Uses spaCy for NLP and semantic analysis.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .models import JSONResume


@dataclass
class KeywordAnalysis:
    """Analysis of keywords from a job description."""

    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    technical_skills: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    education_requirements: list[str] = field(default_factory=list)
    experience_years: Optional[int] = None
    industry_keywords: list[str] = field(default_factory=list)


@dataclass
class ATSScore:
    """Comprehensive ATS score breakdown."""

    overall: float
    keyword_score: float
    semantic_score: float
    experience_score: float
    skills_score: float
    formatting_score: float
    
    matched_keywords: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_preferred: list[str] = field(default_factory=list)
    
    passes_threshold: bool = False  # True if score >= 75
    recommendations: list[str] = field(default_factory=list)


@dataclass
class BulletOption:
    """A single optimization option for a bullet point."""

    text: str
    keywords_added: list[str] = field(default_factory=list)
    style: str = ""  # e.g., "metrics-focused", "action-oriented", "technical"


@dataclass
class BulletOptions:
    """Multiple optimization options for user selection."""

    option_id: str
    original: str
    options: list[BulletOption] = field(default_factory=list)
    work_index: int = 0
    bullet_index: int = 0
    target_keywords: list[str] = field(default_factory=list)


@dataclass
class SummaryOptions:
    """Multiple summary options for user selection."""

    option_id: str
    current_summary: Optional[str]
    options: list[str] = field(default_factory=list)


@dataclass
class OptimizationItem:
    """An item to optimize in an interactive session."""

    item_type: str  # "bullet", "summary", "skills"
    section: str
    index: int
    sub_index: Optional[int] = None
    current_text: str = ""
    priority: str = "medium"  # critical, high, medium, low
    impact_score: float = 0.0


@dataclass
class OptimizationSession:
    """Interactive optimization session state."""

    session_id: str
    resume_id: str
    job_description: str
    current_score: float
    potential_score: float
    items: list[OptimizationItem] = field(default_factory=list)
    current_index: int = 0
    completed_items: list[int] = field(default_factory=list)


class EnterpriseATSOptimizer:
    """
    Advanced ATS optimization engine mimicking enterprise systems.
    
    Scoring methodology based on real ATS algorithms like Workday, Taleo, iCIMS.
    """

    # Score weights
    KEYWORD_WEIGHT = 0.40
    SEMANTIC_WEIGHT = 0.20
    EXPERIENCE_WEIGHT = 0.20
    SKILLS_WEIGHT = 0.15
    FORMATTING_WEIGHT = 0.05

    # Pass threshold
    PASS_THRESHOLD = 75.0

    def __init__(self):
        """Initialize optimizer with NLP components."""
        self._nlp = None
        self._sessions: dict[str, OptimizationSession] = {}
        self._option_cache: dict[str, dict] = {}

    @property
    def nlp(self):
        """Lazy load spaCy model."""
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_lg")
            except OSError:
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    raise RuntimeError(
                        "No spaCy model found. Run: python -m spacy download en_core_web_lg"
                    )
        return self._nlp

    # ═══════════════════════════════════════════════════════════════════════════
    # Keyword Extraction
    # ═══════════════════════════════════════════════════════════════════════════

    def extract_keywords(self, job_description: str) -> KeywordAnalysis:
        """
        Extract and categorize keywords from a job description.
        
        Args:
            job_description: The job description text
            
        Returns:
            KeywordAnalysis with categorized keywords
        """
        doc = self.nlp(job_description.lower())
        analysis = KeywordAnalysis()

        # Extract noun chunks and entities
        keywords = set()
        
        # Named entities (organizations, products, etc.)
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT", "GPE", "WORK_OF_ART"):
                keywords.add(ent.text)

        # Noun chunks (potential skills/technologies)
        for chunk in doc.noun_chunks:
            text = chunk.text.strip()
            if 1 < len(text) < 50:
                keywords.add(text)

        # Pattern-based extraction for common requirements
        text = job_description.lower()
        
        # Experience years
        exp_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", text)
        if exp_match:
            analysis.experience_years = int(exp_match.group(1))

        # Required vs preferred (look for section headers)
        required_section = re.search(
            r"(?:required|must\s+have|requirements?)[\s:]+(.+?)(?:preferred|nice\s+to\s+have|bonus|$)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        preferred_section = re.search(
            r"(?:preferred|nice\s+to\s+have|bonus|desired)[\s:]+(.+?)$",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        # Common technical skill patterns
        tech_patterns = [
            r"\b(python|javascript|typescript|java|c\+\+|c#|go|rust|ruby|php|swift|kotlin)\b",
            r"\b(react|angular|vue|node\.?js|django|flask|spring|rails)\b",
            r"\b(aws|azure|gcp|kubernetes|docker|terraform|jenkins|ci/cd)\b",
            r"\b(sql|postgresql|mysql|mongodb|redis|elasticsearch)\b",
            r"\b(git|github|gitlab|jira|confluence|agile|scrum)\b",
            r"\b(machine\s+learning|ml|ai|data\s+science|nlp|deep\s+learning)\b",
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            analysis.technical_skills.extend(matches)

        # Soft skills patterns
        soft_patterns = [
            r"\b(leadership|communication|teamwork|collaboration|problem.?solving)\b",
            r"\b(analytical|critical\s+thinking|attention\s+to\s+detail)\b",
            r"\b(self.?motivated|proactive|adaptable|flexible)\b",
        ]

        for pattern in soft_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            analysis.soft_skills.extend(matches)

        # Certification patterns
        cert_patterns = [
            r"\b(pmp|aws\s+certified|azure\s+certified|gcp\s+certified|cpa|cfa)\b",
            r"\b(scrum\s+master|csm|safe|itil|cissp|comptia)\b",
        ]

        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            analysis.certifications.extend(matches)

        # Deduplicate
        analysis.technical_skills = list(set(analysis.technical_skills))
        analysis.soft_skills = list(set(analysis.soft_skills))
        analysis.certifications = list(set(analysis.certifications))
        
        # Set required/preferred based on sections
        all_keywords = (
            analysis.technical_skills
            + analysis.soft_skills
            + analysis.certifications
        )
        
        if required_section:
            req_text = required_section.group(1).lower()
            analysis.required_skills = [k for k in all_keywords if k.lower() in req_text]
        else:
            # If no clear section, treat technical skills as required
            analysis.required_skills = analysis.technical_skills

        if preferred_section:
            pref_text = preferred_section.group(1).lower()
            analysis.preferred_skills = [k for k in all_keywords if k.lower() in pref_text]

        return analysis

    # ═══════════════════════════════════════════════════════════════════════════
    # Resume Scoring
    # ═══════════════════════════════════════════════════════════════════════════

    def score_resume(self, resume: JSONResume, job_description: str) -> ATSScore:
        """
        Score a resume against a job description using enterprise ATS methodology.
        
        Args:
            resume: The resume to score
            job_description: The target job description
            
        Returns:
            Detailed ATS score breakdown
        """
        analysis = self.extract_keywords(job_description)
        resume_text = resume.get_full_text().lower()
        resume_doc = self.nlp(resume_text)
        job_doc = self.nlp(job_description.lower())

        # 1. Keyword Match Score (40%)
        matched = []
        missing_required = []
        missing_preferred = []

        for keyword in analysis.required_skills:
            if keyword.lower() in resume_text:
                matched.append(keyword)
            else:
                missing_required.append(keyword)

        for keyword in analysis.preferred_skills:
            if keyword.lower() in resume_text:
                matched.append(keyword)
            else:
                missing_preferred.append(keyword)

        total_keywords = len(analysis.required_skills) + len(analysis.preferred_skills)
        if total_keywords > 0:
            # Required keywords are worth 2x
            required_matched = len([k for k in matched if k in analysis.required_skills])
            preferred_matched = len([k for k in matched if k in analysis.preferred_skills])
            
            required_total = len(analysis.required_skills)
            preferred_total = len(analysis.preferred_skills)
            
            if required_total + preferred_total > 0:
                keyword_score = (
                    (required_matched * 2 + preferred_matched)
                    / (required_total * 2 + preferred_total)
                    * 100
                )
            else:
                keyword_score = 50.0
        else:
            keyword_score = 50.0

        # 2. Semantic Similarity Score (20%)
        semantic_score = resume_doc.similarity(job_doc) * 100

        # 3. Experience Match Score (20%)
        experience_score = 70.0  # Default
        if analysis.experience_years:
            # Count years from resume work experience
            total_years = 0
            for work in resume.work:
                # Simple heuristic based on date ranges
                if work.startDate and work.endDate:
                    try:
                        start = int(work.startDate[:4])
                        end = int(work.endDate[:4]) if work.endDate.lower() != "present" else datetime.now().year
                        total_years += max(0, end - start)
                    except (ValueError, IndexError):
                        pass
                elif work.startDate:
                    # Current position
                    try:
                        start = int(work.startDate[:4])
                        total_years += datetime.now().year - start
                    except (ValueError, IndexError):
                        pass

            if total_years >= analysis.experience_years:
                experience_score = 100.0
            elif total_years >= analysis.experience_years * 0.7:
                experience_score = 80.0
            elif total_years >= analysis.experience_years * 0.5:
                experience_score = 60.0
            else:
                experience_score = 40.0

        # 4. Skills Coverage Score (15%)
        resume_skills = set()
        for skill in resume.skills:
            resume_skills.add(skill.name.lower())
            resume_skills.update(k.lower() for k in skill.keywords)

        required_skills = set(k.lower() for k in analysis.technical_skills)
        if required_skills:
            skills_covered = len(resume_skills.intersection(required_skills))
            skills_score = (skills_covered / len(required_skills)) * 100
        else:
            skills_score = 70.0

        # 5. Formatting Score (5%)
        formatting_score = 100.0
        issues = []
        
        # Check for common issues
        if not resume.basics.email:
            formatting_score -= 20
            issues.append("Missing email")
        if not resume.basics.phone:
            formatting_score -= 10
            issues.append("Missing phone")
        if not resume.basics.summary:
            formatting_score -= 15
            issues.append("Missing summary")
        if len(resume.work) == 0:
            formatting_score -= 30
            issues.append("No work experience")
        if len(resume.skills) == 0:
            formatting_score -= 15
            issues.append("No skills section")

        formatting_score = max(0, formatting_score)

        # Calculate overall score
        overall = (
            keyword_score * self.KEYWORD_WEIGHT
            + semantic_score * self.SEMANTIC_WEIGHT
            + experience_score * self.EXPERIENCE_WEIGHT
            + skills_score * self.SKILLS_WEIGHT
            + formatting_score * self.FORMATTING_WEIGHT
        )

        # Generate recommendations
        recommendations = []
        if missing_required:
            recommendations.append(
                f"Add missing required keywords: {', '.join(missing_required[:5])}"
            )
        if missing_preferred:
            recommendations.append(
                f"Consider adding: {', '.join(missing_preferred[:5])}"
            )
        if experience_score < 80:
            recommendations.append("Highlight relevant experience more prominently")
        if skills_score < 70:
            recommendations.append("Expand skills section with more relevant technologies")
        if issues:
            recommendations.append(f"Fix formatting issues: {', '.join(issues)}")

        return ATSScore(
            overall=round(overall, 1),
            keyword_score=round(keyword_score, 1),
            semantic_score=round(semantic_score, 1),
            experience_score=round(experience_score, 1),
            skills_score=round(skills_score, 1),
            formatting_score=round(formatting_score, 1),
            matched_keywords=matched,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            passes_threshold=overall >= self.PASS_THRESHOLD,
            recommendations=recommendations,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Multi-Option Optimization
    # ═══════════════════════════════════════════════════════════════════════════

    def generate_bullet_options(
        self,
        original: str,
        target_keywords: list[str],
        industry: Optional[str] = None,
        work_index: int = 0,
        bullet_index: int = 0,
        num_options: int = 3,
    ) -> BulletOptions:
        """
        Generate multiple rewrite options for a bullet point.
        
        Note: This generates placeholder options. The actual rewriting
        should be done by the LLM when presenting to the user.
        
        Args:
            original: The original bullet text
            target_keywords: Keywords to incorporate
            industry: Target industry for context
            work_index: Work experience index
            bullet_index: Bullet point index
            num_options: Number of options to generate
            
        Returns:
            BulletOptions with option_id for selection/regeneration
        """
        option_id = str(uuid4())
        
        options = BulletOptions(
            option_id=option_id,
            original=original,
            work_index=work_index,
            bullet_index=bullet_index,
            target_keywords=target_keywords,
        )

        # Store in cache for regeneration
        self._option_cache[option_id] = {
            "type": "bullet",
            "original": original,
            "target_keywords": target_keywords,
            "industry": industry,
            "work_index": work_index,
            "bullet_index": bullet_index,
            "created_at": datetime.now().isoformat(),
        }

        # Generate placeholder options
        # In actual use, the LLM will generate the real options
        styles = [
            ("metrics-focused", "Focus on quantifiable results and metrics"),
            ("action-oriented", "Lead with strong action verbs"),
            ("technical", "Emphasize technical skills and tools"),
        ]

        for i, (style, _) in enumerate(styles[:num_options]):
            options.options.append(
                BulletOption(
                    text=f"[LLM will generate {style} version incorporating: {', '.join(target_keywords[:3])}]",
                    keywords_added=target_keywords[:3],
                    style=style,
                )
            )

        return options

    def generate_summary_options(
        self,
        resume: JSONResume,
        job_description: str,
        num_options: int = 3,
    ) -> SummaryOptions:
        """
        Generate multiple professional summary options.
        
        Args:
            resume: The resume being optimized
            job_description: Target job description
            num_options: Number of options to generate
            
        Returns:
            SummaryOptions with option_id for selection/regeneration
        """
        option_id = str(uuid4())
        
        # Store in cache
        self._option_cache[option_id] = {
            "type": "summary",
            "resume_id": resume.get_id(),
            "job_description_hash": hashlib.md5(job_description.encode()).hexdigest()[:8],
            "created_at": datetime.now().isoformat(),
        }

        return SummaryOptions(
            option_id=option_id,
            current_summary=resume.basics.summary,
            options=[
                "[LLM will generate concise summary option]",
                "[LLM will generate detailed summary option]",
                "[LLM will generate achievement-focused summary option]",
            ][:num_options],
        )

    def regenerate_options(
        self,
        option_id: str,
        feedback: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get context for regenerating options based on user feedback.
        
        Args:
            option_id: The option ID from previous generation
            feedback: User feedback for targeted regeneration
            
        Returns:
            Context dict for the LLM to generate new options
        """
        if option_id not in self._option_cache:
            return None

        cached = self._option_cache[option_id]
        cached["feedback"] = feedback
        cached["regeneration_requested_at"] = datetime.now().isoformat()

        return cached

    def apply_selection(
        self,
        resume: JSONResume,
        option_id: str,
        selected_text: str,
    ) -> bool:
        """
        Apply a selected option to the resume.
        
        Args:
            resume: The resume to update
            option_id: The option ID
            selected_text: The text of the selected option
            
        Returns:
            True if applied successfully
        """
        if option_id not in self._option_cache:
            return False

        cached = self._option_cache[option_id]

        if cached["type"] == "bullet":
            work_index = cached["work_index"]
            bullet_index = cached["bullet_index"]
            
            if work_index < len(resume.work):
                work = resume.work[work_index]
                if bullet_index < len(work.highlights):
                    work.highlights[bullet_index] = selected_text
                    return True

        elif cached["type"] == "summary":
            resume.basics.summary = selected_text
            return True

        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # Interactive Optimization Sessions
    # ═══════════════════════════════════════════════════════════════════════════

    def start_interactive_session(
        self,
        resume: JSONResume,
        job_description: str,
    ) -> OptimizationSession:
        """
        Start an interactive optimization session.
        
        Args:
            resume: The resume to optimize
            job_description: Target job description
            
        Returns:
            OptimizationSession with prioritized items
        """
        session_id = str(uuid4())
        
        # Score the resume
        score = self.score_resume(resume, job_description)
        analysis = self.extract_keywords(job_description)
        
        # Build list of items to optimize
        items = []
        
        # Add summary if missing or could be improved
        if not resume.basics.summary or score.semantic_score < 70:
            items.append(
                OptimizationItem(
                    item_type="summary",
                    section="basics",
                    index=0,
                    current_text=resume.basics.summary or "",
                    priority="high",
                    impact_score=15.0,
                )
            )

        # Add work experience bullets that could incorporate missing keywords
        for wi, work in enumerate(resume.work):
            for bi, bullet in enumerate(work.highlights):
                # Check if bullet could benefit from keywords
                bullet_lower = bullet.lower()
                applicable_keywords = [
                    kw for kw in score.missing_required + score.missing_preferred
                    if kw.lower() not in bullet_lower
                ]
                
                if applicable_keywords:
                    items.append(
                        OptimizationItem(
                            item_type="bullet",
                            section="work",
                            index=wi,
                            sub_index=bi,
                            current_text=bullet,
                            priority="high" if any(kw in score.missing_required for kw in applicable_keywords) else "medium",
                            impact_score=5.0 * len(applicable_keywords),
                        )
                    )

        # Sort by impact score
        items.sort(key=lambda x: x.impact_score, reverse=True)
        
        # Limit to top 20 items
        items = items[:20]

        # Calculate potential score
        potential_improvement = sum(item.impact_score for item in items) * 0.5
        potential_score = min(100, score.overall + potential_improvement)

        session = OptimizationSession(
            session_id=session_id,
            resume_id=resume.get_id(),
            job_description=job_description,
            current_score=score.overall,
            potential_score=round(potential_score, 1),
            items=items,
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[OptimizationSession]:
        """Get an optimization session by ID."""
        return self._sessions.get(session_id)

    def get_next_item(
        self,
        session_id: str,
        skip_current: bool = False,
    ) -> Optional[OptimizationItem]:
        """
        Get the next item to optimize in a session.
        
        Args:
            session_id: The session ID
            skip_current: If True, skip current item without changes
            
        Returns:
            Next OptimizationItem or None if session complete
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if skip_current:
            session.current_index += 1

        while session.current_index < len(session.items):
            if session.current_index not in session.completed_items:
                return session.items[session.current_index]
            session.current_index += 1

        return None

    def complete_item(self, session_id: str) -> None:
        """Mark current item as completed."""
        session = self._sessions.get(session_id)
        if session:
            session.completed_items.append(session.current_index)
            session.current_index += 1


# Global optimizer instance
_optimizer: Optional[EnterpriseATSOptimizer] = None


def get_optimizer() -> EnterpriseATSOptimizer:
    """Get the global optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = EnterpriseATSOptimizer()
    return _optimizer
