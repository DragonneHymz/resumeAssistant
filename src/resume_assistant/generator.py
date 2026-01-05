"""
Resume Generator Module

Generates PDF resumes from JSON Resume data using HTML templates.
Uses Jinja2 for templating and WeasyPrint for PDF conversion.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from .models import JSONResume


class ResumeGenerator:
    """Generates PDF resumes from templates."""

    TEMPLATES = ["modern", "classic", "executive"]

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize generator.
        
        Args:
            output_dir: Directory to save generated PDFs.
                        Defaults to ./output relative to package.
        """
        # Template directory
        package_dir = Path(__file__).parent
        self.templates_dir = package_dir / "templates"
        
        # Output directory
        if output_dir is None:
            project_dir = package_dir.parent.parent
            output_dir = project_dir / "output"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date

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

    def list_templates(self) -> list[dict]:
        """
        List available templates with descriptions.
        
        Returns:
            List of template info dicts
        """
        return [
            {
                "id": "modern",
                "name": "Modern",
                "description": "Clean, contemporary design with color accents. Two-column layout. Best for tech and creative roles.",
                "features": ["Two-column layout", "Skills sidebar", "Sans-serif fonts", "Color accents"],
            },
            {
                "id": "classic",
                "name": "Classic",
                "description": "Traditional single-column layout. Conservative styling. Maximum ATS compatibility.",
                "features": ["Single-column", "Serif fonts", "Black and white", "Traditional headers"],
            },
            {
                "id": "executive",
                "name": "Executive",
                "description": "Premium design with elegant typography. Strategic whitespace. Ideal for senior roles.",
                "features": ["Premium styling", "Elegant fonts", "Strategic whitespace", "Professional borders"],
            },
        ]

    def render_html(self, resume: JSONResume, template: str = "modern") -> str:
        """
        Render resume to HTML using selected template.
        
        Args:
            resume: The resume data
            template: Template ID (modern, classic, executive)
            
        Returns:
            HTML string
        """
        if template not in self.TEMPLATES:
            template = "modern"

        template_file = f"{template}.html"
        
        try:
            tmpl = self.env.get_template(template_file)
        except Exception:
            # Fallback to basic rendering if template doesn't exist yet
            return self._render_basic(resume)

        # Prepare template context
        context = {
            "resume": resume,
            "basics": resume.basics,
            "work": resume.work,
            "education": resume.education,
            "skills": resume.skills,
            "projects": resume.projects,
            "certificates": resume.certificates,
            "languages": resume.languages,
            "now": datetime.now(),
        }

        return tmpl.render(**context)

    def _render_basic(self, resume: JSONResume) -> str:
        """Render a basic HTML resume without template file."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            '<meta charset="utf-8">',
            "<style>",
            "body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; }",
            "h1 { color: #333; margin-bottom: 5px; }",
            "h2 { color: #555; border-bottom: 1px solid #ddd; padding-bottom: 5px; }",
            "h3 { color: #666; margin-bottom: 5px; }",
            ".contact { color: #666; margin-bottom: 20px; }",
            ".section { margin-bottom: 25px; }",
            ".entry { margin-bottom: 15px; }",
            ".date { color: #888; font-size: 0.9em; }",
            ".skills { display: flex; flex-wrap: wrap; gap: 10px; }",
            ".skill-category { background: #f5f5f5; padding: 10px; border-radius: 5px; }",
            ".skill-keywords { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; }",
            ".skill-keyword { background: #e0e0e0; padding: 2px 8px; border-radius: 3px; font-size: 0.9em; }",
            "ul { margin-top: 5px; padding-left: 20px; }",
            "li { margin-bottom: 3px; }",
            "</style>",
            "</head><body>",
        ]

        # Header
        html_parts.append(f"<h1>{resume.basics.name}</h1>")
        
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
        
        if contact_parts:
            html_parts.append(f'<div class="contact">{" | ".join(contact_parts)}</div>')

        if resume.basics.summary:
            html_parts.append(f"<p>{resume.basics.summary}</p>")

        # Work Experience
        if resume.work:
            html_parts.append('<div class="section">')
            html_parts.append("<h2>Experience</h2>")
            for work in resume.work:
                html_parts.append('<div class="entry">')
                html_parts.append(f"<h3>{work.position}</h3>")
                date_range = f"{self._format_date(work.startDate)} - {self._format_date(work.endDate)}"
                html_parts.append(f'<div><strong>{work.name}</strong> | <span class="date">{date_range}</span></div>')
                if work.highlights:
                    html_parts.append("<ul>")
                    for highlight in work.highlights:
                        html_parts.append(f"<li>{highlight}</li>")
                    html_parts.append("</ul>")
                html_parts.append("</div>")
            html_parts.append("</div>")

        # Education
        if resume.education:
            html_parts.append('<div class="section">')
            html_parts.append("<h2>Education</h2>")
            for edu in resume.education:
                html_parts.append('<div class="entry">')
                degree = f"{edu.studyType or ''} {edu.area or ''}".strip()
                if degree:
                    html_parts.append(f"<h3>{degree}</h3>")
                html_parts.append(f"<div><strong>{edu.institution}</strong></div>")
                if edu.endDate:
                    html_parts.append(f'<div class="date">{self._format_date(edu.endDate)}</div>')
                html_parts.append("</div>")
            html_parts.append("</div>")

        # Skills
        if resume.skills:
            html_parts.append('<div class="section">')
            html_parts.append("<h2>Skills</h2>")
            html_parts.append('<div class="skills">')
            for skill in resume.skills:
                html_parts.append('<div class="skill-category">')
                html_parts.append(f"<strong>{skill.name}</strong>")
                if skill.keywords:
                    html_parts.append('<div class="skill-keywords">')
                    for kw in skill.keywords:
                        html_parts.append(f'<span class="skill-keyword">{kw}</span>')
                    html_parts.append("</div>")
                html_parts.append("</div>")
            html_parts.append("</div>")
            html_parts.append("</div>")

        # Projects
        if resume.projects:
            html_parts.append('<div class="section">')
            html_parts.append("<h2>Projects</h2>")
            for project in resume.projects:
                html_parts.append('<div class="entry">')
                html_parts.append(f"<h3>{project.name}</h3>")
                if project.description:
                    html_parts.append(f"<p>{project.description}</p>")
                if project.highlights:
                    html_parts.append("<ul>")
                    for highlight in project.highlights:
                        html_parts.append(f"<li>{highlight}</li>")
                    html_parts.append("</ul>")
                html_parts.append("</div>")
            html_parts.append("</div>")

        # Certifications
        if resume.certificates:
            html_parts.append('<div class="section">')
            html_parts.append("<h2>Certifications</h2>")
            for cert in resume.certificates:
                html_parts.append('<div class="entry">')
                html_parts.append(f"<strong>{cert.name}</strong>")
                if cert.issuer:
                    html_parts.append(f" - {cert.issuer}")
                if cert.date:
                    html_parts.append(f' <span class="date">({self._format_date(cert.date)})</span>')
                html_parts.append("</div>")
            html_parts.append("</div>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def generate_pdf(
        self,
        resume: JSONResume,
        template: str = "modern",
        filename: Optional[str] = None,
    ) -> str:
        """
        Generate a PDF resume.
        
        Args:
            resume: The resume data
            template: Template ID (modern, classic, executive)
            filename: Output filename (without extension)
            
        Returns:
            Absolute path to generated PDF
        """
        from weasyprint import HTML

        # Generate HTML
        html_content = self.render_html(resume, template)

        # Determine output path
        if filename is None:
            safe_name = resume.basics.name.replace(" ", "_").lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{template}_{timestamp}"

        output_path = self.output_dir / f"{filename}.pdf"

        # Generate PDF
        html = HTML(string=html_content, base_url=str(self.templates_dir))
        html.write_pdf(str(output_path))

        return str(output_path.absolute())


# Global generator instance
_generator: Optional[ResumeGenerator] = None


def get_generator() -> ResumeGenerator:
    """Get the global generator instance."""
    global _generator
    if _generator is None:
        _generator = ResumeGenerator()
    return _generator
