"""API endpoints for Scraping Templates."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

from app.core.security import get_current_user
from app.models.user import User
from app.scrapers.templates import (
    template_manager,
    ScrapingTemplate,
    TemplateCategory,
    ExtractionField
)

router = APIRouter()
logger = structlog.get_logger()


# Response schemas
class ExtractionFieldResponse(BaseModel):
    name: str
    selector: str
    extract_type: str
    attribute: Optional[str]
    multiple: bool
    required: bool
    transform: Optional[str]
    fallback_selectors: List[str]


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    url_patterns: List[str]
    fields: List[ExtractionFieldResponse]
    pagination_selector: Optional[str]
    pagination_type: str
    max_pages: int
    wait_for_selector: Optional[str]
    wait_timeout: int
    scroll_to_bottom: bool
    javascript_required: bool
    tags: List[str]


class TemplateListResponse(BaseModel):
    templates: List[TemplateResponse]
    total: int


class TemplateCreateRequest(BaseModel):
    id: str
    name: str
    description: str
    category: str
    url_patterns: List[str]
    fields: List[Dict[str, Any]]
    pagination_selector: Optional[str] = None
    pagination_type: str = "next_button"
    max_pages: int = 10
    wait_for_selector: Optional[str] = None
    wait_timeout: int = 10000
    scroll_to_bottom: bool = False
    javascript_required: bool = False
    tags: List[str] = []


class MatchUrlRequest(BaseModel):
    url: str


def template_to_response(template: ScrapingTemplate) -> TemplateResponse:
    """Convert template to response model."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        url_patterns=template.url_patterns,
        fields=[
            ExtractionFieldResponse(
                name=f.name,
                selector=f.selector,
                extract_type=f.extract_type,
                attribute=f.attribute,
                multiple=f.multiple,
                required=f.required,
                transform=f.transform,
                fallback_selectors=f.fallback_selectors
            )
            for f in template.fields
        ],
        pagination_selector=template.pagination_selector,
        pagination_type=template.pagination_type,
        max_pages=template.max_pages,
        wait_for_selector=template.wait_for_selector,
        wait_timeout=template.wait_timeout,
        scroll_to_bottom=template.scroll_to_bottom,
        javascript_required=template.javascript_required,
        tags=template.tags
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = None,
    tags: Optional[str] = None,
    query: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List available scraping templates."""
    # Parse filters
    category_enum = None
    if category:
        try:
            category_enum = TemplateCategory(category)
        except ValueError:
            pass
    
    tags_list = tags.split(",") if tags else None
    
    # Search templates
    templates = template_manager.search_templates(
        query=query,
        category=category_enum,
        tags=tags_list
    )
    
    return TemplateListResponse(
        templates=[template_to_response(t) for t in templates],
        total=len(templates)
    )


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user)
):
    """List available template categories."""
    return {
        "categories": [
            {"id": c.value, "name": c.name.replace("_", " ").title()}
            for c in TemplateCategory
        ]
    }


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific template by ID."""
    template = template_manager.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template_to_response(template)


@router.post("/match")
async def match_url(
    request: MatchUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """Find a template matching a URL."""
    template = template_manager.match_url(request.url)
    
    if template:
        return {
            "matched": True,
            "template": template_to_response(template)
        }
    
    return {"matched": False, "template": None}


@router.post("", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a custom template."""
    # Check if ID already exists
    if template_manager.get_template(request.id):
        raise HTTPException(
            status_code=400,
            detail="Template with this ID already exists"
        )
    
    # Parse category
    try:
        category = TemplateCategory(request.category)
    except ValueError:
        category = TemplateCategory.GENERAL
    
    # Create fields
    fields = [
        ExtractionField(
            name=f.get("name", ""),
            selector=f.get("selector", ""),
            extract_type=f.get("extract_type", "text"),
            attribute=f.get("attribute"),
            multiple=f.get("multiple", False),
            required=f.get("required", False),
            transform=f.get("transform"),
            fallback_selectors=f.get("fallback_selectors", [])
        )
        for f in request.fields
    ]
    
    # Create template
    template = ScrapingTemplate(
        id=request.id,
        name=request.name,
        description=request.description,
        category=category,
        url_patterns=request.url_patterns,
        fields=fields,
        pagination_selector=request.pagination_selector,
        pagination_type=request.pagination_type,
        max_pages=request.max_pages,
        wait_for_selector=request.wait_for_selector,
        wait_timeout=request.wait_timeout,
        scroll_to_bottom=request.scroll_to_bottom,
        javascript_required=request.javascript_required,
        tags=request.tags
    )
    
    template_manager.add_template(template)
    
    logger.info(f"Custom template created: {template.id}")
    
    return template_to_response(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a custom template."""
    template = template_manager.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Don't allow deleting built-in templates
    if template.author == "system":
        raise HTTPException(
            status_code=403,
            detail="Cannot delete built-in templates"
        )
    
    template_manager.remove_template(template_id)
    
    return {"status": "ok"}

