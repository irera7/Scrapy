"""Backup Service for Dataset Protection.

Provides automated and manual backup capabilities:
- Database backups
- File storage backups
- Version snapshots
- Restore functionality
"""
import os
import json
import gzip
import shutil
import tarfile
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import structlog
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.data_item import DataItem
from app.models.project import Project
from app.models.dataset import DatasetVersion, DatasetCard
from app.core.storage import storage_service
from app.core.config import settings

logger = structlog.get_logger()


class BackupService:
    """Service for creating and managing backups."""
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = backup_dir or os.path.join(os.getcwd(), "backups")
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
    
    async def create_project_backup(
        self,
        db: AsyncSession,
        project_id: UUID,
        include_files: bool = True,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        Create a full backup of a project.
        
        Includes:
        - All data items with metadata
        - Dataset versions
        - Dataset card
        - Annotation types
        - Augmentation rules
        - Optionally: media files
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"project_{project_id}_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        os.makedirs(backup_path, exist_ok=True)
        
        try:
            # Get project info
            project_result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                return {"error": "Project not found"}
            
            backup_manifest = {
                "backup_id": backup_name,
                "project_id": str(project_id),
                "project_name": project.name,
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "components": []
            }
            
            # Backup project metadata
            project_data = {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "data_type": project.data_type,
                "created_at": project.created_at.isoformat() if project.created_at else None,
            }
            
            with open(os.path.join(backup_path, "project.json"), "w", encoding="utf-8") as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            backup_manifest["components"].append("project.json")
            
            # Backup data items
            items_result = await db.execute(
                select(DataItem).where(DataItem.project_id == project_id)
            )
            items = items_result.scalars().all()
            
            items_data = []
            file_paths = []
            
            for item in items:
                item_dict = {
                    "id": str(item.id),
                    "data_type": item.data_type,
                    "source_url": item.source_url,
                    "content": item.content,
                    "file_path": item.file_path,
                    "file_size": item.file_size,
                    "mime_type": item.mime_type,
                    "metadata": item.item_metadata,
                    "labels": item.labels,
                    "quality_score": item.quality_score,
                    "is_processed": item.is_processed,
                    "is_labeled": item.is_labeled,
                    "dataset_split": item.dataset_split,
                    "annotations": item.annotations,
                    "augmented_from": str(item.augmented_from) if item.augmented_from else None,
                    "augmentation_type": item.augmentation_type,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                items_data.append(item_dict)
                
                if item.file_path:
                    file_paths.append(item.file_path)
            
            with open(os.path.join(backup_path, "data_items.json"), "w", encoding="utf-8") as f:
                json.dump(items_data, f, ensure_ascii=False, indent=2)
            
            backup_manifest["components"].append("data_items.json")
            backup_manifest["item_count"] = len(items_data)
            
            # Backup dataset versions
            versions_result = await db.execute(
                select(DatasetVersion).where(DatasetVersion.project_id == project_id)
            )
            versions = versions_result.scalars().all()
            
            versions_data = []
            for version in versions:
                versions_data.append({
                    "id": str(version.id),
                    "version": version.version,
                    "description": version.description,
                    "item_count": version.item_count,
                    "train_count": version.train_count,
                    "val_count": version.val_count,
                    "test_count": version.test_count,
                    "item_ids": version.item_ids,
                    "split_config": version.split_config,
                    "statistics": version.statistics,
                    "is_published": version.is_published,
                    "created_at": version.created_at.isoformat() if version.created_at else None,
                })
            
            if versions_data:
                with open(os.path.join(backup_path, "dataset_versions.json"), "w", encoding="utf-8") as f:
                    json.dump(versions_data, f, ensure_ascii=False, indent=2)
                backup_manifest["components"].append("dataset_versions.json")
            
            # Backup dataset card
            card_result = await db.execute(
                select(DatasetCard).where(DatasetCard.project_id == project_id)
            )
            card = card_result.scalar_one_or_none()
            
            if card:
                card_data = {
                    "id": str(card.id),
                    "title": card.title,
                    "description": card.description,
                    "homepage": card.homepage,
                    "license": card.license,
                    "citation": card.citation,
                    "languages": card.languages,
                    "task_categories": card.task_categories,
                    "task_ids": card.task_ids,
                    "size_categories": card.size_categories,
                    "source_datasets": card.source_datasets,
                    "annotations_creators": card.annotations_creators,
                    "language_creators": card.language_creators,
                    "multilinguality": card.multilinguality,
                    "pretty_name": card.pretty_name,
                    "tags": card.tags,
                    "configs": card.configs,
                    "bias_risks": card.bias_risks,
                    "ethical_considerations": card.ethical_considerations,
                    "curation_rationale": card.curation_rationale,
                }
                
                with open(os.path.join(backup_path, "dataset_card.json"), "w", encoding="utf-8") as f:
                    json.dump(card_data, f, ensure_ascii=False, indent=2)
                backup_manifest["components"].append("dataset_card.json")
            
            # Backup files if requested
            if include_files and file_paths:
                files_dir = os.path.join(backup_path, "files")
                os.makedirs(files_dir, exist_ok=True)
                
                files_backed_up = 0
                for file_path in file_paths:
                    try:
                        file_data = storage_service.download_file(file_path)
                        # Create subdirectory structure
                        file_name = os.path.basename(file_path)
                        local_path = os.path.join(files_dir, file_name)
                        
                        with open(local_path, "wb") as f:
                            f.write(file_data)
                        files_backed_up += 1
                    except Exception as e:
                        logger.warning(f"Could not backup file {file_path}: {e}")
                
                backup_manifest["files_backed_up"] = files_backed_up
                backup_manifest["components"].append("files/")
            
            # Save manifest
            with open(os.path.join(backup_path, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(backup_manifest, f, ensure_ascii=False, indent=2)
            
            # Compress if requested
            final_path = backup_path
            if compress:
                archive_path = f"{backup_path}.tar.gz"
                with tarfile.open(archive_path, "w:gz") as tar:
                    tar.add(backup_path, arcname=backup_name)
                
                # Remove uncompressed directory
                shutil.rmtree(backup_path)
                final_path = archive_path
                backup_manifest["compressed"] = True
            
            return {
                "success": True,
                "backup_id": backup_name,
                "backup_path": final_path,
                "manifest": backup_manifest
            }
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Cleanup on failure
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            return {"error": str(e)}
    
    async def restore_project_backup(
        self,
        db: AsyncSession,
        backup_path: str,
        user_id: UUID,
        new_project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Restore a project from backup.
        
        Creates a new project with the backed up data.
        """
        import uuid as uuid_module
        
        try:
            # Extract if compressed
            if backup_path.endswith(".tar.gz"):
                extract_dir = backup_path.replace(".tar.gz", "_extracted")
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
                
                # Find the backup directory
                subdirs = os.listdir(extract_dir)
                backup_dir = os.path.join(extract_dir, subdirs[0]) if subdirs else extract_dir
            else:
                backup_dir = backup_path
                extract_dir = None
            
            # Read manifest
            manifest_path = os.path.join(backup_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                return {"error": "Invalid backup: manifest.json not found"}
            
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            # Read project data
            with open(os.path.join(backup_dir, "project.json"), "r", encoding="utf-8") as f:
                project_data = json.load(f)
            
            # Create new project
            new_project = Project(
                id=uuid_module.uuid4(),
                user_id=user_id,
                name=new_project_name or f"{project_data['name']} (Restored)",
                description=project_data.get('description'),
                data_type=project_data.get('data_type', 'text'),
            )
            db.add(new_project)
            
            # Map old IDs to new IDs
            id_mapping = {}
            
            # Restore data items
            items_path = os.path.join(backup_dir, "data_items.json")
            if os.path.exists(items_path):
                with open(items_path, "r", encoding="utf-8") as f:
                    items_data = json.load(f)
                
                for item_data in items_data:
                    old_id = item_data["id"]
                    new_id = uuid_module.uuid4()
                    id_mapping[old_id] = str(new_id)
                    
                    new_item = DataItem(
                        id=new_id,
                        project_id=new_project.id,
                        data_type=item_data["data_type"],
                        source_url=item_data.get("source_url"),
                        content=item_data.get("content"),
                        file_path=item_data.get("file_path"),
                        file_size=item_data.get("file_size"),
                        mime_type=item_data.get("mime_type"),
                        item_metadata=item_data.get("metadata", {}),
                        labels=item_data.get("labels", []),
                        quality_score=item_data.get("quality_score"),
                        is_processed=item_data.get("is_processed", False),
                        is_labeled=item_data.get("is_labeled", False),
                        dataset_split=item_data.get("dataset_split", "unassigned"),
                        annotations=item_data.get("annotations", {}),
                        augmentation_type=item_data.get("augmentation_type"),
                    )
                    db.add(new_item)
            
            # Restore dataset card
            card_path = os.path.join(backup_dir, "dataset_card.json")
            if os.path.exists(card_path):
                with open(card_path, "r", encoding="utf-8") as f:
                    card_data = json.load(f)
                
                new_card = DatasetCard(
                    id=uuid_module.uuid4(),
                    project_id=new_project.id,
                    title=card_data.get("title", new_project.name),
                    description=card_data.get("description"),
                    homepage=card_data.get("homepage"),
                    license=card_data.get("license"),
                    citation=card_data.get("citation"),
                    languages=card_data.get("languages", []),
                    task_categories=card_data.get("task_categories", []),
                    task_ids=card_data.get("task_ids", []),
                    size_categories=card_data.get("size_categories"),
                    source_datasets=card_data.get("source_datasets", []),
                    annotations_creators=card_data.get("annotations_creators", []),
                    language_creators=card_data.get("language_creators", []),
                    multilinguality=card_data.get("multilinguality"),
                    pretty_name=card_data.get("pretty_name"),
                    tags=card_data.get("tags", []),
                    configs=card_data.get("configs", []),
                    bias_risks=card_data.get("bias_risks"),
                    ethical_considerations=card_data.get("ethical_considerations"),
                    curation_rationale=card_data.get("curation_rationale"),
                )
                db.add(new_card)
            
            await db.commit()
            
            # Cleanup extracted files
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            
            return {
                "success": True,
                "new_project_id": str(new_project.id),
                "new_project_name": new_project.name,
                "items_restored": len(id_mapping),
                "id_mapping": id_mapping
            }
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            await db.rollback()
            return {"error": str(e)}
    
    def list_backups(self, project_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        
        for entry in os.listdir(self.backup_dir):
            entry_path = os.path.join(self.backup_dir, entry)
            
            # Check if it matches our backup pattern
            if entry.startswith("project_"):
                # Filter by project if specified
                if project_id:
                    if str(project_id) not in entry:
                        continue
                
                is_compressed = entry.endswith(".tar.gz")
                
                backup_info = {
                    "name": entry,
                    "path": entry_path,
                    "compressed": is_compressed,
                    "size_bytes": os.path.getsize(entry_path) if os.path.isfile(entry_path) else None,
                    "modified_at": datetime.fromtimestamp(os.path.getmtime(entry_path)).isoformat()
                }
                
                # Try to read manifest
                if is_compressed:
                    try:
                        with tarfile.open(entry_path, "r:gz") as tar:
                            for member in tar.getmembers():
                                if member.name.endswith("manifest.json"):
                                    f = tar.extractfile(member)
                                    if f:
                                        manifest = json.load(f)
                                        backup_info["manifest"] = manifest
                                    break
                    except:
                        pass
                else:
                    manifest_path = os.path.join(entry_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        with open(manifest_path, "r") as f:
                            backup_info["manifest"] = json.load(f)
                
                backups.append(backup_info)
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x["modified_at"], reverse=True)
        
        return backups
    
    def delete_backup(self, backup_name: str) -> Dict[str, Any]:
        """Delete a backup."""
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            return {"error": "Backup not found"}
        
        try:
            if os.path.isfile(backup_path):
                os.remove(backup_path)
            else:
                shutil.rmtree(backup_path)
            
            return {"success": True, "deleted": backup_name}
        except Exception as e:
            return {"error": str(e)}
    
    async def cleanup_old_backups(
        self,
        max_age_days: int = 30,
        max_backups_per_project: int = 5
    ) -> Dict[str, Any]:
        """
        Cleanup old backups.
        
        Args:
            max_age_days: Delete backups older than this
            max_backups_per_project: Keep only this many backups per project
        """
        deleted = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        # Group backups by project
        project_backups: Dict[str, List[Dict]] = {}
        
        for backup in self.list_backups():
            # Extract project ID from name
            parts = backup["name"].split("_")
            if len(parts) >= 2:
                project_id = parts[1]
                if project_id not in project_backups:
                    project_backups[project_id] = []
                project_backups[project_id].append(backup)
        
        # Delete old backups
        for entry in os.listdir(self.backup_dir):
            entry_path = os.path.join(self.backup_dir, entry)
            mod_time = datetime.fromtimestamp(os.path.getmtime(entry_path))
            
            if mod_time < cutoff_date:
                result = self.delete_backup(entry)
                if result.get("success"):
                    deleted.append(entry)
        
        # Keep only max_backups_per_project
        for project_id, backups in project_backups.items():
            if len(backups) > max_backups_per_project:
                # Sort by date (newest first) and delete excess
                backups.sort(key=lambda x: x["modified_at"], reverse=True)
                for backup in backups[max_backups_per_project:]:
                    result = self.delete_backup(backup["name"])
                    if result.get("success"):
                        deleted.append(backup["name"])
        
        return {
            "deleted_count": len(deleted),
            "deleted_backups": deleted
        }


# Global instance
backup_service = BackupService()
