"""Tabular Data Analysis Service."""
import io
import json
from typing import Dict, Any, Optional, List, Union
from uuid import UUID
from datetime import datetime
import structlog
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem

logger = structlog.get_logger()


class ColumnTypeDetector:
    """Detect and infer column types from data."""
    
    COLUMN_TYPES = {
        'numeric': ['int', 'float', 'integer', 'number', 'decimal'],
        'categorical': ['category', 'categorical', 'enum', 'class'],
        'text': ['string', 'text', 'str', 'varchar'],
        'datetime': ['date', 'time', 'datetime', 'timestamp'],
        'boolean': ['bool', 'boolean', 'flag'],
        'id': ['id', 'key', 'uuid', 'identifier']
    }
    
    def detect_type(self, values: List[Any], column_name: str = "") -> Dict[str, Any]:
        """Detect the type of a column from its values."""
        if not values:
            return {"type": "unknown", "confidence": 0}
        
        # Filter out None/null values
        non_null = [v for v in values if v is not None and v != "" and str(v).lower() != 'nan']
        
        if not non_null:
            return {"type": "empty", "null_ratio": 1.0}
        
        null_ratio = 1 - len(non_null) / len(values)
        sample = non_null[:1000]  # Sample for performance
        
        # Check if column name suggests type
        name_lower = column_name.lower()
        suggested_type = self._infer_from_name(name_lower)
        
        # Check for ID column
        if self._is_id_column(sample, name_lower):
            return {
                "type": "id",
                "subtype": "auto_increment" if self._is_sequential(sample) else "unique",
                "null_ratio": round(null_ratio, 4),
                "confidence": 0.9
            }
        
        # Check for datetime
        if self._is_datetime(sample):
            return {
                "type": "datetime",
                "format": self._detect_datetime_format(sample),
                "null_ratio": round(null_ratio, 4),
                "confidence": 0.95
            }
        
        # Check for boolean
        if self._is_boolean(sample):
            return {
                "type": "boolean",
                "values": list(set(str(v).lower() for v in sample[:10])),
                "null_ratio": round(null_ratio, 4),
                "confidence": 0.95
            }
        
        # Check for numeric
        if self._is_numeric(sample):
            is_integer = all(float(v) == int(float(v)) for v in sample if self._is_number(v))
            return {
                "type": "numeric",
                "subtype": "integer" if is_integer else "float",
                "null_ratio": round(null_ratio, 4),
                "confidence": 0.9
            }
        
        # Check for categorical
        unique_ratio = len(set(sample)) / len(sample)
        if unique_ratio < 0.1 or len(set(sample)) <= 20:
            return {
                "type": "categorical",
                "cardinality": len(set(non_null)),
                "unique_values": list(set(str(v) for v in sample[:20])),
                "null_ratio": round(null_ratio, 4),
                "confidence": 0.8
            }
        
        # Default to text
        avg_length = sum(len(str(v)) for v in sample) / len(sample)
        return {
            "type": "text",
            "avg_length": round(avg_length, 1),
            "null_ratio": round(null_ratio, 4),
            "confidence": 0.7
        }
    
    def _infer_from_name(self, name: str) -> Optional[str]:
        """Infer type from column name."""
        if any(kw in name for kw in ['id', 'key', 'uuid']):
            return 'id'
        if any(kw in name for kw in ['date', 'time', 'created', 'updated']):
            return 'datetime'
        if any(kw in name for kw in ['is_', 'has_', 'flag', 'active']):
            return 'boolean'
        if any(kw in name for kw in ['count', 'amount', 'price', 'quantity', 'score']):
            return 'numeric'
        return None
    
    def _is_id_column(self, values: List, name: str) -> bool:
        """Check if column is an ID column."""
        if 'id' in name.lower() or 'key' in name.lower():
            unique_ratio = len(set(values)) / len(values)
            return unique_ratio > 0.99
        return False
    
    def _is_sequential(self, values: List) -> bool:
        """Check if values are sequential integers."""
        try:
            nums = sorted(int(v) for v in values if self._is_number(v))
            if len(nums) < 2:
                return False
            diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
            return len(set(diffs)) == 1 and diffs[0] == 1
        except:
            return False
    
    def _is_datetime(self, values: List) -> bool:
        """Check if values are datetime strings."""
        from dateutil import parser
        
        success = 0
        for v in values[:20]:
            try:
                parser.parse(str(v))
                success += 1
            except:
                pass
        
        return success / min(len(values), 20) > 0.8
    
    def _detect_datetime_format(self, values: List) -> str:
        """Detect common datetime format."""
        sample = str(values[0]) if values else ""
        
        if 'T' in sample:
            return "ISO 8601"
        elif '-' in sample and ':' in sample:
            return "YYYY-MM-DD HH:MM:SS"
        elif '/' in sample:
            return "MM/DD/YYYY"
        else:
            return "unknown"
    
    def _is_boolean(self, values: List) -> bool:
        """Check if values are boolean."""
        bool_values = {'true', 'false', '0', '1', 'yes', 'no', 't', 'f', 'y', 'n'}
        str_values = set(str(v).lower() for v in values)
        return str_values.issubset(bool_values)
    
    def _is_numeric(self, values: List) -> bool:
        """Check if values are numeric."""
        success = 0
        for v in values[:50]:
            if self._is_number(v):
                success += 1
        return success / min(len(values), 50) > 0.9
    
    def _is_number(self, value: Any) -> bool:
        """Check if a value is a number."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


class CorrelationAnalyzer:
    """Analyze correlations between columns."""
    
    def compute_correlation_matrix(
        self, 
        data: Dict[str, List], 
        method: str = "pearson"
    ) -> Dict[str, Any]:
        """Compute correlation matrix for numeric columns."""
        numeric_cols = {}
        
        for col, values in data.items():
            try:
                numeric_values = [float(v) for v in values if v is not None and str(v).lower() != 'nan']
                if len(numeric_values) >= 10:
                    numeric_cols[col] = numeric_values
            except (ValueError, TypeError):
                continue
        
        if len(numeric_cols) < 2:
            return {"error": "Need at least 2 numeric columns"}
        
        # Ensure all columns have same length (use min)
        min_len = min(len(v) for v in numeric_cols.values())
        for col in numeric_cols:
            numeric_cols[col] = numeric_cols[col][:min_len]
        
        col_names = list(numeric_cols.keys())
        n_cols = len(col_names)
        
        matrix = np.zeros((n_cols, n_cols))
        
        for i, col1 in enumerate(col_names):
            for j, col2 in enumerate(col_names):
                if i == j:
                    matrix[i, j] = 1.0
                elif j > i:
                    corr = self._compute_correlation(
                        numeric_cols[col1], 
                        numeric_cols[col2], 
                        method
                    )
                    matrix[i, j] = corr
                    matrix[j, i] = corr
        
        # Find high correlations
        high_correlations = []
        for i, col1 in enumerate(col_names):
            for j, col2 in enumerate(col_names):
                if i < j and abs(matrix[i, j]) > 0.7:
                    high_correlations.append({
                        "column1": col1,
                        "column2": col2,
                        "correlation": round(matrix[i, j], 4),
                        "strength": "strong" if abs(matrix[i, j]) > 0.9 else "moderate"
                    })
        
        return {
            "columns": col_names,
            "matrix": matrix.round(4).tolist(),
            "high_correlations": high_correlations,
            "method": method
        }
    
    def _compute_correlation(
        self, 
        x: List[float], 
        y: List[float], 
        method: str
    ) -> float:
        """Compute correlation between two arrays."""
        try:
            x = np.array(x)
            y = np.array(y)
            
            if method == "pearson":
                return float(np.corrcoef(x, y)[0, 1])
            elif method == "spearman":
                from scipy import stats
                return float(stats.spearmanr(x, y)[0])
            else:
                return float(np.corrcoef(x, y)[0, 1])
        except Exception:
            return 0.0


class TabularStatistics:
    """Compute statistics for tabular data."""
    
    def compute_column_stats(self, values: List, column_type: str) -> Dict[str, Any]:
        """Compute statistics for a column."""
        non_null = [v for v in values if v is not None and str(v).lower() != 'nan']
        
        stats = {
            "count": len(values),
            "non_null": len(non_null),
            "null_count": len(values) - len(non_null),
            "null_ratio": round((len(values) - len(non_null)) / len(values), 4) if values else 0
        }
        
        if column_type in ["numeric", "integer", "float"]:
            try:
                nums = [float(v) for v in non_null]
                stats.update({
                    "min": float(np.min(nums)),
                    "max": float(np.max(nums)),
                    "mean": round(float(np.mean(nums)), 4),
                    "median": round(float(np.median(nums)), 4),
                    "std": round(float(np.std(nums)), 4),
                    "quartiles": {
                        "q1": round(float(np.percentile(nums, 25)), 4),
                        "q2": round(float(np.percentile(nums, 50)), 4),
                        "q3": round(float(np.percentile(nums, 75)), 4)
                    }
                })
            except Exception:
                pass
        
        elif column_type in ["categorical", "text"]:
            unique = list(set(str(v) for v in non_null))
            value_counts = {}
            for v in non_null:
                sv = str(v)
                value_counts[sv] = value_counts.get(sv, 0) + 1
            
            top_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            stats.update({
                "unique_count": len(unique),
                "unique_ratio": round(len(unique) / len(non_null), 4) if non_null else 0,
                "top_values": [{"value": k, "count": v} for k, v in top_values]
            })
        
        return stats


class TabularService:
    """Main service for tabular data analysis."""
    
    def __init__(self):
        self.type_detector = ColumnTypeDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.statistics = TabularStatistics()
    
    async def analyze_schema(
        self,
        db: AsyncSession,
        project_id: UUID,
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """Analyze schema of tabular data in a project."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id
            ).limit(sample_size)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        # Collect all keys from metadata
        all_keys = set()
        sample_data = {}
        
        for item in items:
            if item.item_metadata:
                for key in item.item_metadata.keys():
                    all_keys.add(key)
                    if key not in sample_data:
                        sample_data[key] = []
                    sample_data[key].append(item.item_metadata.get(key))
        
        if not all_keys:
            return {"error": "No structured data found"}
        
        # Detect column types
        schema = {}
        for key in all_keys:
            values = sample_data.get(key, [])
            type_info = self.type_detector.detect_type(values, key)
            schema[key] = type_info
        
        return {
            "columns": list(schema.keys()),
            "column_count": len(schema),
            "row_count": len(items),
            "schema": schema
        }
    
    async def compute_correlations(
        self,
        db: AsyncSession,
        project_id: UUID,
        columns: Optional[List[str]] = None,
        method: str = "pearson"
    ) -> Dict[str, Any]:
        """Compute correlation matrix for numeric columns."""
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id
            )
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        # Extract column data
        data = {}
        for item in items:
            if item.item_metadata:
                for key, value in item.item_metadata.items():
                    if columns is None or key in columns:
                        if key not in data:
                            data[key] = []
                        data[key].append(value)
        
        if len(data) < 2:
            return {"error": "Need at least 2 columns"}
        
        return self.correlation_analyzer.compute_correlation_matrix(data, method)
    
    async def compute_statistics(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Compute comprehensive statistics for all columns."""
        # First get schema
        schema_result = await self.analyze_schema(db, project_id, sample_size=1000)
        
        if "error" in schema_result:
            return schema_result
        
        result = await db.execute(
            select(DataItem).where(
                DataItem.project_id == project_id
            )
        )
        items = result.scalars().all()
        
        # Extract data
        data = {}
        for item in items:
            if item.item_metadata:
                for key, value in item.item_metadata.items():
                    if key not in data:
                        data[key] = []
                    data[key].append(value)
        
        # Compute stats for each column
        column_stats = {}
        for col, values in data.items():
            col_type = schema_result["schema"].get(col, {}).get("type", "unknown")
            column_stats[col] = self.statistics.compute_column_stats(values, col_type)
        
        return {
            "row_count": len(items),
            "column_count": len(column_stats),
            "columns": column_stats
        }
    
    async def detect_data_quality_issues(
        self,
        db: AsyncSession,
        project_id: UUID
    ) -> Dict[str, Any]:
        """Detect data quality issues in tabular data."""
        stats = await self.compute_statistics(db, project_id)
        
        if "error" in stats:
            return stats
        
        issues = []
        
        for col, col_stats in stats.get("columns", {}).items():
            # High null ratio
            if col_stats.get("null_ratio", 0) > 0.3:
                issues.append({
                    "column": col,
                    "issue": "high_null_ratio",
                    "severity": "warning",
                    "value": col_stats["null_ratio"],
                    "message": f"Column has {col_stats['null_ratio']*100:.1f}% missing values"
                })
            
            # Low cardinality for supposed text
            unique_ratio = col_stats.get("unique_ratio", 1)
            if unique_ratio < 0.01 and col_stats.get("unique_count", 0) < 5:
                issues.append({
                    "column": col,
                    "issue": "low_cardinality",
                    "severity": "info",
                    "value": col_stats.get("unique_count"),
                    "message": f"Column has only {col_stats.get('unique_count')} unique values"
                })
            
            # Potential outliers in numeric columns
            if "std" in col_stats and col_stats.get("std", 0) > 0:
                cv = col_stats["std"] / abs(col_stats.get("mean", 1) or 1)
                if cv > 2:
                    issues.append({
                        "column": col,
                        "issue": "high_variance",
                        "severity": "info",
                        "value": round(cv, 2),
                        "message": f"Column has high coefficient of variation ({cv:.2f})"
                    })
        
        return {
            "total_issues": len(issues),
            "issues": issues,
            "summary": {
                "high_null_columns": len([i for i in issues if i["issue"] == "high_null_ratio"]),
                "low_cardinality_columns": len([i for i in issues if i["issue"] == "low_cardinality"]),
                "high_variance_columns": len([i for i in issues if i["issue"] == "high_variance"])
            }
        }


# Global instance
tabular_service = TabularService()
