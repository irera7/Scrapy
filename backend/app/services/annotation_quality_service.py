"""Inter-Annotator Agreement Service.

This service provides tools for measuring annotation quality
and agreement between multiple annotators.
"""
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from collections import defaultdict
import structlog
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.data_item import DataItem
from app.models.user import User

logger = structlog.get_logger()


class AnnotationAgreementCalculator:
    """Calculate inter-annotator agreement metrics."""
    
    @staticmethod
    def cohens_kappa(annotations1: List[str], annotations2: List[str]) -> float:
        """
        Calculate Cohen's Kappa for two annotators.
        
        Args:
            annotations1: Labels from annotator 1
            annotations2: Labels from annotator 2
            
        Returns:
            Kappa score (-1 to 1, where 1 is perfect agreement)
        """
        if len(annotations1) != len(annotations2):
            raise ValueError("Annotation lists must have same length")
        
        if not annotations1:
            return 0.0
        
        # Get all unique labels
        all_labels = list(set(annotations1 + annotations2))
        n = len(annotations1)
        
        # Build confusion matrix
        matrix = defaultdict(lambda: defaultdict(int))
        for a1, a2 in zip(annotations1, annotations2):
            matrix[a1][a2] += 1
        
        # Calculate observed agreement (Po)
        observed_agreement = sum(matrix[label][label] for label in all_labels) / n
        
        # Calculate expected agreement (Pe)
        expected_agreement = 0.0
        for label in all_labels:
            # Probability annotator 1 chooses this label
            p1 = sum(matrix[label][l] for l in all_labels) / n
            # Probability annotator 2 chooses this label
            p2 = sum(matrix[l][label] for l in all_labels) / n
            expected_agreement += p1 * p2
        
        # Calculate Kappa
        if expected_agreement == 1.0:
            return 1.0
        
        kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)
        return round(kappa, 4)
    
    @staticmethod
    def fleiss_kappa(annotations_matrix: List[List[str]]) -> float:
        """
        Calculate Fleiss' Kappa for multiple annotators.
        
        Args:
            annotations_matrix: List of lists, where each inner list
                               contains labels from all annotators for one item
                               
        Returns:
            Fleiss' Kappa score
        """
        if not annotations_matrix:
            return 0.0
        
        n_items = len(annotations_matrix)
        n_raters = len(annotations_matrix[0])
        
        # Get all unique categories
        all_categories = list(set(
            label for item_annotations in annotations_matrix 
            for label in item_annotations
        ))
        n_categories = len(all_categories)
        
        if n_categories == 0:
            return 0.0
        
        # Create category index mapping
        cat_to_idx = {cat: idx for idx, cat in enumerate(all_categories)}
        
        # Build counts matrix (n_items x n_categories)
        counts = [[0] * n_categories for _ in range(n_items)]
        for i, item_annotations in enumerate(annotations_matrix):
            for label in item_annotations:
                counts[i][cat_to_idx[label]] += 1
        
        # Calculate P_i (agreement for each item)
        P_i = []
        for i in range(n_items):
            sum_squared = sum(c * c for c in counts[i])
            P_i.append((sum_squared - n_raters) / (n_raters * (n_raters - 1)))
        
        # Calculate P_bar (mean agreement)
        P_bar = sum(P_i) / n_items if n_items > 0 else 0
        
        # Calculate p_j (proportion of all assignments to category j)
        p_j = []
        total_assignments = n_items * n_raters
        for j in range(n_categories):
            count_j = sum(counts[i][j] for i in range(n_items))
            p_j.append(count_j / total_assignments if total_assignments > 0 else 0)
        
        # Calculate P_e (expected agreement by chance)
        P_e = sum(p * p for p in p_j)
        
        # Calculate Fleiss' Kappa
        if P_e == 1.0:
            return 1.0
        
        kappa = (P_bar - P_e) / (1 - P_e)
        return round(kappa, 4)
    
    @staticmethod
    def krippendorffs_alpha(
        annotations_matrix: List[List[Optional[str]]],
        metric: str = "nominal"
    ) -> float:
        """
        Calculate Krippendorff's Alpha (handles missing data).
        
        Args:
            annotations_matrix: List of lists, can contain None for missing
            metric: Type of data ("nominal", "ordinal", "interval", "ratio")
            
        Returns:
            Alpha score (0 to 1)
        """
        # Filter out items with no valid annotations
        valid_items = []
        for item_annotations in annotations_matrix:
            valid = [a for a in item_annotations if a is not None]
            if len(valid) >= 2:  # Need at least 2 annotations
                valid_items.append(valid)
        
        if not valid_items:
            return 0.0
        
        # For nominal data, use simple observed/expected disagreement
        all_labels = list(set(
            label for item in valid_items for label in item
        ))
        
        if len(all_labels) <= 1:
            return 1.0  # Perfect agreement if only one label
        
        # Calculate observed disagreement
        observed_disagreement = 0.0
        total_pairs = 0
        
        for item in valid_items:
            n = len(item)
            for i in range(n):
                for j in range(i + 1, n):
                    if item[i] != item[j]:
                        observed_disagreement += 1
                    total_pairs += 1
        
        if total_pairs == 0:
            return 1.0
        
        observed_disagreement /= total_pairs
        
        # Calculate expected disagreement
        label_counts = defaultdict(int)
        total_annotations = 0
        for item in valid_items:
            for label in item:
                label_counts[label] += 1
                total_annotations += 1
        
        expected_disagreement = 0.0
        for l1 in all_labels:
            for l2 in all_labels:
                if l1 != l2:
                    p1 = label_counts[l1] / total_annotations
                    p2 = label_counts[l2] / total_annotations
                    expected_disagreement += p1 * p2
        
        if expected_disagreement == 0:
            return 1.0
        
        alpha = 1 - (observed_disagreement / expected_disagreement)
        return round(alpha, 4)
    
    @staticmethod
    def percentage_agreement(annotations1: List[str], annotations2: List[str]) -> float:
        """Calculate simple percentage agreement."""
        if len(annotations1) != len(annotations2):
            raise ValueError("Annotation lists must have same length")
        
        if not annotations1:
            return 0.0
        
        agreements = sum(1 for a, b in zip(annotations1, annotations2) if a == b)
        return round(agreements / len(annotations1), 4)
    
    @staticmethod
    def interpret_kappa(kappa: float) -> str:
        """Interpret Kappa score."""
        if kappa < 0:
            return "poor"
        elif kappa < 0.20:
            return "slight"
        elif kappa < 0.40:
            return "fair"
        elif kappa < 0.60:
            return "moderate"
        elif kappa < 0.80:
            return "substantial"
        else:
            return "almost_perfect"


class AnnotationQualityService:
    """Service for managing annotation quality and agreement."""
    
    def __init__(self):
        self.calculator = AnnotationAgreementCalculator()
    
    async def calculate_project_agreement(
        self,
        db: AsyncSession,
        project_id: UUID,
        annotation_field: str = "labels"
    ) -> Dict[str, Any]:
        """
        Calculate inter-annotator agreement for a project.
        
        This assumes items have been annotated by multiple annotators
        and annotations are stored with annotator info in metadata.
        """
        # Get items with annotations
        result = await db.execute(
            select(DataItem).where(
                and_(
                    DataItem.project_id == project_id,
                    DataItem.is_labeled == True
                )
            )
        )
        items = result.scalars().all()
        
        if not items:
            return {
                "error": "No labeled items found",
                "item_count": 0
            }
        
        # Group annotations by annotator
        annotator_labels: Dict[str, Dict[str, str]] = defaultdict(dict)
        
        for item in items:
            metadata = item.item_metadata or {}
            
            # Check if we have multi-annotator data
            if "annotators" in metadata:
                for annotator_id, annotation in metadata["annotators"].items():
                    label = annotation.get(annotation_field) or annotation.get("label")
                    if label:
                        if isinstance(label, list):
                            label = label[0] if label else None
                        if label:
                            annotator_labels[annotator_id][str(item.id)] = label
            else:
                # Single annotator - use created_by or default
                annotator_id = str(metadata.get("annotator_id", "default"))
                labels = item.labels
                if labels:
                    label = labels[0] if isinstance(labels, list) else labels
                    annotator_labels[annotator_id][str(item.id)] = label
        
        annotators = list(annotator_labels.keys())
        
        if len(annotators) < 2:
            return {
                "warning": "Less than 2 annotators found",
                "annotator_count": len(annotators),
                "item_count": len(items),
                "agreement_possible": False
            }
        
        # Calculate pairwise Cohen's Kappa
        pairwise_agreements = []
        
        for i, ann1 in enumerate(annotators):
            for ann2 in annotators[i+1:]:
                # Find common items
                common_items = set(annotator_labels[ann1].keys()) & set(annotator_labels[ann2].keys())
                
                if len(common_items) < 10:
                    continue
                
                labels1 = [annotator_labels[ann1][item_id] for item_id in common_items]
                labels2 = [annotator_labels[ann2][item_id] for item_id in common_items]
                
                kappa = self.calculator.cohens_kappa(labels1, labels2)
                percent_agree = self.calculator.percentage_agreement(labels1, labels2)
                
                pairwise_agreements.append({
                    "annotator_1": ann1,
                    "annotator_2": ann2,
                    "common_items": len(common_items),
                    "cohens_kappa": kappa,
                    "percentage_agreement": percent_agree,
                    "interpretation": self.calculator.interpret_kappa(kappa)
                })
        
        # Calculate overall Fleiss' Kappa if possible
        fleiss_kappa = None
        if len(annotators) >= 2:
            # Build matrix for Fleiss' Kappa
            all_item_ids = set()
            for ann_labels in annotator_labels.values():
                all_item_ids.update(ann_labels.keys())
            
            matrix = []
            for item_id in all_item_ids:
                item_labels = []
                for ann_id in annotators:
                    if item_id in annotator_labels[ann_id]:
                        item_labels.append(annotator_labels[ann_id][item_id])
                if len(item_labels) >= 2:
                    matrix.append(item_labels)
            
            if len(matrix) >= 10:
                fleiss_kappa = self.calculator.fleiss_kappa(matrix)
        
        # Calculate average agreement
        avg_kappa = 0.0
        avg_percent = 0.0
        if pairwise_agreements:
            avg_kappa = sum(p["cohens_kappa"] for p in pairwise_agreements) / len(pairwise_agreements)
            avg_percent = sum(p["percentage_agreement"] for p in pairwise_agreements) / len(pairwise_agreements)
        
        return {
            "project_id": str(project_id),
            "item_count": len(items),
            "annotator_count": len(annotators),
            "annotators": annotators,
            "pairwise_agreements": pairwise_agreements,
            "average_cohens_kappa": round(avg_kappa, 4),
            "average_percentage_agreement": round(avg_percent, 4),
            "fleiss_kappa": fleiss_kappa,
            "overall_interpretation": self.calculator.interpret_kappa(avg_kappa),
            "quality_threshold_met": avg_kappa >= 0.6,  # Substantial agreement
            "calculated_at": datetime.now().isoformat()
        }
    
    async def identify_disagreements(
        self,
        db: AsyncSession,
        project_id: UUID,
        min_annotators: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Identify items where annotators disagree.
        Returns items sorted by disagreement level.
        """
        result = await db.execute(
            select(DataItem).where(
                and_(
                    DataItem.project_id == project_id,
                    DataItem.is_labeled == True
                )
            )
        )
        items = result.scalars().all()
        
        disagreements = []
        
        for item in items:
            metadata = item.item_metadata or {}
            
            if "annotators" not in metadata:
                continue
            
            annotations = metadata["annotators"]
            if len(annotations) < min_annotators:
                continue
            
            # Get all labels for this item
            labels = []
            for ann_id, ann_data in annotations.items():
                label = ann_data.get("label") or ann_data.get("labels")
                if label:
                    if isinstance(label, list):
                        labels.extend(label)
                    else:
                        labels.append(label)
            
            if len(labels) < min_annotators:
                continue
            
            # Calculate disagreement
            unique_labels = set(labels)
            disagreement_score = 1 - (1 / len(unique_labels))
            
            if disagreement_score > 0:
                disagreements.append({
                    "item_id": str(item.id),
                    "data_type": item.data_type,
                    "content_preview": (item.content or "")[:200] if item.content else None,
                    "file_path": item.file_path,
                    "annotator_count": len(annotations),
                    "labels": labels,
                    "unique_labels": list(unique_labels),
                    "disagreement_score": round(disagreement_score, 3),
                    "needs_review": True
                })
        
        # Sort by disagreement score (highest first)
        disagreements.sort(key=lambda x: x["disagreement_score"], reverse=True)
        
        return disagreements
    
    async def create_review_task(
        self,
        db: AsyncSession,
        project_id: UUID,
        item_id: UUID,
        reviewer_id: UUID,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a review task for disputed annotations."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return {"error": "Item not found"}
        
        metadata = item.item_metadata or {}
        
        # Add review task
        if "review_tasks" not in metadata:
            metadata["review_tasks"] = []
        
        review_task = {
            "id": str(UUID()),
            "reviewer_id": str(reviewer_id),
            "status": "pending",
            "notes": notes,
            "created_at": datetime.now().isoformat()
        }
        
        metadata["review_tasks"].append(review_task)
        item.item_metadata = metadata
        
        await db.commit()
        
        return {
            "success": True,
            "task": review_task
        }
    
    async def resolve_disagreement(
        self,
        db: AsyncSession,
        item_id: UUID,
        final_label: str,
        resolver_id: UUID,
        resolution_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve a labeling disagreement with final decision."""
        result = await db.execute(
            select(DataItem).where(DataItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return {"error": "Item not found"}
        
        # Update label
        item.labels = [final_label]
        
        # Record resolution
        metadata = item.item_metadata or {}
        metadata["label_resolution"] = {
            "final_label": final_label,
            "resolver_id": str(resolver_id),
            "resolution_notes": resolution_notes,
            "resolved_at": datetime.now().isoformat(),
            "previous_labels": metadata.get("annotators", {})
        }
        item.item_metadata = metadata
        
        await db.commit()
        
        return {
            "success": True,
            "item_id": str(item_id),
            "final_label": final_label
        }


# Global instance
annotation_quality_service = AnnotationQualityService()
