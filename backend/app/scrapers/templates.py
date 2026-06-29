"""Pre-built scraping templates for common websites and use cases."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class TemplateCategory(str, Enum):
    """Categories of scraping templates."""
    NEWS = "news"
    ECOMMERCE = "ecommerce"
    SOCIAL_MEDIA = "social_media"
    BLOG = "blog"
    JOB_BOARD = "job_board"
    REAL_ESTATE = "real_estate"
    DIRECTORY = "directory"
    FORUM = "forum"
    ACADEMIC = "academic"
    GENERAL = "general"


@dataclass
class ExtractionField:
    """A field to extract from a page."""
    name: str
    selector: str
    extract_type: str = "text"  # text, html, attribute, href, src
    attribute: Optional[str] = None
    multiple: bool = False
    required: bool = False
    transform: Optional[str] = None
    fallback_selectors: List[str] = field(default_factory=list)


@dataclass
class ScrapingTemplate:
    """A complete scraping template."""
    id: str
    name: str
    description: str
    category: TemplateCategory
    
    # URL patterns this template matches
    url_patterns: List[str]
    
    # Extraction configuration
    fields: List[ExtractionField]
    
    # Page navigation
    pagination_selector: Optional[str] = None
    pagination_type: str = "next_button"  # next_button, infinite_scroll, load_more, page_number
    max_pages: int = 10
    
    # Wait conditions
    wait_for_selector: Optional[str] = None
    wait_timeout: int = 10000
    
    # Scroll behavior
    scroll_to_bottom: bool = False
    scroll_pause: float = 1.0
    
    # Anti-detection
    rate_limit_delay: float = 1.0
    random_delay: bool = True
    
    # Additional options
    javascript_required: bool = False
    login_required: bool = False
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    author: str = "system"
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)


# ============================================
# Pre-built Templates
# ============================================

# News Article Template
NEWS_ARTICLE_TEMPLATE = ScrapingTemplate(
    id="news_article",
    name="News Article",
    description="Extract content from news articles (BBC, CNN, NYT, etc.)",
    category=TemplateCategory.NEWS,
    url_patterns=[
        r".*bbc\.com/news/.*",
        r".*cnn\.com/.*/.*",
        r".*nytimes\.com/.*/.*",
        r".*theguardian\.com/.*/.*",
        r".*reuters\.com/.*/.*",
        r".*washingtonpost\.com/.*/.*",
    ],
    fields=[
        ExtractionField(
            name="title",
            selector="h1, article h1, .article-title, .headline",
            required=True
        ),
        ExtractionField(
            name="author",
            selector=".author, .byline, [rel='author'], .article-author",
            fallback_selectors=["meta[name='author']"]
        ),
        ExtractionField(
            name="published_date",
            selector="time[datetime], .publish-date, .article-date",
            extract_type="attribute",
            attribute="datetime",
            fallback_selectors=["meta[property='article:published_time']"]
        ),
        ExtractionField(
            name="content",
            selector="article p, .article-body p, .story-body p",
            multiple=True,
            required=True
        ),
        ExtractionField(
            name="category",
            selector=".category, .section-tag, .topic"
        ),
        ExtractionField(
            name="image",
            selector="article img, .article-image img, figure img",
            extract_type="src"
        ),
        ExtractionField(
            name="tags",
            selector=".tags a, .article-tags a",
            multiple=True
        ),
    ],
    wait_for_selector="article, .article-body",
    tags=["news", "article", "text"]
)

# E-commerce Product Template
ECOMMERCE_PRODUCT_TEMPLATE = ScrapingTemplate(
    id="ecommerce_product",
    name="E-commerce Product",
    description="Extract product information from e-commerce sites",
    category=TemplateCategory.ECOMMERCE,
    url_patterns=[
        r".*amazon\.com/.*/dp/.*",
        r".*ebay\.com/itm/.*",
        r".*walmart\.com/ip/.*",
        r".*etsy\.com/listing/.*",
        r".*aliexpress\.com/item/.*",
    ],
    fields=[
        ExtractionField(
            name="title",
            selector="#productTitle, .product-title, h1.title, [data-testid='product-title']",
            required=True
        ),
        ExtractionField(
            name="price",
            selector=".price, #priceblock_ourprice, .product-price, [data-testid='price']",
            required=True,
            transform="regex:[\d.,]+"
        ),
        ExtractionField(
            name="currency",
            selector=".price-currency, .currency-symbol"
        ),
        ExtractionField(
            name="rating",
            selector=".rating, .stars, [data-testid='rating']",
            transform="regex:[\d.]+"
        ),
        ExtractionField(
            name="review_count",
            selector=".review-count, #acrCustomerReviewText",
            transform="regex:\d+"
        ),
        ExtractionField(
            name="description",
            selector="#productDescription, .product-description, .description"
        ),
        ExtractionField(
            name="images",
            selector=".product-image img, #imgTagWrapperId img, .gallery img",
            extract_type="src",
            multiple=True
        ),
        ExtractionField(
            name="availability",
            selector=".availability, #availability, .stock-status"
        ),
        ExtractionField(
            name="seller",
            selector=".seller-name, #sellerProfileTriggerId"
        ),
        ExtractionField(
            name="categories",
            selector=".breadcrumb a, #wayfinding-breadcrumbs_feature_div a",
            multiple=True
        ),
        ExtractionField(
            name="features",
            selector=".product-features li, #feature-bullets li",
            multiple=True
        ),
    ],
    wait_for_selector="#productTitle, .product-title",
    javascript_required=True,
    tags=["ecommerce", "product", "price"]
)

# Product Listing Template
PRODUCT_LISTING_TEMPLATE = ScrapingTemplate(
    id="product_listing",
    name="Product Listing Page",
    description="Extract product list from category/search pages",
    category=TemplateCategory.ECOMMERCE,
    url_patterns=[
        r".*amazon\.com/s\?.*",
        r".*/category/.*",
        r".*/search\?.*",
        r".*/products.*",
    ],
    fields=[
        ExtractionField(
            name="products",
            selector=".product-item, .s-result-item, .product-card",
            multiple=True
        ),
        ExtractionField(
            name="product_title",
            selector=".product-title, h2 a, .product-name"
        ),
        ExtractionField(
            name="product_price",
            selector=".price, .product-price"
        ),
        ExtractionField(
            name="product_url",
            selector="a.product-link, h2 a",
            extract_type="href"
        ),
        ExtractionField(
            name="product_image",
            selector=".product-image img",
            extract_type="src"
        ),
        ExtractionField(
            name="total_results",
            selector=".result-count, .total-count"
        ),
    ],
    pagination_selector=".pagination .next, .a-pagination .a-last a",
    pagination_type="next_button",
    max_pages=5,
    tags=["ecommerce", "listing", "search"]
)

# Blog Post Template
BLOG_POST_TEMPLATE = ScrapingTemplate(
    id="blog_post",
    name="Blog Post",
    description="Extract content from blog posts",
    category=TemplateCategory.BLOG,
    url_patterns=[
        r".*/blog/.*",
        r".*/post/.*",
        r".*medium\.com/.*",
        r".*wordpress\.com/.*",
        r".*blogger\.com/.*",
    ],
    fields=[
        ExtractionField(
            name="title",
            selector="h1, .post-title, .entry-title, article h1",
            required=True
        ),
        ExtractionField(
            name="author",
            selector=".author, .post-author, .byline, [rel='author']"
        ),
        ExtractionField(
            name="date",
            selector=".date, .post-date, .entry-date, time",
            extract_type="attribute",
            attribute="datetime"
        ),
        ExtractionField(
            name="content",
            selector=".post-content, .entry-content, article, .article-body",
            required=True
        ),
        ExtractionField(
            name="tags",
            selector=".tags a, .post-tags a, .entry-tags a",
            multiple=True
        ),
        ExtractionField(
            name="categories",
            selector=".categories a, .post-categories a",
            multiple=True
        ),
        ExtractionField(
            name="featured_image",
            selector=".featured-image img, .post-thumbnail img",
            extract_type="src"
        ),
        ExtractionField(
            name="comments_count",
            selector=".comments-count, .comment-count",
            transform="regex:\d+"
        ),
    ],
    wait_for_selector="article, .post-content",
    tags=["blog", "article", "text"]
)

# Job Listing Template
JOB_LISTING_TEMPLATE = ScrapingTemplate(
    id="job_listing",
    name="Job Listing",
    description="Extract job postings from job boards",
    category=TemplateCategory.JOB_BOARD,
    url_patterns=[
        r".*indeed\.com/viewjob.*",
        r".*linkedin\.com/jobs/view/.*",
        r".*glassdoor\.com/job-listing/.*",
        r".*monster\.com/job-openings/.*",
    ],
    fields=[
        ExtractionField(
            name="title",
            selector=".jobTitle, .job-title, h1.title, .topcard__title",
            required=True
        ),
        ExtractionField(
            name="company",
            selector=".company, .companyName, .employer, .topcard__org-name-link",
            required=True
        ),
        ExtractionField(
            name="location",
            selector=".location, .job-location, .topcard__flavor--bullet"
        ),
        ExtractionField(
            name="salary",
            selector=".salary, .salary-snippet, .compensation"
        ),
        ExtractionField(
            name="job_type",
            selector=".job-type, .employment-type"
        ),
        ExtractionField(
            name="description",
            selector=".job-description, #jobDescriptionText, .description__text",
            required=True
        ),
        ExtractionField(
            name="requirements",
            selector=".requirements li, .qualifications li",
            multiple=True
        ),
        ExtractionField(
            name="benefits",
            selector=".benefits li, .perks li",
            multiple=True
        ),
        ExtractionField(
            name="posted_date",
            selector=".date, .posted-date, time"
        ),
        ExtractionField(
            name="apply_url",
            selector=".apply-button, #applyButton",
            extract_type="href"
        ),
    ],
    wait_for_selector=".job-description, #jobDescriptionText",
    tags=["jobs", "career", "employment"]
)

# Real Estate Listing Template
REAL_ESTATE_TEMPLATE = ScrapingTemplate(
    id="real_estate",
    name="Real Estate Listing",
    description="Extract property listings",
    category=TemplateCategory.REAL_ESTATE,
    url_patterns=[
        r".*zillow\.com/homedetails/.*",
        r".*realtor\.com/realestateandhomes-detail/.*",
        r".*redfin\.com/.*/home/.*",
        r".*trulia\.com/p/.*",
    ],
    fields=[
        ExtractionField(
            name="address",
            selector=".address, .property-address, h1",
            required=True
        ),
        ExtractionField(
            name="price",
            selector=".price, .home-price, .listing-price",
            required=True,
            transform="regex:[\d,.]+"
        ),
        ExtractionField(
            name="bedrooms",
            selector=".beds, .bedroom-count, [data-testid='beds']",
            transform="regex:\d+"
        ),
        ExtractionField(
            name="bathrooms",
            selector=".baths, .bathroom-count, [data-testid='baths']",
            transform="regex:[\d.]+"
        ),
        ExtractionField(
            name="sqft",
            selector=".sqft, .square-feet, [data-testid='sqft']",
            transform="regex:[\d,]+"
        ),
        ExtractionField(
            name="lot_size",
            selector=".lot-size, .land-area"
        ),
        ExtractionField(
            name="year_built",
            selector=".year-built, .build-year",
            transform="regex:\d{4}"
        ),
        ExtractionField(
            name="property_type",
            selector=".property-type, .home-type"
        ),
        ExtractionField(
            name="description",
            selector=".description, .listing-description"
        ),
        ExtractionField(
            name="images",
            selector=".gallery img, .photos img, .carousel img",
            extract_type="src",
            multiple=True
        ),
        ExtractionField(
            name="features",
            selector=".features li, .amenities li",
            multiple=True
        ),
        ExtractionField(
            name="agent_name",
            selector=".agent-name, .realtor-name"
        ),
        ExtractionField(
            name="agent_phone",
            selector=".agent-phone, .contact-phone"
        ),
    ],
    wait_for_selector=".price, .home-price",
    javascript_required=True,
    tags=["real_estate", "property", "housing"]
)

# Social Media Post Template
SOCIAL_POST_TEMPLATE = ScrapingTemplate(
    id="social_post",
    name="Social Media Post",
    description="Extract posts from social media platforms",
    category=TemplateCategory.SOCIAL_MEDIA,
    url_patterns=[
        r".*twitter\.com/.*/status/.*",
        r".*x\.com/.*/status/.*",
        r".*facebook\.com/.*/posts/.*",
        r".*instagram\.com/p/.*",
    ],
    fields=[
        ExtractionField(
            name="author",
            selector=".author, .username, .display-name",
            required=True
        ),
        ExtractionField(
            name="handle",
            selector=".handle, .screen-name, .username"
        ),
        ExtractionField(
            name="content",
            selector=".post-content, .tweet-text, .caption",
            required=True
        ),
        ExtractionField(
            name="timestamp",
            selector="time, .timestamp, .post-time",
            extract_type="attribute",
            attribute="datetime"
        ),
        ExtractionField(
            name="likes",
            selector=".likes, .like-count, [data-testid='like']",
            transform="regex:[\d,]+"
        ),
        ExtractionField(
            name="shares",
            selector=".shares, .retweet-count, .share-count",
            transform="regex:[\d,]+"
        ),
        ExtractionField(
            name="comments",
            selector=".comments, .reply-count, .comment-count",
            transform="regex:[\d,]+"
        ),
        ExtractionField(
            name="media",
            selector=".media img, .post-image img, video",
            extract_type="src",
            multiple=True
        ),
        ExtractionField(
            name="hashtags",
            selector="a[href*='hashtag'], .hashtag",
            multiple=True
        ),
    ],
    javascript_required=True,
    tags=["social", "post", "engagement"]
)

# Forum Thread Template
FORUM_THREAD_TEMPLATE = ScrapingTemplate(
    id="forum_thread",
    name="Forum Thread",
    description="Extract discussions from forum threads",
    category=TemplateCategory.FORUM,
    url_patterns=[
        r".*reddit\.com/r/.*/comments/.*",
        r".*/thread/.*",
        r".*/forum/.*",
        r".*/discussion/.*",
    ],
    fields=[
        ExtractionField(
            name="title",
            selector="h1, .thread-title, .post-title",
            required=True
        ),
        ExtractionField(
            name="author",
            selector=".author, .username, .poster"
        ),
        ExtractionField(
            name="date",
            selector=".date, time, .timestamp"
        ),
        ExtractionField(
            name="content",
            selector=".post-content, .message-body, .thread-body",
            required=True
        ),
        ExtractionField(
            name="replies",
            selector=".reply, .comment, .response",
            multiple=True
        ),
        ExtractionField(
            name="reply_author",
            selector=".reply .author, .comment .username"
        ),
        ExtractionField(
            name="reply_content",
            selector=".reply .content, .comment .body"
        ),
        ExtractionField(
            name="reply_date",
            selector=".reply time, .comment .date"
        ),
        ExtractionField(
            name="upvotes",
            selector=".upvotes, .score, .votes",
            transform="regex:[\d,]+"
        ),
        ExtractionField(
            name="views",
            selector=".views, .view-count",
            transform="regex:[\d,]+"
        ),
    ],
    scroll_to_bottom=True,
    tags=["forum", "discussion", "community"]
)

# Academic Paper Template
ACADEMIC_PAPER_TEMPLATE = ScrapingTemplate(
    id="academic_paper",
    name="Academic Paper",
    description="Extract academic paper metadata",
    category=TemplateCategory.ACADEMIC,
    url_patterns=[
        r".*arxiv\.org/abs/.*",
        r".*scholar\.google\.com/.*",
        r".*pubmed\.ncbi\.nlm\.nih\.gov/.*",
        r".*ieee\.org/document/.*",
        r".*sciencedirect\.com/science/article/.*",
    ],
    fields=[
        ExtractionField(
            name="title",
            selector="h1, .title, .article-title, .document-title",
            required=True
        ),
        ExtractionField(
            name="authors",
            selector=".authors a, .author-name, .contrib-author",
            multiple=True
        ),
        ExtractionField(
            name="abstract",
            selector=".abstract, #abstract, .article-abstract",
            required=True
        ),
        ExtractionField(
            name="published_date",
            selector=".pub-date, .publish-date, time"
        ),
        ExtractionField(
            name="journal",
            selector=".journal-name, .publication, .venue"
        ),
        ExtractionField(
            name="doi",
            selector=".doi, [data-doi]",
            fallback_selectors=["meta[name='citation_doi']"]
        ),
        ExtractionField(
            name="keywords",
            selector=".keywords a, .keyword, .subject-term",
            multiple=True
        ),
        ExtractionField(
            name="citations",
            selector=".citation-count, .times-cited",
            transform="regex:\d+"
        ),
        ExtractionField(
            name="pdf_url",
            selector="a[href*='.pdf'], .pdf-link, .download-pdf",
            extract_type="href"
        ),
        ExtractionField(
            name="references",
            selector=".references li, .ref-list li",
            multiple=True
        ),
    ],
    tags=["academic", "paper", "research"]
)


# ============================================
# Template Manager
# ============================================

class TemplateManager:
    """Manager for scraping templates."""
    
    def __init__(self):
        self._templates: Dict[str, ScrapingTemplate] = {}
        self._load_built_in_templates()
    
    def _load_built_in_templates(self):
        """Load all built-in templates."""
        templates = [
            NEWS_ARTICLE_TEMPLATE,
            ECOMMERCE_PRODUCT_TEMPLATE,
            PRODUCT_LISTING_TEMPLATE,
            BLOG_POST_TEMPLATE,
            JOB_LISTING_TEMPLATE,
            REAL_ESTATE_TEMPLATE,
            SOCIAL_POST_TEMPLATE,
            FORUM_THREAD_TEMPLATE,
            ACADEMIC_PAPER_TEMPLATE,
        ]
        
        for template in templates:
            self._templates[template.id] = template
    
    def get_template(self, template_id: str) -> Optional[ScrapingTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[ScrapingTemplate]:
        """Get all templates in a category."""
        return [t for t in self._templates.values() if t.category == category]
    
    def get_all_templates(self) -> List[ScrapingTemplate]:
        """Get all available templates."""
        return list(self._templates.values())
    
    def match_url(self, url: str) -> Optional[ScrapingTemplate]:
        """Find a template that matches the given URL."""
        import re
        
        for template in self._templates.values():
            for pattern in template.url_patterns:
                if re.match(pattern, url):
                    return template
        
        return None
    
    def add_template(self, template: ScrapingTemplate):
        """Add a custom template."""
        self._templates[template.id] = template
    
    def remove_template(self, template_id: str):
        """Remove a template."""
        if template_id in self._templates:
            del self._templates[template_id]
    
    def template_to_dict(self, template: ScrapingTemplate) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "url_patterns": template.url_patterns,
            "fields": [
                {
                    "name": f.name,
                    "selector": f.selector,
                    "extract_type": f.extract_type,
                    "attribute": f.attribute,
                    "multiple": f.multiple,
                    "required": f.required,
                    "transform": f.transform,
                    "fallback_selectors": f.fallback_selectors,
                }
                for f in template.fields
            ],
            "pagination_selector": template.pagination_selector,
            "pagination_type": template.pagination_type,
            "max_pages": template.max_pages,
            "wait_for_selector": template.wait_for_selector,
            "wait_timeout": template.wait_timeout,
            "scroll_to_bottom": template.scroll_to_bottom,
            "javascript_required": template.javascript_required,
            "tags": template.tags,
        }
    
    def search_templates(
        self,
        query: Optional[str] = None,
        category: Optional[TemplateCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[ScrapingTemplate]:
        """Search templates by various criteria."""
        results = list(self._templates.values())
        
        if category:
            results = [t for t in results if t.category == category]
        
        if tags:
            results = [t for t in results if any(tag in t.tags for tag in tags)]
        
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower() or
                   query_lower in t.description.lower() or
                   any(query_lower in tag for tag in t.tags)
            ]
        
        return results


# Global template manager
template_manager = TemplateManager()

