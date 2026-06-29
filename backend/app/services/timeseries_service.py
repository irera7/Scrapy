"""Time Series Specialized Processing Service."""
import os
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem

logger = structlog.get_logger()


class StationarityTester:
    """Test time series for stationarity."""
    
    @staticmethod
    def adf_test(series: List[float]) -> Dict[str, Any]:
        """
        Perform Augmented Dickey-Fuller test for stationarity.
        
        Null hypothesis: Series has a unit root (non-stationary)
        If p-value < 0.05, we reject null hypothesis (series is stationary)
        """
        try:
            from statsmodels.tsa.stattools import adfuller
            import numpy as np
            
            result = adfuller(np.array(series), autolag='AIC')
            
            return {
                "test_statistic": round(float(result[0]), 4),
                "p_value": round(float(result[1]), 6),
                "lags_used": int(result[2]),
                "observations": int(result[3]),
                "critical_values": {k: round(v, 4) for k, v in result[4].items()},
                "is_stationary": result[1] < 0.05,
                "interpretation": "Stationary (reject unit root)" if result[1] < 0.05 
                                  else "Non-stationary (cannot reject unit root)"
            }
        except ImportError:
            return {"error": "statsmodels not installed"}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def kpss_test(series: List[float]) -> Dict[str, Any]:
        """
        Perform KPSS test for stationarity.
        
        Null hypothesis: Series is stationary
        If p-value < 0.05, series is non-stationary
        """
        try:
            from statsmodels.tsa.stattools import kpss
            import numpy as np
            
            result = kpss(np.array(series), regression='c', nlags='auto')
            
            return {
                "test_statistic": round(float(result[0]), 4),
                "p_value": round(float(result[1]), 6),
                "lags_used": int(result[2]),
                "critical_values": {k: round(v, 4) for k, v in result[3].items()},
                "is_stationary": result[1] >= 0.05,
                "interpretation": "Stationary" if result[1] >= 0.05 else "Non-stationary"
            }
        except ImportError:
            return {"error": "statsmodels not installed"}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def combined_test(series: List[float]) -> Dict[str, Any]:
        """Run both ADF and KPSS tests for comprehensive analysis."""
        adf_result = StationarityTester.adf_test(series)
        kpss_result = StationarityTester.kpss_test(series)
        
        # Interpret combined results
        adf_stationary = adf_result.get("is_stationary", False)
        kpss_stationary = kpss_result.get("is_stationary", False)
        
        if adf_stationary and kpss_stationary:
            conclusion = "stationary"
            recommendation = "Series is stationary, no differencing needed"
        elif not adf_stationary and not kpss_stationary:
            conclusion = "non_stationary"
            recommendation = "Series is non-stationary, consider differencing"
        elif adf_stationary and not kpss_stationary:
            conclusion = "trend_stationary"
            recommendation = "Series is trend-stationary, consider detrending"
        else:
            conclusion = "difference_stationary"
            recommendation = "Series is difference-stationary, apply differencing"
        
        return {
            "adf_test": adf_result,
            "kpss_test": kpss_result,
            "conclusion": conclusion,
            "recommendation": recommendation
        }


class SeasonalDecomposer:
    """Decompose time series into trend, seasonal, and residual components."""
    
    @staticmethod
    def decompose(
        series: List[float],
        period: Optional[int] = None,
        model: str = "additive"  # or "multiplicative"
    ) -> Dict[str, Any]:
        """
        Perform seasonal decomposition.
        
        Args:
            series: Time series data
            period: Seasonal period (auto-detected if None)
            model: "additive" or "multiplicative"
        """
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            import numpy as np
            
            data = np.array(series)
            
            # Auto-detect period if not provided
            if period is None:
                period = SeasonalDecomposer._detect_period(data)
            
            if period is None or period < 2:
                return {"error": "Could not detect seasonality period"}
            
            if len(data) < 2 * period:
                return {"error": f"Series too short for period {period}, need at least {2*period} points"}
            
            result = seasonal_decompose(data, model=model, period=period)
            
            return {
                "trend": [round(x, 4) if not np.isnan(x) else None for x in result.trend],
                "seasonal": [round(x, 4) for x in result.seasonal],
                "residual": [round(x, 4) if not np.isnan(x) else None for x in result.resid],
                "period": period,
                "model": model,
                "trend_strength": SeasonalDecomposer._compute_strength(
                    result.resid[~np.isnan(result.resid)],
                    result.trend[~np.isnan(result.trend)]
                ),
                "seasonal_strength": SeasonalDecomposer._compute_strength(
                    result.resid[~np.isnan(result.resid)],
                    result.seasonal
                )
            }
        except ImportError:
            return {"error": "statsmodels not installed"}
        except Exception as e:
            logger.error(f"Decomposition error: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _detect_period(series) -> Optional[int]:
        """Auto-detect seasonality period using autocorrelation."""
        try:
            from statsmodels.tsa.stattools import acf
            import numpy as np
            
            # Compute ACF
            acf_values = acf(series, nlags=min(len(series)//2, 100))
            
            # Find first significant peak after lag 1
            for i in range(2, len(acf_values)):
                if acf_values[i] > 0.5:  # Significant positive correlation
                    return i
            
            return None
        except:
            return None
    
    @staticmethod
    def _compute_strength(residual, component) -> float:
        """Compute strength of trend or seasonal component."""
        import numpy as np
        
        var_resid = np.var(residual)
        var_component = np.var(component)
        
        if var_resid + var_component == 0:
            return 0.0
        
        strength = max(0, 1 - var_resid / (var_resid + var_component))
        return round(float(strength), 4)


class TimeSeriesInterpolator:
    """Handle missing values in time series."""
    
    @staticmethod
    def interpolate(
        series: List[Optional[float]],
        timestamps: Optional[List[datetime]] = None,
        method: str = "linear"  # linear, spline, forward_fill, backward_fill
    ) -> Dict[str, Any]:
        """
        Interpolate missing values in time series.
        
        Args:
            series: Series with None values for missing
            timestamps: Optional timestamps
            method: Interpolation method
        """
        try:
            import numpy as np
            
            data = np.array([x if x is not None else np.nan for x in series], dtype=float)
            mask = np.isnan(data)
            missing_count = int(np.sum(mask))
            
            if missing_count == 0:
                return {
                    "interpolated": series,
                    "missing_count": 0,
                    "method": "none_needed"
                }
            
            if missing_count == len(data):
                return {"error": "All values are missing"}
            
            # Get indices
            indices = np.arange(len(data))
            valid_indices = indices[~mask]
            valid_values = data[~mask]
            
            if method == "linear":
                interpolated = np.interp(indices, valid_indices, valid_values)
            
            elif method == "spline":
                from scipy.interpolate import UnivariateSpline
                spline = UnivariateSpline(valid_indices, valid_values, s=0)
                interpolated = spline(indices)
            
            elif method == "forward_fill":
                interpolated = data.copy()
                for i in range(1, len(interpolated)):
                    if np.isnan(interpolated[i]):
                        interpolated[i] = interpolated[i-1]
            
            elif method == "backward_fill":
                interpolated = data.copy()
                for i in range(len(interpolated)-2, -1, -1):
                    if np.isnan(interpolated[i]):
                        interpolated[i] = interpolated[i+1]
            
            else:
                return {"error": f"Unknown method: {method}"}
            
            return {
                "interpolated": [round(float(x), 6) for x in interpolated],
                "missing_count": missing_count,
                "missing_ratio": round(missing_count / len(data), 4),
                "method": method
            }
            
        except ImportError as e:
            return {"error": f"Missing library: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}


class TimeSeriesAnalyzer:
    """Comprehensive time series analysis."""
    
    @staticmethod
    def compute_statistics(series: List[float]) -> Dict[str, Any]:
        """Compute basic time series statistics."""
        try:
            import numpy as np
            
            data = np.array(series)
            
            return {
                "count": len(data),
                "mean": round(float(np.mean(data)), 4),
                "std": round(float(np.std(data)), 4),
                "min": round(float(np.min(data)), 4),
                "max": round(float(np.max(data)), 4),
                "median": round(float(np.median(data)), 4),
                "q25": round(float(np.percentile(data, 25)), 4),
                "q75": round(float(np.percentile(data, 75)), 4),
                "skewness": round(float(TimeSeriesAnalyzer._skewness(data)), 4),
                "kurtosis": round(float(TimeSeriesAnalyzer._kurtosis(data)), 4)
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def _skewness(data) -> float:
        import numpy as np
        n = len(data)
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.sum(((data - mean) / std) ** 3) / n
    
    @staticmethod
    def _kurtosis(data) -> float:
        import numpy as np
        n = len(data)
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.sum(((data - mean) / std) ** 4) / n - 3
    
    @staticmethod
    def detect_anomalies(
        series: List[float],
        method: str = "zscore",  # zscore, iqr, isolation_forest
        threshold: float = 3.0
    ) -> Dict[str, Any]:
        """Detect anomalies in time series."""
        try:
            import numpy as np
            
            data = np.array(series)
            anomaly_indices = []
            anomaly_values = []
            
            if method == "zscore":
                mean = np.mean(data)
                std = np.std(data)
                if std > 0:
                    z_scores = np.abs((data - mean) / std)
                    anomaly_mask = z_scores > threshold
                    anomaly_indices = np.where(anomaly_mask)[0].tolist()
                    anomaly_values = data[anomaly_mask].tolist()
            
            elif method == "iqr":
                q1 = np.percentile(data, 25)
                q3 = np.percentile(data, 75)
                iqr = q3 - q1
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
                anomaly_mask = (data < lower) | (data > upper)
                anomaly_indices = np.where(anomaly_mask)[0].tolist()
                anomaly_values = data[anomaly_mask].tolist()
            
            elif method == "isolation_forest":
                try:
                    from sklearn.ensemble import IsolationForest
                    clf = IsolationForest(contamination=0.1, random_state=42)
                    predictions = clf.fit_predict(data.reshape(-1, 1))
                    anomaly_mask = predictions == -1
                    anomaly_indices = np.where(anomaly_mask)[0].tolist()
                    anomaly_values = data[anomaly_mask].tolist()
                except ImportError:
                    return {"error": "sklearn not installed for isolation_forest"}
            
            return {
                "anomaly_count": len(anomaly_indices),
                "anomaly_ratio": round(len(anomaly_indices) / len(data), 4),
                "anomaly_indices": anomaly_indices,
                "anomaly_values": [round(v, 4) for v in anomaly_values],
                "method": method,
                "threshold": threshold
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def compute_autocorrelation(
        series: List[float],
        max_lag: Optional[int] = None
    ) -> Dict[str, Any]:
        """Compute autocorrelation function."""
        try:
            from statsmodels.tsa.stattools import acf, pacf
            import numpy as np
            
            data = np.array(series)
            
            if max_lag is None:
                max_lag = min(len(data) // 4, 40)
            
            acf_values = acf(data, nlags=max_lag)
            
            try:
                pacf_values = pacf(data, nlags=max_lag)
            except:
                pacf_values = None
            
            return {
                "acf": [round(float(x), 4) for x in acf_values],
                "pacf": [round(float(x), 4) for x in pacf_values] if pacf_values is not None else None,
                "max_lag": max_lag,
                "significant_lags": TimeSeriesAnalyzer._find_significant_lags(acf_values)
            }
            
        except ImportError:
            # Fallback without statsmodels
            import numpy as np
            data = np.array(series)
            n = len(data)
            mean = np.mean(data)
            
            if max_lag is None:
                max_lag = min(n // 4, 40)
            
            acf_values = []
            for lag in range(max_lag + 1):
                if lag == 0:
                    acf_values.append(1.0)
                else:
                    numerator = np.sum((data[:-lag] - mean) * (data[lag:] - mean))
                    denominator = np.sum((data - mean) ** 2)
                    acf_values.append(numerator / denominator if denominator > 0 else 0)
            
            return {
                "acf": [round(float(x), 4) for x in acf_values],
                "pacf": None,
                "max_lag": max_lag,
                "significant_lags": TimeSeriesAnalyzer._find_significant_lags(acf_values)
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def _find_significant_lags(acf_values, threshold: float = 0.2) -> List[int]:
        """Find lags with significant autocorrelation."""
        significant = []
        for i, val in enumerate(acf_values[1:], 1):  # Skip lag 0
            if abs(val) > threshold:
                significant.append(i)
        return significant


class TimeSeriesService:
    """Main service for time series operations."""
    
    def __init__(self):
        self.stationarity = StationarityTester()
        self.decomposer = SeasonalDecomposer()
        self.interpolator = TimeSeriesInterpolator()
        self.analyzer = TimeSeriesAnalyzer()
    
    async def analyze_series(
        self,
        series: List[float],
        include_stationarity: bool = True,
        include_decomposition: bool = True,
        include_anomalies: bool = True
    ) -> Dict[str, Any]:
        """Run comprehensive time series analysis."""
        results = {
            "statistics": self.analyzer.compute_statistics(series),
            "autocorrelation": self.analyzer.compute_autocorrelation(series)
        }
        
        if include_stationarity:
            results["stationarity"] = self.stationarity.combined_test(series)
        
        if include_decomposition and len(series) >= 20:
            results["decomposition"] = self.decomposer.decompose(series)
        
        if include_anomalies:
            results["anomalies"] = self.analyzer.detect_anomalies(series)
        
        return results
    
    async def analyze_project_timeseries(
        self,
        db: AsyncSession,
        project_id: UUID,
        value_field: str = "value",
        timestamp_field: str = "timestamp"
    ) -> Dict[str, Any]:
        """Analyze time series data in a project."""
        result = await db.execute(
            select(DataItem)
            .where(DataItem.project_id == project_id)
            .order_by(DataItem.created_at)
        )
        items = result.scalars().all()
        
        if not items:
            return {"error": "No items found"}
        
        # Extract time series values from metadata
        values = []
        timestamps = []
        
        for item in items:
            metadata = item.item_metadata or {}
            
            if value_field in metadata:
                try:
                    values.append(float(metadata[value_field]))
                    timestamps.append(item.created_at)
                except (ValueError, TypeError):
                    continue
        
        if len(values) < 10:
            return {"error": f"Not enough numeric data points (found {len(values)})"}
        
        analysis = await self.analyze_series(values)
        analysis["item_count"] = len(values)
        analysis["date_range"] = {
            "start": timestamps[0].isoformat() if timestamps else None,
            "end": timestamps[-1].isoformat() if timestamps else None
        }
        
        return analysis
    
    async def fill_missing_values(
        self,
        db: AsyncSession,
        project_id: UUID,
        value_field: str,
        method: str = "linear"
    ) -> Dict[str, Any]:
        """Fill missing values in project time series data."""
        result = await db.execute(
            select(DataItem)
            .where(DataItem.project_id == project_id)
            .order_by(DataItem.created_at)
        )
        items = result.scalars().all()
        
        values = []
        for item in items:
            metadata = item.item_metadata or {}
            val = metadata.get(value_field)
            if val is not None:
                try:
                    values.append(float(val))
                except:
                    values.append(None)
            else:
                values.append(None)
        
        interpolation_result = self.interpolator.interpolate(values, method=method)
        
        if "error" in interpolation_result:
            return interpolation_result
        
        # Update items with interpolated values
        interpolated = interpolation_result["interpolated"]
        updated_count = 0
        
        for i, item in enumerate(items):
            if values[i] is None and interpolated[i] is not None:
                metadata = item.item_metadata or {}
                metadata[value_field] = interpolated[i]
                metadata[f"{value_field}_interpolated"] = True
                item.item_metadata = metadata
                updated_count += 1
        
        await db.commit()
        
        return {
            "updated_count": updated_count,
            "method": method,
            "missing_filled": interpolation_result["missing_count"]
        }


# Global instance
timeseries_service = TimeSeriesService()
