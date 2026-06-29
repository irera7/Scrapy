"""Data Validation Service.

Provides comprehensive data validation including:
- Schema validation for structured data
- Missing values management
- Outlier detection
- Data type validation
- Temporal split for time series
"""
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from uuid import UUID
from datetime import datetime, timedelta
from collections import defaultdict
import json
import re
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.data_item import DataItem

logger = structlog.get_logger()


class SchemaValidator:
    """Validate data against defined schemas."""
    
    # Supported field types
    FIELD_TYPES = {
        "string": str,
        "integer": int,
        "float": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
        "email": str,
        "url": str,
        "date": str,
        "datetime": str,
    }
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize with schema definition.
        
        Schema format:
        {
            "fields": {
                "name": {"type": "string", "required": True, "min_length": 1},
                "age": {"type": "integer", "min": 0, "max": 150},
                "email": {"type": "email", "required": True},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "allow_extra_fields": False
        }
        """
        self.schema = schema
        self.fields = schema.get("fields", {})
        self.allow_extra = schema.get("allow_extra_fields", True)
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against schema.
        
        Returns:
            {
                "valid": bool,
                "errors": List[Dict],
                "warnings": List[Dict]
            }
        """
        errors = []
        warnings = []
        
        if not isinstance(data, dict):
            return {
                "valid": False,
                "errors": [{"message": "Data must be an object"}],
                "warnings": []
            }
        
        # Check required fields
        for field_name, field_schema in self.fields.items():
            if field_schema.get("required", False):
                if field_name not in data or data[field_name] is None:
                    errors.append({
                        "field": field_name,
                        "error": "required_field_missing",
                        "message": f"Required field '{field_name}' is missing"
                    })
        
        # Validate each field
        for field_name, value in data.items():
            if field_name not in self.fields:
                if not self.allow_extra:
                    warnings.append({
                        "field": field_name,
                        "warning": "extra_field",
                        "message": f"Extra field '{field_name}' not in schema"
                    })
                continue
            
            field_schema = self.fields[field_name]
            field_errors = self._validate_field(field_name, value, field_schema)
            errors.extend(field_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_field(
        self, 
        field_name: str, 
        value: Any, 
        field_schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate a single field."""
        errors = []
        
        # Handle null values
        if value is None:
            if field_schema.get("required", False):
                errors.append({
                    "field": field_name,
                    "error": "null_value",
                    "message": f"Field '{field_name}' cannot be null"
                })
            return errors
        
        field_type = field_schema.get("type", "string")
        
        # Type validation
        type_error = self._validate_type(field_name, value, field_type)
        if type_error:
            errors.append(type_error)
            return errors  # Skip other validations if type is wrong
        
        # String validations
        if field_type == "string" and isinstance(value, str):
            if "min_length" in field_schema and len(value) < field_schema["min_length"]:
                errors.append({
                    "field": field_name,
                    "error": "min_length",
                    "message": f"Field '{field_name}' is too short (min: {field_schema['min_length']})"
                })
            
            if "max_length" in field_schema and len(value) > field_schema["max_length"]:
                errors.append({
                    "field": field_name,
                    "error": "max_length",
                    "message": f"Field '{field_name}' is too long (max: {field_schema['max_length']})"
                })
            
            if "pattern" in field_schema:
                if not re.match(field_schema["pattern"], value):
                    errors.append({
                        "field": field_name,
                        "error": "pattern_mismatch",
                        "message": f"Field '{field_name}' doesn't match required pattern"
                    })
        
        # Numeric validations
        if field_type in ["integer", "float"] and isinstance(value, (int, float)):
            if "min" in field_schema and value < field_schema["min"]:
                errors.append({
                    "field": field_name,
                    "error": "below_minimum",
                    "message": f"Field '{field_name}' is below minimum ({field_schema['min']})"
                })
            
            if "max" in field_schema and value > field_schema["max"]:
                errors.append({
                    "field": field_name,
                    "error": "above_maximum",
                    "message": f"Field '{field_name}' is above maximum ({field_schema['max']})"
                })
        
        # Array validations
        if field_type == "array" and isinstance(value, list):
            if "min_items" in field_schema and len(value) < field_schema["min_items"]:
                errors.append({
                    "field": field_name,
                    "error": "too_few_items",
                    "message": f"Field '{field_name}' has too few items (min: {field_schema['min_items']})"
                })
            
            if "max_items" in field_schema and len(value) > field_schema["max_items"]:
                errors.append({
                    "field": field_name,
                    "error": "too_many_items",
                    "message": f"Field '{field_name}' has too many items (max: {field_schema['max_items']})"
                })
        
        # Enum validation
        if "enum" in field_schema and value not in field_schema["enum"]:
            errors.append({
                "field": field_name,
                "error": "invalid_enum_value",
                "message": f"Field '{field_name}' must be one of: {field_schema['enum']}"
            })
        
        return errors
    
    def _validate_type(
        self, 
        field_name: str, 
        value: Any, 
        expected_type: str
    ) -> Optional[Dict[str, Any]]:
        """Validate field type."""
        if expected_type == "email":
            if not isinstance(value, str) or not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', value):
                return {
                    "field": field_name,
                    "error": "invalid_email",
                    "message": f"Field '{field_name}' is not a valid email"
                }
        
        elif expected_type == "url":
            if not isinstance(value, str) or not re.match(r'^https?://\S+$', value):
                return {
                    "field": field_name,
                    "error": "invalid_url",
                    "message": f"Field '{field_name}' is not a valid URL"
                }
        
        elif expected_type == "date":
            try:
                if isinstance(value, str):
                    datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return {
                    "field": field_name,
                    "error": "invalid_date",
                    "message": f"Field '{field_name}' is not a valid date (YYYY-MM-DD)"
                }
        
        elif expected_type == "datetime":
            try:
                if isinstance(value, str):
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return {
                    "field": field_name,
                    "error": "invalid_datetime",
                    "message": f"Field '{field_name}' is not a valid datetime"
                }
        
        elif expected_type in self.FIELD_TYPES:
            expected = self.FIELD_TYPES[expected_type]
            if not isinstance(value, expected):
                return {
                    "field": field_name,
                    "error": "type_mismatch",
                    "message": f"Field '{field_name}' should be {expected_type}, got {type(value).__name__}"
                }
        
        return None


class MissingValuesHandler:
    """Handle missing values in datasets."""
    
    @staticmethod
    def analyze_missing(data_items: List[Dict[str, Any]], fields: List[str] = None) -> Dict[str, Any]:
        """
        Analyze missing values in a dataset.
        
        Returns statistics about missing values per field.
        """
        if not data_items:
            return {"error": "No data provided"}
        
        total_items = len(data_items)
        
        # Determine fields to check
        if not fields:
            # Get all unique fields
            all_fields: Set[str] = set()
            for item in data_items:
                if isinstance(item, dict):
                    all_fields.update(item.keys())
            fields = list(all_fields)
        
        # Count missing per field
        missing_stats = {}
        for field in fields:
            missing_count = 0
            null_count = 0
            empty_count = 0
            
            for item in data_items:
                if not isinstance(item, dict):
                    continue
                
                if field not in item:
                    missing_count += 1
                elif item[field] is None:
                    null_count += 1
                elif isinstance(item[field], str) and item[field].strip() == "":
                    empty_count += 1
            
            total_missing = missing_count + null_count + empty_count
            missing_stats[field] = {
                "missing": missing_count,
                "null": null_count,
                "empty_string": empty_count,
                "total_missing": total_missing,
                "missing_ratio": round(total_missing / total_items, 4),
                "completeness": round(1 - (total_missing / total_items), 4)
            }
        
        # Overall statistics
        overall_missing = sum(s["total_missing"] for s in missing_stats.values())
        total_cells = total_items * len(fields)
        
        return {
            "total_items": total_items,
            "fields_analyzed": len(fields),
            "field_stats": missing_stats,
            "overall_completeness": round(1 - (overall_missing / total_cells), 4) if total_cells > 0 else 1.0,
            "fields_with_missing": [f for f, s in missing_stats.items() if s["total_missing"] > 0]
        }
    
    @staticmethod
    def impute_values(
        data: Dict[str, Any],
        strategy: Dict[str, str],
        reference_data: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Impute missing values using specified strategies.
        
        Strategies:
        - "mean": Replace with mean (numeric)
        - "median": Replace with median (numeric)
        - "mode": Replace with most common value
        - "constant": Replace with specified constant
        - "drop": Mark for removal
        """
        imputed = data.copy()
        imputation_log = []
        
        for field, method in strategy.items():
            if field not in data or data[field] is None or (isinstance(data[field], str) and data[field].strip() == ""):
                # Need to impute
                if method == "drop":
                    imputation_log.append({
                        "field": field,
                        "action": "mark_for_drop"
                    })
                    imputed["_should_drop"] = True
                
                elif method.startswith("constant:"):
                    constant_value = method.split(":", 1)[1]
                    imputed[field] = constant_value
                    imputation_log.append({
                        "field": field,
                        "action": "constant",
                        "value": constant_value
                    })
                
                elif method in ["mean", "median", "mode"] and reference_data:
                    values = [
                        d[field] for d in reference_data 
                        if field in d and d[field] is not None
                    ]
                    
                    if values:
                        if method == "mean":
                            numeric_values = [v for v in values if isinstance(v, (int, float))]
                            if numeric_values:
                                imputed[field] = sum(numeric_values) / len(numeric_values)
                        elif method == "median":
                            numeric_values = sorted([v for v in values if isinstance(v, (int, float))])
                            if numeric_values:
                                mid = len(numeric_values) // 2
                                imputed[field] = numeric_values[mid]
                        elif method == "mode":
                            from collections import Counter
                            imputed[field] = Counter(values).most_common(1)[0][0]
                        
                        imputation_log.append({
                            "field": field,
                            "action": method,
                            "value": imputed.get(field)
                        })
        
        return {
            "data": imputed,
            "imputation_log": imputation_log
        }


class OutlierDetector:
    """Detect outliers in numeric data."""
    
    @staticmethod
    def detect_iqr(values: List[float], multiplier: float = 1.5) -> Dict[str, Any]:
        """
        Detect outliers using IQR method.
        """
        if not values or len(values) < 4:
            return {"error": "Not enough data for IQR analysis"}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        outliers = [v for v in values if v < lower_bound or v > upper_bound]
        
        return {
            "method": "iqr",
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "outlier_count": len(outliers),
            "outliers": outliers,
            "outlier_ratio": len(outliers) / len(values)
        }
    
    @staticmethod
    def detect_zscore(values: List[float], threshold: float = 3.0) -> Dict[str, Any]:
        """
        Detect outliers using Z-score method.
        """
        if not values or len(values) < 2:
            return {"error": "Not enough data for Z-score analysis"}
        
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        
        if std == 0:
            return {
                "method": "zscore",
                "outlier_count": 0,
                "outliers": [],
                "message": "Standard deviation is 0"
            }
        
        outliers = []
        outlier_details = []
        
        for v in values:
            z = abs((v - mean) / std)
            if z > threshold:
                outliers.append(v)
                outlier_details.append({"value": v, "zscore": round(z, 2)})
        
        return {
            "method": "zscore",
            "mean": mean,
            "std": std,
            "threshold": threshold,
            "outlier_count": len(outliers),
            "outliers": outliers,
            "outlier_details": outlier_details,
            "outlier_ratio": len(outliers) / len(values)
        }


class TemporalSplitter:
    """Handle temporal splitting for time series data."""
    
    async def temporal_split(
        self,
        db: AsyncSession,
        project_id: UUID,
        timestamp_field: str = "created_at",
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        gap_days: int = 0
    ) -> Dict[str, Any]:
        """
        Split data temporally (by time order).
        
        Unlike random split, temporal split ensures:
        - Training data is always older than validation/test
        - No future leakage
        
        Args:
            gap_days: Gap between splits to avoid leakage
        """
        # Validate ratios
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.001:
            return {"error": "Ratios must sum to 1.0"}
        
        # Get all items ordered by timestamp
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id
            ).order_by(DataItem.created_at)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        n = len(items)
        
        # Calculate split indices
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        # Apply splits
        train_items = items[:train_end]
        val_items = items[train_end:val_end]
        test_items = items[val_end:]
        
        # Apply gap if specified
        if gap_days > 0 and train_items and val_items:
            train_max_date = train_items[-1].created_at
            gap_delta = timedelta(days=gap_days)
            
            # Remove items in gap period from validation
            val_items = [
                item for item in val_items 
                if item.created_at > train_max_date + gap_delta
            ]
            
            # Similarly for test
            if val_items:
                val_max_date = val_items[-1].created_at
                test_items = [
                    item for item in test_items 
                    if item.created_at > val_max_date + gap_delta
                ]
        
        # Apply splits to database
        for item in train_items:
            item.dataset_split = "train"
        for item in val_items:
            item.dataset_split = "val"
        for item in test_items:
            item.dataset_split = "test"
        
        await db.commit()
        
        # Prepare result
        result = {
            "project_id": str(project_id),
            "split_type": "temporal",
            "total_items": n,
            "train": {
                "count": len(train_items),
                "date_range": {
                    "start": train_items[0].created_at.isoformat() if train_items else None,
                    "end": train_items[-1].created_at.isoformat() if train_items else None
                }
            },
            "val": {
                "count": len(val_items),
                "date_range": {
                    "start": val_items[0].created_at.isoformat() if val_items else None,
                    "end": val_items[-1].created_at.isoformat() if val_items else None
                }
            },
            "test": {
                "count": len(test_items),
                "date_range": {
                    "start": test_items[0].created_at.isoformat() if test_items else None,
                    "end": test_items[-1].created_at.isoformat() if test_items else None
                }
            },
            "gap_days": gap_days,
            "no_temporal_leakage": True
        }
        
        return result
    
    async def sliding_window_split(
        self,
        db: AsyncSession,
        project_id: UUID,
        window_size_days: int = 30,
        step_size_days: int = 7,
        forecast_horizon_days: int = 7
    ) -> Dict[str, Any]:
        """
        Create sliding window splits for time series cross-validation.
        
        Each window:
        - Training: data in window
        - Test: data in forecast horizon after window
        """
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id
            ).order_by(DataItem.created_at)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        # Get date range
        min_date = items[0].created_at
        max_date = items[-1].created_at
        
        windows = []
        current_start = min_date
        
        window_delta = timedelta(days=window_size_days)
        step_delta = timedelta(days=step_size_days)
        horizon_delta = timedelta(days=forecast_horizon_days)
        
        window_num = 0
        while current_start + window_delta + horizon_delta <= max_date:
            window_end = current_start + window_delta
            test_end = window_end + horizon_delta
            
            # Count items in each part
            train_count = sum(
                1 for item in items 
                if current_start <= item.created_at < window_end
            )
            test_count = sum(
                1 for item in items 
                if window_end <= item.created_at < test_end
            )
            
            windows.append({
                "window_id": window_num,
                "train_start": current_start.isoformat(),
                "train_end": window_end.isoformat(),
                "test_start": window_end.isoformat(),
                "test_end": test_end.isoformat(),
                "train_count": train_count,
                "test_count": test_count
            })
            
            current_start += step_delta
            window_num += 1
        
        return {
            "project_id": str(project_id),
            "split_type": "sliding_window",
            "total_items": len(items),
            "date_range": {
                "start": min_date.isoformat(),
                "end": max_date.isoformat()
            },
            "parameters": {
                "window_size_days": window_size_days,
                "step_size_days": step_size_days,
                "forecast_horizon_days": forecast_horizon_days
            },
            "windows": windows,
            "total_windows": len(windows)
        }


class DataValidationService:
    """Main service for data validation."""
    
    def __init__(self):
        self.missing_handler = MissingValuesHandler()
        self.outlier_detector = OutlierDetector()
        self.temporal_splitter = TemporalSplitter()
    
    def create_schema_validator(self, schema: Dict[str, Any]) -> SchemaValidator:
        """Create a schema validator with given schema."""
        return SchemaValidator(schema)
    
    async def validate_project_data(
        self,
        db: AsyncSession,
        project_id: UUID,
        schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate all data in a project against schema.
        """
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        validation_results = {
            "total_items": len(items),
            "valid_count": 0,
            "invalid_count": 0,
            "error_summary": defaultdict(int),
            "sample_errors": []
        }
        
        validator = SchemaValidator(schema) if schema else None
        
        for item in items:
            if item.data_type == "structured" and item.item_metadata:
                data = item.item_metadata
            elif item.content:
                try:
                    data = json.loads(item.content)
                except:
                    data = {"content": item.content}
            else:
                data = {}
            
            if validator:
                result = validator.validate(data)
                
                if result["valid"]:
                    validation_results["valid_count"] += 1
                else:
                    validation_results["invalid_count"] += 1
                    
                    for error in result["errors"]:
                        validation_results["error_summary"][error["error"]] += 1
                    
                    if len(validation_results["sample_errors"]) < 10:
                        validation_results["sample_errors"].append({
                            "item_id": str(item.id),
                            "errors": result["errors"]
                        })
            else:
                validation_results["valid_count"] += 1
        
        validation_results["error_summary"] = dict(validation_results["error_summary"])
        validation_results["validity_rate"] = round(
            validation_results["valid_count"] / max(1, validation_results["total_items"]), 
            4
        )
        
        return validation_results
    
    async def analyze_completeness(
        self,
        db: AsyncSession,
        project_id: UUID,
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """Analyze data completeness for a project."""
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        # Extract metadata as data records
        data_records = []
        for item in items:
            record = item.item_metadata or {}
            record["content"] = item.content
            record["labels"] = item.labels
            record["file_path"] = item.file_path
            data_records.append(record)
        
        return self.missing_handler.analyze_missing(data_records, fields)
    
    async def detect_outliers(
        self,
        db: AsyncSession,
        project_id: UUID,
        numeric_field: str,
        method: str = "iqr"
    ) -> Dict[str, Any]:
        """Detect outliers in a numeric field."""
        result = await db.execute(
            select(DataItem).where(DataItem.project_id == project_id)
        )
        items = result.scalars().all()
        
        values = []
        for item in items:
            metadata = item.item_metadata or {}
            if numeric_field in metadata:
                value = metadata[numeric_field]
                if isinstance(value, (int, float)):
                    values.append(value)
        
        if not values:
            return {"error": f"No numeric values found for field '{numeric_field}'"}
        
        if method == "iqr":
            return self.outlier_detector.detect_iqr(values)
        elif method == "zscore":
            return self.outlier_detector.detect_zscore(values)
        else:
            return {"error": f"Unknown method: {method}"}
    
    async def temporal_split(
        self,
        db: AsyncSession,
        project_id: UUID,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        gap_days: int = 0
    ) -> Dict[str, Any]:
        """Perform temporal split on project data."""
        return await self.temporal_splitter.temporal_split(
            db, project_id,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            gap_days=gap_days
        )


# Global instance
data_validation_service = DataValidationService()
