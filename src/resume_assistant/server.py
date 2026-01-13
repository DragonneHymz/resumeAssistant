"""
Resume Assistant MCP Server

Main FastMCP server implementation with tools, resources, and prompts.
Each @mcp.tool() is an "Agent Skill" - a capability the AI assistant gains.
"""

from datetime import datetime
from typing import Optional

from fastmcp import FastMCP

from .generator import get_generator
from .models import (
    Basics,
    Certificate,
    Education,
    Interest,
    JSONResume,
    Language,
    Location,
    Profile,
    Project,
    ResumeExtensions,
    Skill,
    Work,
)
from .optimizer import get_optimizer
from .parser import get_fetcher, get_parser
from .storage import get_storage

# Initialize MCP server
mcp = FastMCP(
    name="Resume Assistant",
    instructions="""You are a Resume Assistant helping users secure jobs through optimized resumes.

Core Mission: Help the user SECURE A JOB.

Key Capabilities:
- Store and manage resumes using JSON Resume standard
- Import existing PDF resumes
- Analyze job descriptions from URLs or text
- Score resumes using enterprise ATS methodology
- Optimize content with multiple options for user selection
- Export formatted text files for easy copy-paste into your template

Always:
1. Ask for the user's target industry first
2. Use professional terminology appropriate to their field
3. Present optimization options and let the user choose
4. Focus on authentic improvements (never fabricate experience)
""",
)

# ═══════════════════════════════════════════════════════════════════════════════
# RESUME IMPORT & STORAGE SKILLS
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def import_resume_from_pdf(pdf_path: str, industry: Optional[str] = None) -> dict:
    """
    Import an existing resume from a PDF file.
    
    Args:
        pdf_path: Absolute path to the PDF file
        industry: Target industry for the user (e.g., "technology", "finance")
        
    Returns:
        dict with resume_id, extracted data summary, and any parsing notes
    """
    parser = get_parser()
    storage = get_storage()
    
    try:
        # Parse PDF
        parsed = parser.parse_pdf(pdf_path)
        
        # Create JSON Resume
        resume = JSONResume(
            basics=Basics(
                name=parsed["basics"].get("name", ""),
                email=parsed["basics"].get("email", ""),
                phone=parsed["basics"].get("phone"),
                profiles=[Profile(**p) for p in parsed["basics"].get("profiles", [])],
            ),
            work=[Work(**w) for w in parsed.get("work", [])],
            education=[Education(**e) for e in parsed.get("education", [])],
            skills=[Skill(**s) for s in parsed.get("skills", [])],
        )
        
        # Set industry if provided
        if industry:
            resume.set_industry(industry)
        
        # Save
        resume_id = storage.save(resume)
        
        return {
            "success": True,
            "resume_id": resume_id,
            "name": resume.basics.name,
            "email": resume.basics.email,
            "industry": industry,
            "sections_extracted": {
                "work_entries": len(resume.work),
                "education_entries": len(resume.education),
                "skill_categories": len(resume.skills),
            },
            "notes": "Review extracted data and make corrections as needed.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def store_resume(
    name: str,
    email: str,
    industry: Optional[str] = None,
    phone: Optional[str] = None,
    label: Optional[str] = None,
    summary: Optional[str] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    Create and store a new resume with basic information.
    
    Args:
        name: Full name
        email: Email address
        industry: Target industry (e.g., "technology", "finance", "healthcare")
        phone: Phone number
        label: Professional title (e.g., "Software Engineer")
        summary: Professional summary paragraph
        city: City name
        region: State/province
        
    Returns:
        dict with resume_id and confirmation
    """
    storage = get_storage()
    
    location = None
    if city or region:
        location = Location(city=city, region=region)
    
    resume = JSONResume(
        basics=Basics(
            name=name,
            email=email,
            phone=phone,
            label=label,
            summary=summary,
            location=location,
        ),
    )
    
    if industry:
        resume.set_industry(industry)
    
    resume_id = storage.save(resume)
    
    return {
        "success": True,
        "resume_id": resume_id,
        "message": f"Resume created for {name}. Add experience, education, and skills next.",
    }


@mcp.tool()
def get_resume(resume_id: str) -> dict:
    """
    Retrieve full resume data by ID.
    
    Args:
        resume_id: The resume's unique identifier
        
    Returns:
        Complete resume data in JSON Resume format
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    return {
        "resume": resume.model_dump(mode="json"),
        "industry": resume.get_industry(),
    }


@mcp.tool()
def export_json_resume(resume_id: str) -> dict:
    """
    Export resume as standard JSON Resume format for use with other tools.
    
    Args:
        resume_id: The resume's unique identifier
        
    Returns:
        Standard JSON Resume (without internal extensions)
    """
    storage = get_storage()
    result = storage.export_standard(resume_id)
    
    if not result:
        return {"error": f"Resume not found: {resume_id}"}
    
    return result


@mcp.tool()
def set_target_industry(
    resume_id: str,
    industry: str,
    target_roles: Optional[list[str]] = None,
) -> dict:
    """
    Set or update the target industry and roles for a resume.
    
    This affects how the LLM provides terminology suggestions and optimization.
    
    Args:
        resume_id: The resume's unique identifier
        industry: Target industry (e.g., "technology", "finance", "healthcare")
        target_roles: List of target job titles
        
    Returns:
        Confirmation of update
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    resume.set_industry(industry)
    if target_roles:
        resume.extensions.target_roles = target_roles
    
    storage.save(resume)
    
    return {
        "success": True,
        "industry": industry,
        "target_roles": target_roles or [],
        "message": f"Industry set to '{industry}'. All optimizations will use {industry} terminology.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RESUME EDITING SKILLS
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
def update_basics(
    resume_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    label: Optional[str] = None,
    summary: Optional[str] = None,
    url: Optional[str] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    Update basic contact information and summary.
    
    Only provided fields will be updated; omit fields to keep current values.
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    if name:
        resume.basics.name = name
    if email:
        resume.basics.email = email
    if phone:
        resume.basics.phone = phone
    if label:
        resume.basics.label = label
    if summary:
        resume.basics.summary = summary
    if url:
        resume.basics.url = url
    if city or region:
        if not resume.basics.location:
            resume.basics.location = Location()
        if city:
            resume.basics.location.city = city
        if region:
            resume.basics.location.region = region
    
    storage.save(resume)
    
    return {"success": True, "updated_basics": resume.basics.model_dump()}


@mcp.tool()
def add_work_experience(
    resume_id: str,
    company: str,
    position: str,
    start_date: str,
    end_date: Optional[str] = None,
    summary: Optional[str] = None,
    highlights: Optional[list[str]] = None,
) -> dict:
    """
    Add a new work experience entry.
    
    Args:
        resume_id: The resume's unique identifier
        company: Company name
        position: Job title
        start_date: Start date (YYYY-MM-DD or YYYY-MM)
        end_date: End date (YYYY-MM-DD, YYYY-MM, or None for current)
        summary: Brief role description
        highlights: List of achievement bullet points
        
    Returns:
        Confirmation with the new entry index
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    work = Work(
        name=company,
        position=position,
        startDate=start_date,
        endDate=end_date,
        summary=summary,
        highlights=highlights or [],
    )
    
    resume.work.append(work)
    storage.save(resume)
    
    return {
        "success": True,
        "index": len(resume.work) - 1,
        "message": f"Added {position} at {company}",
    }


@mcp.tool()
def update_work_experience(
    resume_id: str,
    index: int,
    company: Optional[str] = None,
    position: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    summary: Optional[str] = None,
    highlights: Optional[list[str]] = None,
) -> dict:
    """
    Update an existing work experience entry.
    
    Only provided fields will be updated.
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    if index >= len(resume.work):
        return {"error": f"Work entry index {index} not found"}
    
    work = resume.work[index]
    
    if company:
        work.name = company
    if position:
        work.position = position
    if start_date:
        work.startDate = start_date
    if end_date is not None:
        work.endDate = end_date
    if summary:
        work.summary = summary
    if highlights is not None:
        work.highlights = highlights
    
    storage.save(resume)
    
    return {"success": True, "updated_work": work.model_dump()}


@mcp.tool()
def add_education(
    resume_id: str,
    institution: str,
    study_type: Optional[str] = None,
    area: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    score: Optional[str] = None,
    courses: Optional[list[str]] = None,
) -> dict:
    """
    Add a new education entry.
    
    Args:
        institution: School/university name
        study_type: Degree type (e.g., "Bachelor", "Master", "PhD")
        area: Field of study (e.g., "Computer Science")
        start_date: Start date
        end_date: Graduation date (or expected)
        score: GPA or grade
        courses: Relevant coursework
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    edu = Education(
        institution=institution,
        studyType=study_type,
        area=area,
        startDate=start_date,
        endDate=end_date,
        score=score,
        courses=courses or [],
    )
    
    resume.education.append(edu)
    storage.save(resume)
    
    return {
        "success": True,
        "index": len(resume.education) - 1,
        "message": f"Added {study_type or 'education'} from {institution}",
    }


@mcp.tool()
def add_skill(
    resume_id: str,
    category: str,
    keywords: list[str],
    level: Optional[str] = None,
) -> dict:
    """
    Add skills to the resume.
    
    Args:
        category: Skill category (e.g., "Programming Languages", "Cloud Platforms")
        keywords: List of specific skills (e.g., ["Python", "JavaScript", "Go"])
        level: Proficiency level (e.g., "Expert", "Intermediate")
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    # Check if category exists
    for skill in resume.skills:
        if skill.name.lower() == category.lower():
            # Add to existing category
            skill.keywords.extend(keywords)
            skill.keywords = list(set(skill.keywords))  # Dedupe
            storage.save(resume)
            return {
                "success": True,
                "message": f"Added {len(keywords)} skills to existing category '{category}'",
                "total_keywords": len(skill.keywords),
            }
    
    # Create new category
    skill = Skill(name=category, keywords=keywords, level=level)
    resume.skills.append(skill)
    storage.save(resume)
    
    return {
        "success": True,
        "message": f"Created new skill category '{category}' with {len(keywords)} skills",
    }


@mcp.tool()
def add_project(
    resume_id: str,
    name: str,
    description: Optional[str] = None,
    highlights: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    url: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Add a project entry.
    
    Args:
        name: Project name
        description: Brief description
        highlights: Key accomplishments or features
        keywords: Technologies/skills used
        url: Link to project (GitHub, demo, etc.)
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    project = Project(
        name=name,
        description=description,
        highlights=highlights or [],
        keywords=keywords or [],
        url=url,
        startDate=start_date,
        endDate=end_date,
    )
    
    resume.projects.append(project)
    storage.save(resume)
    
    return {
        "success": True,
        "index": len(resume.projects) - 1,
        "message": f"Added project: {name}",
    }


@mcp.tool()
def add_certification(
    resume_id: str,
    name: str,
    issuer: Optional[str] = None,
    date: Optional[str] = None,
    url: Optional[str] = None,
) -> dict:
    """
    Add a professional certification.
    
    Args:
        name: Certification name (e.g., "AWS Solutions Architect")
        issuer: Issuing organization (e.g., "Amazon Web Services")
        date: Date obtained
        url: Verification URL
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    cert = Certificate(name=name, issuer=issuer, date=date, url=url)
    resume.certificates.append(cert)
    storage.save(resume)
    
    return {
        "success": True,
        "index": len(resume.certificates) - 1,
        "message": f"Added certification: {name}",
    }


@mcp.tool()
def add_language(
    resume_id: str,
    language: str,
    fluency: Optional[str] = None,
) -> dict:
    """
    Add a language proficiency.
    
    Args:
        language: Language name (e.g., "English", "Spanish")
        fluency: Proficiency level (e.g., "Native", "Fluent", "Intermediate")
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    lang = Language(language=language, fluency=fluency)
    resume.languages.append(lang)
    storage.save(resume)
    
    return {
        "success": True,
        "index": len(resume.languages) - 1,
        "message": f"Added language: {language}",
    }


@mcp.tool()
def add_interest(
    resume_id: str,
    name: str,
    keywords: list[str],
) -> dict:
    """
    Add a personal interest or hobby.
    
    Args:
        name: Interest name (e.g., "Photography", "Hiking")
        keywords: List of related keywords (e.g., ["Landscape", "Portrait"])
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    # Check if interest exists
    for interest in resume.interests:
        if interest.name.lower() == name.lower():
            # Add to existing interest
            interest.keywords.extend(keywords)
            interest.keywords = list(set(interest.keywords))  # Dedupe
            storage.save(resume)
            return {
                "success": True,
                "message": f"Added {len(keywords)} keywords to existing interest '{name}'",
                "total_keywords": len(interest.keywords),
            }
            
    interest = Interest(name=name, keywords=keywords)
    resume.interests.append(interest)
    storage.save(resume)
    
    return {
        "success": True,
        "index": len(resume.interests) - 1,
        "message": f"Added interest: {name}",
    }


@mcp.tool()
def delete_entry(resume_id: str, section: str, index: int) -> dict:
    """
    Delete a specific entry from a resume section by index.
    
    Args:
        resume_id: The resume's unique identifier
        section: Section name (work, education, skills, projects, certificates)
        index: Entry index to delete
    """
    storage = get_storage()
    resume = storage.load(resume_id)
    
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    section_map = {
        "work": resume.work,
        "education": resume.education,
        "skills": resume.skills,
        "projects": resume.projects,
        "certificates": resume.certificates,
        "languages": resume.languages,
        "interests": resume.interests,
    }
    
    if section not in section_map:
        return {"error": f"Invalid section: {section}. Valid: {list(section_map.keys())}"}
    
    items = section_map[section]
    
    if index >= len(items):
        return {"error": f"Index {index} out of range for {section} (has {len(items)} entries)"}
    
    deleted = items.pop(index)
    storage.save(resume)
    
    return {"success": True, "deleted": deleted.model_dump() if hasattr(deleted, 'model_dump') else str(deleted)}


# ═══════════════════════════════════════════════════════════════════════════════
# JOB DESCRIPTION ANALYSIS SKILLS
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def fetch_job_description(job_input: str) -> dict:
    """
    Fetch and parse a job description from URL or return raw text.
    
    Args:
        job_input: Either a URL to a job posting OR the raw job description text.
                   URLs from LinkedIn, Indeed, Greenhouse, Lever, Workday are supported.
                   
    Returns:
        dict with source type, content, and detected metadata
    """
    fetcher = get_fetcher()
    
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            return {
                "success": True,
                "source": "url",
                "url": job_input,
                "title": result.get("title", ""),
                "content": result.get("content", ""),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        return {
            "success": True,
            "source": "text",
            "content": job_input,
        }


@mcp.tool()
async def analyze_job_description(job_input: str) -> dict:
    """
    Deep analysis of job description using enterprise ATS methodology.
    
    Args:
        job_input: URL to job posting OR raw job description text.
    
    Returns:
        Detailed analysis including required/preferred skills, experience requirements,
        and key information for optimization.
    """
    fetcher = get_fetcher()
    optimizer = get_optimizer()
    
    # Get content
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            content = result.get("content", "")
        except Exception as e:
            return {"error": str(e)}
    else:
        content = job_input
    
    # Analyze
    analysis = optimizer.extract_keywords(content)
    
    return {
        "required_skills": analysis.required_skills,
        "preferred_skills": analysis.preferred_skills,
        "technical_skills": analysis.technical_skills,
        "soft_skills": analysis.soft_skills,
        "certifications": analysis.certifications,
        "experience_years": analysis.experience_years,
        "education_requirements": analysis.education_requirements,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ATS OPTIMIZATION SKILLS (Multi-Option with Regeneration)
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def score_resume(resume_id: str, job_input: str) -> dict:
    """
    Score resume using enterprise ATS methodology.
    
    Returns comprehensive score breakdown:
    - Overall score (0-100)
    - Keyword match score (40% weight)
    - Semantic relevance score (20% weight)
    - Experience match score (20% weight)
    - Skills coverage score (15% weight)
    - Formatting score (5% weight)
    - Pass/fail indication (75+ typically passes)
    - Prioritized improvement recommendations
    """
    storage = get_storage()
    fetcher = get_fetcher()
    optimizer = get_optimizer()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    # Get job description content
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            job_description = result.get("content", "")
        except Exception as e:
            return {"error": str(e)}
    else:
        job_description = job_input
    
    # Score
    score = optimizer.score_resume(resume, job_description)
    
    return {
        "overall_score": score.overall,
        "passes_threshold": score.passes_threshold,
        "breakdown": {
            "keyword_match": {"score": score.keyword_score, "weight": "40%"},
            "semantic_relevance": {"score": score.semantic_score, "weight": "20%"},
            "experience_match": {"score": score.experience_score, "weight": "20%"},
            "skills_coverage": {"score": score.skills_score, "weight": "15%"},
            "formatting": {"score": score.formatting_score, "weight": "5%"},
        },
        "matched_keywords": score.matched_keywords,
        "missing_required": score.missing_required,
        "missing_preferred": score.missing_preferred,
        "recommendations": score.recommendations,
    }


@mcp.tool()
async def get_missing_keywords(resume_id: str, job_input: str) -> dict:
    """
    Identify keywords from job description not present in resume.
    
    Returns categorized missing keywords with suggestions on how to incorporate.
    """
    storage = get_storage()
    fetcher = get_fetcher()
    optimizer = get_optimizer()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            job_description = result.get("content", "")
        except Exception as e:
            return {"error": str(e)}
    else:
        job_description = job_input
    
    score = optimizer.score_resume(resume, job_description)
    
    return {
        "critical": score.missing_required,
        "important": score.missing_preferred,
        "suggestions": [
            f"Add '{kw}' to your skills section if you have this experience"
            for kw in score.missing_required[:5]
        ],
    }


@mcp.tool()
async def generate_bullet_options(
    resume_id: str,
    work_index: int,
    bullet_index: int,
    job_input: str,
    num_options: int = 3,
) -> dict:
    """
    Generate multiple rewrite options for a bullet point.
    
    User can:
    - Select one of the options
    - Request regeneration if none are suitable
    - Provide feedback for targeted regeneration
    
    Returns:
    - original: The current bullet text
    - options: Context for LLM to generate 3 alternative rewrites
    - option_id: Unique ID for selection or regeneration
    """
    storage = get_storage()
    fetcher = get_fetcher()
    optimizer = get_optimizer()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    if work_index >= len(resume.work):
        return {"error": f"Work entry {work_index} not found"}
    
    work = resume.work[work_index]
    if bullet_index >= len(work.highlights):
        return {"error": f"Bullet {bullet_index} not found in work entry {work_index}"}
    
    original = work.highlights[bullet_index]
    
    # Get missing keywords
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            job_description = result.get("content", "")
        except Exception as e:
            return {"error": str(e)}
    else:
        job_description = job_input
    
    score = optimizer.score_resume(resume, job_description)
    target_keywords = score.missing_required + score.missing_preferred
    
    # Generate options
    options = optimizer.generate_bullet_options(
        original=original,
        target_keywords=target_keywords[:5],
        industry=resume.get_industry(),
        work_index=work_index,
        bullet_index=bullet_index,
        num_options=num_options,
    )
    
    return {
        "option_id": options.option_id,
        "original": original,
        "target_keywords": target_keywords[:5],
        "industry": resume.get_industry(),
        "position": work.position,
        "company": work.name,
        "instruction": f"Generate {num_options} different rewrites of this bullet point, each incorporating some of the target keywords naturally. Return as a list of 3 options.",
    }


@mcp.tool()
async def generate_summary_options(
    resume_id: str,
    job_input: str,
    num_options: int = 3,
) -> dict:
    """
    Generate multiple professional summary options tailored to the job.
    
    Returns context for the LLM to generate 3 summary variations.
    """
    storage = get_storage()
    fetcher = get_fetcher()
    optimizer = get_optimizer()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            job_description = result.get("content", "")
        except Exception as e:
            return {"error": str(e)}
    else:
        job_description = job_input
    
    analysis = optimizer.extract_keywords(job_description)
    options = optimizer.generate_summary_options(resume, job_description, num_options)
    
    return {
        "option_id": options.option_id,
        "current_summary": resume.basics.summary,
        "name": resume.basics.name,
        "label": resume.basics.label,
        "industry": resume.get_industry(),
        "years_experience": len(resume.work),
        "required_skills": analysis.required_skills[:5],
        "instruction": f"Generate {num_options} different professional summary paragraphs (2-3 sentences each) tailored to this role. Incorporate key skills naturally.",
    }


@mcp.tool()
async def regenerate_options(option_id: str, feedback: Optional[str] = None) -> dict:
    """
    Regenerate optimization options based on user feedback.
    
    Args:
        option_id: ID from previous generate_*_options call
        feedback: User guidance, e.g., "make it more concise",
                  "focus on leadership", "include Python keyword"
                  
    Returns context for the LLM to generate new options.
    """
    optimizer = get_optimizer()
    context = optimizer.regenerate_options(option_id, feedback)
    
    if not context:
        return {"error": f"Option ID not found: {option_id}"}
    
    context["instruction"] = f"Generate 3 new options. User feedback: {feedback or 'None provided'}"
    return context


@mcp.tool()
async def select_optimization_option(
    resume_id: str,
    option_id: str,
    selected_index: int,
    selected_text: str,
) -> dict:
    """
    Apply user's selected option to the resume.
    
    Args:
        resume_id: The resume to update
        option_id: ID from the generate_*_options call
        selected_index: 0, 1, or 2 (which option chosen)
        selected_text: The actual text of the selected option
        
    Returns confirmation and updated section.
    """
    storage = get_storage()
    optimizer = get_optimizer()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    success = optimizer.apply_selection(resume, option_id, selected_text)
    
    if success:
        storage.save(resume)
        return {
            "success": True,
            "message": f"Applied option {selected_index + 1}",
            "applied_text": selected_text,
        }
    else:
        return {"error": "Failed to apply selection. Option may have expired."}


@mcp.tool()
async def start_interactive_optimization(resume_id: str, job_input: str) -> dict:
    """
    Start an interactive optimization session.
    
    Returns a prioritized list of items to optimize with the first item's
    options ready for review. Guide the user through each item.
    """
    storage = get_storage()
    fetcher = get_fetcher()
    optimizer = get_optimizer()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    if fetcher.is_url(job_input):
        try:
            result = await fetcher.fetch_url(job_input)
            job_description = result.get("content", "")
        except Exception as e:
            return {"error": str(e)}
    else:
        job_description = job_input
    
    session = optimizer.start_interactive_session(resume, job_description)
    
    return {
        "session_id": session.session_id,
        "current_score": session.current_score,
        "potential_score": session.potential_score,
        "total_items": len(session.items),
        "items_preview": [
            {
                "type": item.item_type,
                "priority": item.priority,
                "current_text": item.current_text[:100] + "..." if len(item.current_text) > 100 else item.current_text,
            }
            for item in session.items[:5]
        ],
        "instruction": "Present these optimization opportunities and guide the user through each, offering options and regeneration.",
    }


@mcp.tool()
async def get_next_optimization(session_id: str, skip_current: bool = False) -> dict:
    """
    Get the next item to optimize in an interactive session.
    
    Args:
        session_id: The optimization session ID
        skip_current: If True, skip current item without changes
    """
    optimizer = get_optimizer()
    
    item = optimizer.get_next_item(session_id, skip_current)
    
    if not item:
        return {
            "session_complete": True,
            "message": "All optimization items have been reviewed!",
        }
    
    return {
        "session_complete": False,
        "item_type": item.item_type,
        "section": item.section,
        "index": item.index,
        "sub_index": item.sub_index,
        "current_text": item.current_text,
        "priority": item.priority,
        "impact_score": item.impact_score,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RESUME EXPORT SKILLS
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def export_text(
    resume_id: str,
    filename: Optional[str] = None,
) -> dict:
    """
    Export resume as a formatted text file for easy copy-paste.
    
    Generates a plain text file with proper section headers, bullet points,
    and indentation that can be easily copied into your own resume template.
    
    Args:
        resume_id: The resume's unique identifier
        filename: Optional custom filename (without extension)
        
    Returns:
        Path to the generated text file
    """
    storage = get_storage()
    generator = get_generator()
    
    resume = storage.load(resume_id)
    if not resume:
        return {"error": f"Resume not found: {resume_id}"}
    
    try:
        text_path = generator.generate_text(resume, filename)
        return {
            "success": True,
            "path": text_path,
            "message": f"Text file generated at: {text_path}",
        }
    except Exception as e:
        return {"error": str(e)}



# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES - Data the AI can read
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.resource("resume://list")
def list_resumes() -> str:
    """List all stored resumes with basic info."""
    storage = get_storage()
    resumes = storage.list_all()
    
    if not resumes:
        return "No resumes stored yet."
    
    lines = ["# Stored Resumes\n"]
    for r in resumes:
        lines.append(f"- **{r['name']}** ({r['id'][:8]}...)")
        if r.get("industry"):
            lines.append(f"  - Industry: {r['industry']}")
        if r.get("label"):
            lines.append(f"  - Title: {r['label']}")
    
    return "\n".join(lines)





# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS - Guided Interaction Templates
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def resume_intake() -> str:
    """Guided prompt for collecting resume information from user."""
    return '''
Help me create a professional resume. Your goal is to help the user SECURE A JOB.

FIRST, determine the user's industry and target roles:
ASK: "What industry are you in, and what type of role are you targeting?"

SECOND, check if they have an existing resume:
ASK: "Do you have an existing resume PDF you'd like me to import, 
     or would you prefer to enter your information from scratch?"

If they have a PDF:
- Use import_resume_from_pdf with their industry
- Review extracted data with user
- Make corrections as needed

If entering from scratch:
1. Use store_resume to create initial record with industry
2. Collect work experience (add_work_experience)
3. Collect education (add_education)
4. Collect skills by category (add_skill)
5. Add projects if relevant (add_project)
6. Add certifications (add_certification)

Throughout, use professional terminology appropriate to their industry.
'''


@mcp.prompt()
def optimize_for_job() -> str:
    """Prompt for optimizing resume for a specific job posting."""
    return '''
Help optimize the user's resume for a specific job. Your goal is to maximize ATS score
while maintaining authenticity.

1. Get the job posting URL or description
2. Use analyze_job_description to extract requirements
3. Use score_resume to get current ATS score

4. If score < 75 (not passing):
   - Use start_interactive_optimization to begin guided session
   - For each item, present 3 options using generate_bullet_options or generate_summary_options
   - Let user select or request regeneration
   - Apply selections with select_optimization_option

5. After optimization:
   - Re-score to show improvement
   - Offer to export text file with export_text for easy copy-paste

IMPORTANT:
- Never fabricate experience
- Present options, don't auto-apply
- Allow regeneration with feedback
- Use industry-appropriate terminology
'''


@mcp.prompt()
def resume_review() -> str:
    """Prompt for comprehensive resume review."""
    return '''
Conduct a comprehensive resume review focused on helping the user secure a job.

1. Confirm the user's industry and target role
   
2. Score the resume using score_resume (without job description for general review)

3. Review for:
   - Impact: Are achievements quantified with metrics?
   - Action verbs: Are they strong and industry-appropriate?
   - Terminology: Is language professional for the industry?
   - Keywords: Are critical industry skills represented?
   - Formatting: Is it ATS-friendly?
   - Length: Is it appropriate for experience level?
   - Consistency: Dates, tenses, formatting

4. Prioritize feedback:
   - Critical: Issues that will cause ATS rejection
   - Important: Significantly impact competitiveness
   - Polish: Nice-to-have improvements

5. Offer to help fix issues using the editing tools
   - Present multiple options for any rewrites
   - Let user choose or regenerate

6. When done, offer to export formatted text file with export_text
'''


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
