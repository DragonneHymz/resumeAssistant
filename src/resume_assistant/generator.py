"""
Resume Generator Module

Generates plain text resumes from JSON Resume data for easy copy-paste.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import JSONResume


class ResumeGenerator:
    """Generates text resumes for easy copy-paste."""

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize generator.
        
        Args:
            output_dir: Directory to save generated files.
                        Defaults to ./output relative to package.
        """
        # Output directory
        package_dir = Path(__file__).parent
        if output_dir is None:
            project_dir = package_dir.parent.parent
            output_dir = project_dir / "output"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _format_date(date_str: Optional[str]) -> str:
        """Format a date string for display."""
        if not date_str:
            return "Present"
        
        if date_str.lower() == "present":
            return "Present"
        
        try:
            # Try to parse ISO format
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date.strftime("%B %Y")
        except ValueError:
            # Return as-is if can't parse
            return date_str

    def generate_text(
        self,
        resume: JSONResume,
        filename: Optional[str] = None,
    ) -> str:
        """
        Generate a plain text resume for easy copy-paste.
        
        Args:
            resume: The resume data
            filename: Output filename (without extension)
            
        Returns:
            Absolute path to generated text file
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append(resume.basics.name.upper().center(80))
        lines.append("=" * 80)
        lines.append("")
        
        # Contact info
        contact_parts = []
        if resume.basics.email:
            contact_parts.append(resume.basics.email)
        if resume.basics.phone:
            contact_parts.append(resume.basics.phone)
        if resume.basics.location:
            loc = resume.basics.location
            loc_str = ", ".join(filter(None, [loc.city, loc.region]))
            if loc_str:
                contact_parts.append(loc_str)
        if resume.basics.url:
            contact_parts.append(resume.basics.url)
        
        if contact_parts:
            lines.append(" | ".join(contact_parts))
            lines.append("")

        # Professional Summary
        if resume.basics.summary:
            lines.append("-" * 80)
            lines.append("PROFESSIONAL SUMMARY")
            lines.append("-" * 80)
            lines.append("")
            # Wrap summary text nicely
            lines.append(resume.basics.summary)
            lines.append("")

        # Work Experience
        if resume.work:
            lines.append("-" * 80)
            lines.append("WORK EXPERIENCE")
            lines.append("-" * 80)
            lines.append("")
            
            for work in resume.work:
                # Position title
                lines.append(work.position.upper())
                
                # Company and date range
                date_range = f"{self._format_date(work.startDate)} - {self._format_date(work.endDate)}"
                lines.append(f"{work.name} | {date_range}")
                
                # Highlights as bullet points
                if work.highlights:
                    for highlight in work.highlights:
                        lines.append(f"  • {highlight}")
                
                lines.append("")

        # Education
        if resume.education:
            lines.append("-" * 80)
            lines.append("EDUCATION")
            lines.append("-" * 80)
            lines.append("")
            
            for edu in resume.education:
                # Degree
                degree_parts = []
                if edu.studyType:
                    degree_parts.append(edu.studyType)
                if edu.area:
                    degree_parts.append(f"in {edu.area}")
                
                if degree_parts:
                    lines.append(" ".join(degree_parts).upper())
                
                # Institution and date
                date_str = ""
                if edu.endDate:
                    date_str = f" | Graduated {self._format_date(edu.endDate)}"
                elif edu.startDate:
                    date_str = f" | {self._format_date(edu.startDate)} - Present"
                
                lines.append(f"{edu.institution}{date_str}")
                
                # GPA/Score
                if edu.score:
                    lines.append(f"  GPA: {edu.score}")
                
                # Relevant courses
                if edu.courses:
                    lines.append(f"  Relevant Coursework: {', '.join(edu.courses)}")
                
                lines.append("")

        # Skills
        if resume.skills:
            lines.append("-" * 80)
            lines.append("SKILLS")
            lines.append("-" * 80)
            lines.append("")
            
            for skill in resume.skills:
                if skill.keywords:
                    lines.append(f"{skill.name}: {', '.join(skill.keywords)}")
            
            lines.append("")

        # Projects
        if resume.projects:
            lines.append("-" * 80)
            lines.append("PROJECTS")
            lines.append("-" * 80)
            lines.append("")
            
            for project in resume.projects:
                lines.append(project.name.upper())
                
                if project.description:
                    lines.append(f"  {project.description}")
                
                if project.keywords:
                    lines.append(f"  Technologies: {', '.join(project.keywords)}")
                
                if project.highlights:
                    for highlight in project.highlights:
                        lines.append(f"  • {highlight}")
                
                if project.url:
                    lines.append(f"  Link: {project.url}")
                
                lines.append("")

        # Certifications
        if resume.certificates:
            lines.append("-" * 80)
            lines.append("CERTIFICATIONS")
            lines.append("-" * 80)
            lines.append("")
            
            for cert in resume.certificates:
                cert_line = f"  • {cert.name}"
                if cert.issuer:
                    cert_line += f" - {cert.issuer}"
                if cert.date:
                    cert_line += f" ({self._format_date(cert.date)})"
                lines.append(cert_line)
            
            lines.append("")

        # Languages
        if resume.languages:
            lines.append("-" * 80)
            lines.append("LANGUAGES")
            lines.append("-" * 80)
            lines.append("")
            
            lang_parts = []
            for lang in resume.languages:
                if lang.fluency:
                    lang_parts.append(f"{lang.language} ({lang.fluency})")
                else:
                    lang_parts.append(lang.language)
            
            lines.append(", ".join(lang_parts))
            lines.append("")

        # Interests
        if resume.interests:
            lines.append("-" * 80)
            lines.append("INTERESTS")
            lines.append("-" * 80)
            lines.append("")
            
            for interest in resume.interests:
                if interest.keywords:
                    lines.append(f"{interest.name}: {', '.join(interest.keywords)}")
                else:
                    lines.append(interest.name)
            
            lines.append("")

        # Join all lines
        content = "\n".join(lines)

        # Determine output path
        if filename is None:
            safe_name = resume.basics.name.replace(" ", "_").lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_resume_{timestamp}"

        output_path = self.output_dir / f"{filename}.txt"

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(output_path.absolute())


# Global generator instance
_generator: Optional[ResumeGenerator] = None


def get_generator() -> ResumeGenerator:
    """Get the global generator instance."""
    global _generator
    if _generator is None:
        _generator = ResumeGenerator()
    return _generator
