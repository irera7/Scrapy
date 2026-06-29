"""API endpoints for Visual Scraper."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import structlog

from app.core.security import get_current_user
from app.models.user import User
from app.scrapers.visual_scraper import (
    visual_scraper_service,
    VisualScraperAPI,
    ExtractionRule,
    ScrapingRecipe
)

router = APIRouter()
logger = structlog.get_logger()


# Request/Response schemas
class SessionCreateResponse(BaseModel):
    session_id: str


class NavigateRequest(BaseModel):
    url: str


class NavigateResponse(BaseModel):
    url: str
    title: str
    structure: Dict[str, Any]


class ElementRequest(BaseModel):
    x: int
    y: int


class ElementResponse(BaseModel):
    tag: str
    id: Optional[str]
    classes: List[str]
    text: str
    html: str
    attributes: Dict[str, str]
    xpath: str
    css_selector: str
    suggested_selectors: List[Dict[str, Any]]
    children_count: int
    parent_tag: Optional[str]
    siblings_count: int
    position: Dict[str, float]


class SelectorTestRequest(BaseModel):
    selector: str


class SelectorTestResponse(BaseModel):
    selector: str
    count: int
    matches: List[Dict[str, Any]]


class ExtractionRuleSchema(BaseModel):
    name: str
    selector: str
    extract_type: str = "text"
    attribute_name: Optional[str] = None
    multiple: bool = False
    transform: Optional[str] = None


class ExtractDataRequest(BaseModel):
    rules: List[ExtractionRuleSchema]


class RecipeCreateRequest(BaseModel):
    name: str
    rules: List[ExtractionRuleSchema]
    pagination: Optional[Dict[str, Any]] = None
    wait_for: Optional[str] = None
    scroll_to_bottom: bool = False


class RecipeResponse(BaseModel):
    id: str
    name: str
    base_url: str
    rules: List[Dict[str, Any]]
    pagination: Optional[Dict[str, Any]]
    wait_for: Optional[str]
    scroll_to_bottom: bool


# Session management
@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    current_user: User = Depends(get_current_user)
):
    """Create a new visual scraper session."""
    session_id = f"{current_user.id}_{uuid4().hex[:8]}"
    await visual_scraper_service.create_session(session_id)
    
    logger.info(f"Visual scraper session created: {session_id}")
    return SessionCreateResponse(session_id=session_id)


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """End a visual scraper session."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await visual_scraper_service.end_session(session_id)
    return {"status": "ok"}


# Navigation
@router.post("/sessions/{session_id}/navigate", response_model=NavigateResponse)
async def navigate(
    session_id: str,
    request: NavigateRequest,
    current_user: User = Depends(get_current_user)
):
    """Navigate to a URL in the session."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        result = await visual_scraper_service.navigate(session_id, request.url)
        return NavigateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Element inspection
@router.post("/sessions/{session_id}/element", response_model=ElementResponse)
async def get_element(
    session_id: str,
    request: ElementRequest,
    current_user: User = Depends(get_current_user)
):
    """Get element at coordinates."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        element = await visual_scraper_service.get_element(
            session_id, request.x, request.y
        )
        
        return ElementResponse(
            tag=element.tag,
            id=element.id,
            classes=element.classes,
            text=element.text,
            html=element.html,
            attributes=element.attributes,
            xpath=element.xpath,
            css_selector=element.css_selector,
            suggested_selectors=[
                {
                    "selector": s.selector,
                    "specificity": s.specificity,
                    "matches_count": s.matches_count,
                    "sample_text": s.sample_text
                }
                for s in element.suggested_selectors
            ],
            children_count=element.children_count,
            parent_tag=element.parent_tag,
            siblings_count=element.siblings_count,
            position=element.position
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Selector testing
@router.post("/sessions/{session_id}/test-selector", response_model=SelectorTestResponse)
async def test_selector(
    session_id: str,
    request: SelectorTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Test a CSS selector."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        result = await visual_scraper_service.test_selector(session_id, request.selector)
        return SelectorTestResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Data extraction
@router.post("/sessions/{session_id}/extract")
async def extract_data(
    session_id: str,
    request: ExtractDataRequest,
    current_user: User = Depends(get_current_user)
):
    """Extract data using rules."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    api = visual_scraper_service.get_session(session_id)
    if not api:
        raise HTTPException(status_code=404, detail="Session not found")
    
    rules = [
        ExtractionRule(
            id=str(uuid4()),
            name=r.name,
            selector=r.selector,
            extract_type=r.extract_type,
            attribute_name=r.attribute_name,
            multiple=r.multiple,
            transform=r.transform
        )
        for r in request.rules
    ]
    
    result = await api.extract_data(rules)
    return {"data": result}


# Screenshot
@router.get("/sessions/{session_id}/screenshot")
async def take_screenshot(
    session_id: str,
    full_page: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Take a screenshot of the current page."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    api = visual_scraper_service.get_session(session_id)
    if not api:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        screenshot = await api.take_screenshot(full_page=full_page)
        
        import base64
        return {
            "image": base64.b64encode(screenshot).decode(),
            "format": "png"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Highlight elements
@router.post("/sessions/{session_id}/highlight")
async def highlight_elements(
    session_id: str,
    request: SelectorTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Highlight elements matching selector."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    api = visual_scraper_service.get_session(session_id)
    if not api:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await api.highlight_elements(request.selector)
    return {"status": "ok"}


# Recipe management
@router.post("/sessions/{session_id}/recipe", response_model=RecipeResponse)
async def create_recipe(
    session_id: str,
    request: RecipeCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a scraping recipe from current session."""
    if not session_id.startswith(str(current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    api = visual_scraper_service.get_session(session_id)
    if not api:
        raise HTTPException(status_code=404, detail="Session not found")
    
    recipe = api.create_recipe(
        name=request.name,
        rules=[r.model_dump() for r in request.rules],
        pagination=request.pagination
    )
    
    recipe.wait_for = request.wait_for
    recipe.scroll_to_bottom = request.scroll_to_bottom
    
    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        base_url=recipe.base_url,
        rules=[
            {
                "id": r.id,
                "name": r.name,
                "selector": r.selector,
                "extract_type": r.extract_type,
                "attribute_name": r.attribute_name,
                "multiple": r.multiple,
                "transform": r.transform
            }
            for r in recipe.rules
        ],
        pagination=recipe.pagination,
        wait_for=recipe.wait_for,
        scroll_to_bottom=recipe.scroll_to_bottom
    )

