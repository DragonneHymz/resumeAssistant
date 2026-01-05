"""
PDF Resume Parser & URL Content Fetcher

Handles importing existing resumes from PDF and fetching job descriptions from URLs.
"""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx


class ContentFetcher:
    """Fetches content from URLs for job descriptions."""

    # User agent for web requests
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Job board specific extractors
    JOB_BOARD_PATTERNS = {
        "linkedin.com": "_extract_linkedin",
        "indeed.com": "_extract_indeed",
        "greenhouse.io": "_extract_greenhouse",
        "lever.co": "_extract_lever",
        "myworkdayjobs.com": "_extract_workday",
    }

    def is_url(self, text: str) -> bool:
        """Check if the input is a URL."""
        if not text:
            return False
        
        try:
            result = urlparse(text.strip())
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    async def fetch_url(self, url: str) -> dict:
        """
        Fetch and extract job description from a URL.
        
        Args:
            url: The job posting URL
            
        Returns:
            dict with 'source', 'content', 'title', and 'company'
        """
        async with httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        # Determine which extractor to use
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        for pattern, method_name in self.JOB_BOARD_PATTERNS.items():
            if pattern in domain:
                method = getattr(self, method_name)
                return method(html, url)
        
        # Generic extraction
        return self._extract_generic(html, url)

    def _extract_generic(self, html: str, url: str) -> dict:
        """Generic HTML content extraction."""
        # Remove script and style tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        # Try to find the main content (heuristic: longest paragraph-like sections)
        paragraphs = [p.strip() for p in text.split(".") if len(p.strip()) > 50]
        content = ". ".join(paragraphs)
        
        return {
            "source": url,
            "title": title,
            "company": "",
            "content": content[:10000],  # Limit content length
        }

    def _extract_linkedin(self, html: str, url: str) -> dict:
        """Extract job description from LinkedIn."""
        # LinkedIn uses specific class names for job content
        content = self._extract_generic(html, url)
        content["source_type"] = "linkedin"
        return content

    def _extract_indeed(self, html: str, url: str) -> dict:
        """Extract job description from Indeed."""
        content = self._extract_generic(html, url)
        content["source_type"] = "indeed"
        return content

    def _extract_greenhouse(self, html: str, url: str) -> dict:
        """Extract job description from Greenhouse."""
        content = self._extract_generic(html, url)
        content["source_type"] = "greenhouse"
        return content

    def _extract_lever(self, html: str, url: str) -> dict:
        """Extract job description from Lever."""
        content = self._extract_generic(html, url)
        content["source_type"] = "lever"
        return content

    def _extract_workday(self, html: str, url: str) -> dict:
        """Extract job description from Workday."""
        content = self._extract_generic(html, url)
        content["source_type"] = "workday"
        return content


class ResumePDFParser:
    """
    Parses existing PDF resumes to extract structured JSON Resume data.
    
    Uses pdfplumber for text extraction and spaCy for NER.
    """

    def __init__(self):
        """Initialize parser with spaCy model."""
        self._nlp = None

    @property
    def nlp(self):
        """Lazy load spaCy model."""
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_lg")
            except OSError:
                # Fallback to smaller model
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    raise RuntimeError(
                        "No spaCy model found. Run: python -m spacy download en_core_web_lg"
                    )
        return self._nlp

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        import pdfplumber

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    def parse_pdf(self, pdf_path: str) -> dict:
        """
        Parse a PDF resume and extract structured data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            dict matching JSON Resume structure
        """
        text = self.extract_text(pdf_path)
        doc = self.nlp(text)

        # Extract components
        basics = self._extract_basics(text, doc)
        work = self._extract_work(text)
        education = self._extract_education(text)
        skills = self._extract_skills(text)

        return {
            "basics": basics,
            "work": work,
            "education": education,
            "skills": skills,
            "volunteer": [],
            "awards": [],
            "certificates": [],
            "publications": [],
            "languages": [],
            "interests": [],
            "references": [],
            "projects": [],
            "_raw_text": text,
        }

    def _extract_basics(self, text: str, doc) -> dict:
        """Extract basic contact information using NER and regex."""
        basics = {
            "name": "",
            "email": "",
            "phone": None,
            "url": None,
            "location": None,
            "profiles": [],
        }

        # Extract email using regex
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        email_match = re.search(email_pattern, text)
        if email_match:
            basics["email"] = email_match.group()

        # Extract phone using regex
        phone_patterns = [
            r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                basics["phone"] = phone_match.group()
                break

        # Extract LinkedIn URL
        linkedin_pattern = r"linkedin\.com/in/[\w-]+"
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            basics["profiles"].append({
                "network": "LinkedIn",
                "url": f"https://www.{linkedin_match.group()}",
            })

        # Extract GitHub URL
        github_pattern = r"github\.com/[\w-]+"
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        if github_match:
            basics["profiles"].append({
                "network": "GitHub",
                "url": f"https://www.{github_match.group()}",
            })

        # Extract name from NER (first PERSON entity)
        for ent in doc.ents:
            if ent.label_ == "PERSON" and not basics["name"]:
                basics["name"] = ent.text
                break

        # If no name found via NER, use first line heuristic
        if not basics["name"]:
            first_line = text.split("\n")[0].strip()
            # If first line is short and doesn't look like a section header
            if len(first_line) < 50 and not any(
                header in first_line.lower()
                for header in ["experience", "education", "skills", "summary"]
            ):
                basics["name"] = first_line

        return basics

    def _extract_work(self, text: str) -> list[dict]:
        """Extract work experience entries."""
        work = []
        
        # Look for experience section
        exp_patterns = [
            r"(?:work\s+)?experience",
            r"employment\s+history",
            r"professional\s+experience",
        ]
        
        exp_section = None
        for pattern in exp_patterns:
            match = re.search(
                rf"{pattern}\s*\n(.*?)(?=\n(?:education|skills|projects|certifications|$))",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if match:
                exp_section = match.group(1)
                break
        
        if not exp_section:
            return work
        
        # Date pattern for work entries
        date_pattern = r"(\w+\.?\s+\d{4}|\d{4})\s*[-–—]\s*(\w+\.?\s+\d{4}|\d{4}|present|current)"
        
        # Split by date patterns to identify entries
        entries = re.split(date_pattern, exp_section, flags=re.IGNORECASE)
        
        # This is a simplified extraction - in production would need more robust parsing
        current_entry = None
        for i, entry in enumerate(entries):
            entry = entry.strip()
            if not entry:
                continue
            
            # Check if this looks like a date
            if re.match(r"^\w+\.?\s+\d{4}$|^\d{4}$|^present$|^current$", entry, re.IGNORECASE):
                continue
            
            # Try to extract company and position
            lines = [l.strip() for l in entry.split("\n") if l.strip()]
            if lines:
                work.append({
                    "name": lines[0] if len(lines) > 0 else "Unknown Company",
                    "position": lines[1] if len(lines) > 1 else "Unknown Position",
                    "startDate": "",
                    "endDate": None,
                    "highlights": lines[2:] if len(lines) > 2 else [],
                })
        
        return work[:10]  # Limit to 10 entries

    def _extract_education(self, text: str) -> list[dict]:
        """Extract education entries."""
        education = []
        
        # Look for education section
        match = re.search(
            r"education\s*\n(.*?)(?=\n(?:experience|skills|projects|certifications|$))",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        
        if not match:
            return education
        
        edu_section = match.group(1)
        
        # Look for degree patterns
        degree_patterns = [
            r"(bachelor|master|ph\.?d|associate|b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?b\.?a\.?)",
        ]
        
        lines = [l.strip() for l in edu_section.split("\n") if l.strip()]
        
        current_edu = None
        for line in lines:
            # Check if this line contains a degree
            has_degree = any(
                re.search(pattern, line, re.IGNORECASE)
                for pattern in degree_patterns
            )
            
            if has_degree or (current_edu is None and len(line) > 10):
                if current_edu:
                    education.append(current_edu)
                current_edu = {
                    "institution": line,
                    "area": "",
                    "studyType": "",
                    "startDate": "",
                    "endDate": "",
                }
            elif current_edu:
                # Add as additional info
                if not current_edu["area"]:
                    current_edu["area"] = line
        
        if current_edu:
            education.append(current_edu)
        
        return education[:5]  # Limit to 5 entries

    def _extract_skills(self, text: str) -> list[dict]:
        """Extract skills section."""
        skills = []
        
        # Look for skills section
        match = re.search(
            r"(?:technical\s+)?skills?\s*:?\s*\n?(.*?)(?=\n(?:experience|education|projects|certifications|$))",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        
        if not match:
            return skills
        
        skills_section = match.group(1)
        
        # Try to identify skill categories and keywords
        # Look for patterns like "Category: skill1, skill2, skill3"
        category_pattern = r"([A-Za-z\s]+):\s*([^\n]+)"
        matches = re.findall(category_pattern, skills_section)
        
        for category, skill_list in matches:
            keywords = [s.strip() for s in re.split(r"[,;|]", skill_list) if s.strip()]
            if keywords:
                skills.append({
                    "name": category.strip(),
                    "keywords": keywords,
                })
        
        # If no categories found, treat as flat list
        if not skills:
            # Split by common delimiters
            all_skills = re.split(r"[,;|\n•·]", skills_section)
            keywords = [s.strip() for s in all_skills if s.strip() and len(s.strip()) < 50]
            if keywords:
                skills.append({
                    "name": "Skills",
                    "keywords": keywords[:30],  # Limit
                })
        
        return skills


# Global instances
_fetcher: Optional[ContentFetcher] = None
_parser: Optional[ResumePDFParser] = None


def get_fetcher() -> ContentFetcher:
    """Get the global content fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = ContentFetcher()
    return _fetcher


def get_parser() -> ResumePDFParser:
    """Get the global PDF parser instance."""
    global _parser
    if _parser is None:
        _parser = ResumePDFParser()
    return _parser
