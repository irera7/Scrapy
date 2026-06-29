"""GitHub scraper for repositories, code, and issues."""
from typing import List, Dict, Any, Optional
from uuid import UUID
import base64
import structlog
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.providers.base import BaseScraper
from app.scrapers.anti_detection import anti_detection
from app.models.data_item import DataItem

logger = structlog.get_logger()


class GitHubScraper(BaseScraper):
    """Scraper for GitHub content."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate GitHub scraper config."""
        valid_types = ["repo", "search_repos", "search_code", "readme", "issues", "commits", "releases", "contents"]
        return config.get("type") in valid_types
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def _api_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """Make GitHub API request."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}/{endpoint}",
                params=params,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    
    async def scrape(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Execute GitHub scraping."""
        scrape_type = config.get("type", "search_repos")
        items = []
        
        if scrape_type == "search_repos":
            items = await self._search_repos(config, project_id, db, job_id)
        elif scrape_type == "search_code":
            items = await self._search_code(config, project_id, db, job_id)
        elif scrape_type == "repo":
            items = await self._get_repo_info(config, project_id, db, job_id)
        elif scrape_type == "readme":
            items = await self._get_readme(config, project_id, db, job_id)
        elif scrape_type == "issues":
            items = await self._get_issues(config, project_id, db, job_id)
        elif scrape_type == "commits":
            items = await self._get_commits(config, project_id, db, job_id)
        elif scrape_type == "releases":
            items = await self._get_releases(config, project_id, db, job_id)
        elif scrape_type == "contents":
            items = await self._get_contents(config, project_id, db, job_id)
        
        await db.commit()
        return items
    
    async def _search_repos(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Search GitHub repositories."""
        query = config.get("query", "")
        max_results = min(config.get("max_results", 100), 1000)
        sort = config.get("sort", "stars")  # stars, forks, updated
        order = config.get("order", "desc")
        language = config.get("language")
        
        # Build query
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        logger.info(f"GitHub repo search: {search_query}")
        
        items = []
        page = 1
        per_page = min(100, max_results)
        
        while len(items) < max_results:
            data = await self._api_request("search/repositories", {
                "q": search_query,
                "sort": sort,
                "order": order,
                "page": page,
                "per_page": per_page
            })
            
            for repo in data.get("items", []):
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="structured",
                    source_url=repo.get("html_url"),
                    content=repo.get("description", ""),
                    item_metadata={
                        "platform": "github",
                        "type": "repository",
                        "repo_id": repo.get("id"),
                        "name": repo.get("name"),
                        "full_name": repo.get("full_name"),
                        "owner": repo.get("owner", {}).get("login"),
                        "language": repo.get("language"),
                        "stars": repo.get("stargazers_count"),
                        "forks": repo.get("forks_count"),
                        "watchers": repo.get("watchers_count"),
                        "open_issues": repo.get("open_issues_count"),
                        "topics": repo.get("topics", []),
                        "license": repo.get("license", {}).get("spdx_id") if repo.get("license") else None,
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                        "default_branch": repo.get("default_branch"),
                    }
                )
                db.add(item)
                items.append(item)
            
            if len(data.get("items", [])) < per_page:
                break
            
            page += 1
            
            if page > 10:  # GitHub API limit
                break
        
        logger.info(f"Found {len(items)} repositories")
        return [{"id": str(item.id)} for item in items]
    
    async def _search_code(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Search code on GitHub."""
        query = config.get("query", "")
        max_results = min(config.get("max_results", 100), 1000)
        language = config.get("language")
        extension = config.get("extension")
        repo = config.get("repo")  # Optional: limit to specific repo
        
        # Build query
        search_query = query
        if language:
            search_query += f" language:{language}"
        if extension:
            search_query += f" extension:{extension}"
        if repo:
            search_query += f" repo:{repo}"
        
        logger.info(f"GitHub code search: {search_query}")
        
        items = []
        page = 1
        per_page = min(100, max_results)
        
        while len(items) < max_results:
            data = await self._api_request("search/code", {
                "q": search_query,
                "page": page,
                "per_page": per_page
            })
            
            for code_item in data.get("items", []):
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="text",
                    source_url=code_item.get("html_url"),
                    content="",  # Will be filled by fetching content
                    item_metadata={
                        "platform": "github",
                        "type": "code",
                        "name": code_item.get("name"),
                        "path": code_item.get("path"),
                        "sha": code_item.get("sha"),
                        "repository": code_item.get("repository", {}).get("full_name"),
                        "score": code_item.get("score"),
                    }
                )
                
                # Optionally fetch actual content
                if config.get("fetch_content", True):
                    try:
                        content_url = code_item.get("url")
                        if content_url:
                            async with httpx.AsyncClient() as client:
                                response = await client.get(
                                    content_url,
                                    headers=self._get_headers(),
                                    timeout=30
                                )
                                if response.status_code == 200:
                                    content_data = response.json()
                                    if content_data.get("encoding") == "base64":
                                        item.content = base64.b64decode(content_data.get("content", "")).decode("utf-8", errors="ignore")
                                    else:
                                        item.content = content_data.get("content", "")
                    except Exception as e:
                        logger.warning(f"Failed to fetch code content: {e}")
                
                db.add(item)
                items.append(item)
            
            if len(data.get("items", [])) < per_page:
                break
            
            page += 1
            
            if page > 10:
                break
        
        logger.info(f"Found {len(items)} code files")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_readme(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get repository README."""
        owner = config.get("owner")
        repo = config.get("repo")
        
        if not owner or not repo:
            raise ValueError("owner and repo required")
        
        items = []
        
        try:
            data = await self._api_request(f"repos/{owner}/{repo}/readme")
            
            content = ""
            if data.get("encoding") == "base64":
                content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
            else:
                content = data.get("content", "")
            
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="text",
                source_url=data.get("html_url"),
                content=content,
                item_metadata={
                    "platform": "github",
                    "type": "readme",
                    "repository": f"{owner}/{repo}",
                    "name": data.get("name"),
                    "path": data.get("path"),
                    "sha": data.get("sha"),
                    "size": data.get("size"),
                }
            )
            db.add(item)
            items.append(item)
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"No README found for {owner}/{repo}")
            else:
                raise
        
        return [{"id": str(item.id)} for item in items]
    
    async def _get_issues(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get repository issues."""
        owner = config.get("owner")
        repo = config.get("repo")
        state = config.get("state", "all")  # open, closed, all
        max_results = config.get("max_results", 100)
        
        if not owner or not repo:
            raise ValueError("owner and repo required")
        
        items = []
        page = 1
        per_page = min(100, max_results)
        
        while len(items) < max_results:
            data = await self._api_request(f"repos/{owner}/{repo}/issues", {
                "state": state,
                "page": page,
                "per_page": per_page
            })
            
            if not data:
                break
            
            for issue in data:
                # Skip pull requests
                if "pull_request" in issue:
                    continue
                
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="text",
                    source_url=issue.get("html_url"),
                    content=f"{issue.get('title', '')}\n\n{issue.get('body', '')}",
                    item_metadata={
                        "platform": "github",
                        "type": "issue",
                        "repository": f"{owner}/{repo}",
                        "issue_number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "author": issue.get("user", {}).get("login"),
                        "labels": [l.get("name") for l in issue.get("labels", [])],
                        "comments_count": issue.get("comments"),
                        "created_at": issue.get("created_at"),
                        "updated_at": issue.get("updated_at"),
                        "closed_at": issue.get("closed_at"),
                    }
                )
                db.add(item)
                items.append(item)
            
            if len(data) < per_page:
                break
            
            page += 1
        
        logger.info(f"Collected {len(items)} issues from {owner}/{repo}")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_commits(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get repository commits."""
        owner = config.get("owner")
        repo = config.get("repo")
        max_results = config.get("max_results", 100)
        branch = config.get("branch")
        
        if not owner or not repo:
            raise ValueError("owner and repo required")
        
        items = []
        page = 1
        per_page = min(100, max_results)
        
        params = {"page": page, "per_page": per_page}
        if branch:
            params["sha"] = branch
        
        while len(items) < max_results:
            data = await self._api_request(f"repos/{owner}/{repo}/commits", params)
            
            if not data:
                break
            
            for commit in data:
                commit_data = commit.get("commit", {})
                
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="text",
                    source_url=commit.get("html_url"),
                    content=commit_data.get("message", ""),
                    item_metadata={
                        "platform": "github",
                        "type": "commit",
                        "repository": f"{owner}/{repo}",
                        "sha": commit.get("sha"),
                        "author": commit_data.get("author", {}).get("name"),
                        "author_email": commit_data.get("author", {}).get("email"),
                        "committer": commit_data.get("committer", {}).get("name"),
                        "date": commit_data.get("author", {}).get("date"),
                        "stats": commit.get("stats", {}),
                    }
                )
                db.add(item)
                items.append(item)
            
            if len(data) < per_page:
                break
            
            page += 1
            params["page"] = page
        
        logger.info(f"Collected {len(items)} commits from {owner}/{repo}")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_releases(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get repository releases."""
        owner = config.get("owner")
        repo = config.get("repo")
        max_results = config.get("max_results", 50)
        
        if not owner or not repo:
            raise ValueError("owner and repo required")
        
        items = []
        
        data = await self._api_request(f"repos/{owner}/{repo}/releases", {
            "per_page": min(100, max_results)
        })
        
        for release in data[:max_results]:
            item = DataItem(
                project_id=project_id,
                job_id=job_id,
                data_type="structured",
                source_url=release.get("html_url"),
                content=release.get("body", ""),
                item_metadata={
                    "platform": "github",
                    "type": "release",
                    "repository": f"{owner}/{repo}",
                    "release_id": release.get("id"),
                    "tag_name": release.get("tag_name"),
                    "name": release.get("name"),
                    "author": release.get("author", {}).get("login"),
                    "prerelease": release.get("prerelease"),
                    "draft": release.get("draft"),
                    "created_at": release.get("created_at"),
                    "published_at": release.get("published_at"),
                    "assets": [
                        {
                            "name": a.get("name"),
                            "size": a.get("size"),
                            "download_url": a.get("browser_download_url"),
                            "download_count": a.get("download_count"),
                        }
                        for a in release.get("assets", [])
                    ]
                }
            )
            db.add(item)
            items.append(item)
        
        logger.info(f"Collected {len(items)} releases from {owner}/{repo}")
        return [{"id": str(item.id)} for item in items]
    
    async def _get_repo_info(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed repository information."""
        owner = config.get("owner")
        repo = config.get("repo")
        
        if not owner or not repo:
            raise ValueError("owner and repo required")
        
        items = []
        
        data = await self._api_request(f"repos/{owner}/{repo}")
        
        item = DataItem(
            project_id=project_id,
            job_id=job_id,
            data_type="structured",
            source_url=data.get("html_url"),
            content=data.get("description", ""),
            item_metadata={
                "platform": "github",
                "type": "repository_info",
                "repo_id": data.get("id"),
                "name": data.get("name"),
                "full_name": data.get("full_name"),
                "owner": data.get("owner", {}).get("login"),
                "private": data.get("private"),
                "language": data.get("language"),
                "languages_url": data.get("languages_url"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "watchers": data.get("watchers_count"),
                "open_issues": data.get("open_issues_count"),
                "topics": data.get("topics", []),
                "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "pushed_at": data.get("pushed_at"),
                "size": data.get("size"),
                "default_branch": data.get("default_branch"),
                "has_wiki": data.get("has_wiki"),
                "has_pages": data.get("has_pages"),
                "has_discussions": data.get("has_discussions"),
                "archived": data.get("archived"),
                "subscribers_count": data.get("subscribers_count"),
                "network_count": data.get("network_count"),
            }
        )
        db.add(item)
        items.append(item)
        
        return [{"id": str(item.id)} for item in items]
    
    async def _get_contents(
        self,
        config: Dict[str, Any],
        project_id: UUID,
        db: AsyncSession,
        job_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get repository contents (files and directories)."""
        owner = config.get("owner")
        repo = config.get("repo")
        path = config.get("path", "")
        recursive = config.get("recursive", False)
        extensions = config.get("extensions", [])  # Filter by file extension
        
        if not owner or not repo:
            raise ValueError("owner and repo required")
        
        items = []
        
        async def fetch_contents(current_path: str):
            data = await self._api_request(f"repos/{owner}/{repo}/contents/{current_path}")
            
            if isinstance(data, list):
                # Directory
                for entry in data:
                    if entry.get("type") == "file":
                        # Check extension filter
                        if extensions:
                            ext = entry.get("name", "").split(".")[-1] if "." in entry.get("name", "") else ""
                            if ext not in extensions:
                                continue
                        
                        # Fetch file content
                        content = ""
                        if config.get("fetch_content", True):
                            try:
                                file_data = await self._api_request(f"repos/{owner}/{repo}/contents/{entry.get('path')}")
                                if file_data.get("encoding") == "base64":
                                    content = base64.b64decode(file_data.get("content", "")).decode("utf-8", errors="ignore")
                            except Exception as e:
                                logger.warning(f"Failed to fetch content: {e}")
                        
                        item = DataItem(
                            project_id=project_id,
                            job_id=job_id,
                            data_type="text",
                            source_url=entry.get("html_url"),
                            content=content,
                            item_metadata={
                                "platform": "github",
                                "type": "file",
                                "repository": f"{owner}/{repo}",
                                "name": entry.get("name"),
                                "path": entry.get("path"),
                                "sha": entry.get("sha"),
                                "size": entry.get("size"),
                            }
                        )
                        db.add(item)
                        items.append(item)
                    
                    elif entry.get("type") == "dir" and recursive:
                        await fetch_contents(entry.get("path"))
            else:
                # Single file
                content = ""
                if data.get("encoding") == "base64":
                    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
                
                item = DataItem(
                    project_id=project_id,
                    job_id=job_id,
                    data_type="text",
                    source_url=data.get("html_url"),
                    content=content,
                    item_metadata={
                        "platform": "github",
                        "type": "file",
                        "repository": f"{owner}/{repo}",
                        "name": data.get("name"),
                        "path": data.get("path"),
                        "sha": data.get("sha"),
                        "size": data.get("size"),
                    }
                )
                db.add(item)
                items.append(item)
        
        await fetch_contents(path)
        
        logger.info(f"Collected {len(items)} files from {owner}/{repo}")
        return [{"id": str(item.id)} for item in items]

