# 🆕 راهنمای قابلیت‌های جدید

این سند قابلیت‌های جدیدی که بر اساس گزارش پوشش راهنمای ساخت دیتاست اضافه شده‌اند را توضیح می‌دهد.

---

## 📑 فهرست قابلیت‌های جدید

1. [Inter-Annotator Agreement](#1-inter-annotator-agreement)
2. [Data Leakage Detection](#2-data-leakage-detection)
3. [Advanced Quality Metrics](#3-advanced-quality-metrics)
4. [Temporal Split](#4-temporal-split)
5. [Schema Validation](#5-schema-validation)
6. [Missing Values Management](#6-missing-values-management)
7. [POS Tagging & Stemming/Lemmatization](#7-pos-tagging--stemminglemmatization)
8. [Backup System](#8-backup-system)

---

## 1. Inter-Annotator Agreement

### چرا مهم است؟
برای اطمینان از کیفیت برچسب‌گذاری، باید توافق بین چند labeler را اندازه‌گیری کنید.

### API Endpoints

#### محاسبه توافق
```http
POST /api/quality/agreement/calculate
Content-Type: application/json

{
    "project_id": "uuid",
    "annotation_field": "labels"
}
```

**پاسخ:**
```json
{
    "project_id": "uuid",
    "item_count": 1000,
    "annotator_count": 3,
    "pairwise_agreements": [...],
    "average_cohens_kappa": 0.75,
    "fleiss_kappa": 0.72,
    "overall_interpretation": "substantial",
    "quality_threshold_met": true
}
```

#### دریافت موارد اختلاف
```http
GET /api/quality/agreement/disagreements/{project_id}?min_annotators=2
```

#### حل اختلاف
```http
POST /api/quality/agreement/resolve/{item_id}?final_label=positive&resolution_notes=...
```

### معیارهای محاسبه شده
| معیار | توضیح | محدوده |
|-------|-------|-------|
| Cohen's Kappa | توافق بین دو annotator | -1 تا 1 |
| Fleiss' Kappa | توافق بین چند annotator | -1 تا 1 |
| Percentage Agreement | درصد توافق ساده | 0 تا 1 |
| Krippendorff's Alpha | با پشتیبانی missing data | 0 تا 1 |

### تفسیر Kappa
| مقدار | تفسیر |
|-------|--------|
| < 0 | poor |
| 0 - 0.20 | slight |
| 0.20 - 0.40 | fair |
| 0.40 - 0.60 | moderate |
| 0.60 - 0.80 | substantial |
| > 0.80 | almost_perfect |

---

## 2. Data Leakage Detection

### چرا مهم است؟
Data leakage باعث می‌شود مدل شما عملکرد غیرواقعی داشته باشد و در production فاجعه به بار آورد!

### API Endpoints

#### بررسی کامل
```http
POST /api/quality/leakage/check
Content-Type: application/json

{
    "project_id": "uuid",
    "similarity_threshold": 0.8
}
```

**پاسخ:**
```json
{
    "project_id": "uuid",
    "checks": {
        "exact_duplicates": {...},
        "near_duplicates": {...},
        "source_overlap": {...},
        "temporal_leakage": {...}
    },
    "overall_status": "warning",
    "total_issues": 5,
    "recommendations": [
        "Remove exact duplicates from test/val that exist in train"
    ]
}
```

#### بررسی‌های جداگانه
```http
GET /api/quality/leakage/exact-duplicates/{project_id}
GET /api/quality/leakage/near-duplicates/{project_id}?threshold=0.8
GET /api/quality/leakage/temporal/{project_id}
```

### انواع Leakage تشخیص داده شده
1. **Exact Duplicates**: محتوای کاملاً یکسان بین train و test
2. **Near Duplicates**: محتوای بسیار مشابه (شباهت > threshold)
3. **Source Overlap**: داده از همان منبع در train و test
4. **Temporal Leakage**: داده آینده در training set

---

## 3. Advanced Quality Metrics

### چرا مهم است؟
تشخیص خودکار داده‌های بی‌کیفیت (تصاویر تار، صدای نویزی، متن نامفهوم)

### API Endpoints

#### تحلیل یک آیتم
```http
GET /api/quality/metrics/item/{item_id}
```

**پاسخ برای تصویر:**
```json
{
    "item_id": "uuid",
    "data_type": "image",
    "image_quality": {
        "blur": {
            "laplacian_variance": 150.5,
            "blur_level": "medium",
            "is_blurry": true
        },
        "brightness": {
            "mean_brightness": 120.5,
            "brightness_class": "normal",
            "is_acceptable": true
        },
        "resolution": {
            "width": 640,
            "height": 480,
            "meets_minimum": true
        },
        "overall_score": 0.7,
        "quality_acceptable": true
    }
}
```

**پاسخ برای متن:**
```json
{
    "item_id": "uuid",
    "data_type": "text",
    "readability": {
        "flesch_reading_ease": 65.5,
        "flesch_kincaid_grade": 8.5,
        "difficulty": "standard"
    },
    "coherence": {
        "type_token_ratio": 0.45,
        "vocabulary_richness": "medium",
        "coherence_score": 0.72
    }
}
```

#### بررسی دسته‌ای
```http
GET /api/quality/metrics/batch/{project_id}?data_type=image&limit=100
```

### معیارهای کیفیت تصویر
| معیار | توضیح |
|-------|-------|
| Blur Detection | Laplacian variance < 100 = تار |
| Brightness | mean < 50 = تیره، > 200 = روشن |
| Resolution | حداقل 224x224 برای ML |

### معیارهای کیفیت متن
| معیار | توضیح |
|-------|-------|
| Flesch Reading Ease | 0-100 (بالاتر = آسان‌تر) |
| Type-Token Ratio | تنوع واژگان |
| Coherence Score | انسجام متن |

---

## 4. Temporal Split

### چرا مهم است؟
برای داده‌های زمانی (اخبار، سری زمانی)، split تصادفی باعث data leakage می‌شود!

### API Endpoints

#### Temporal Split
```http
POST /api/quality/splits/temporal
Content-Type: application/json

{
    "project_id": "uuid",
    "train_ratio": 0.7,
    "val_ratio": 0.15,
    "test_ratio": 0.15,
    "gap_days": 7
}
```

**پاسخ:**
```json
{
    "project_id": "uuid",
    "split_type": "temporal",
    "total_items": 10000,
    "train": {
        "count": 7000,
        "date_range": {
            "start": "2024-01-01T00:00:00",
            "end": "2024-09-30T00:00:00"
        }
    },
    "val": {...},
    "test": {...},
    "gap_days": 7,
    "no_temporal_leakage": true
}
```

#### Sliding Window (برای Cross-Validation)
```http
GET /api/quality/splits/sliding-window/{project_id}?window_size_days=30&step_size_days=7
```

### مزایای Temporal Split
- ✅ بدون data leakage
- ✅ شبیه‌سازی واقعی production
- ✅ مناسب برای داده‌های زمانی

---

## 5. Schema Validation

### چرا مهم است؟
اطمینان از ساختار صحیح داده‌های structured

### API Endpoints

#### اعتبارسنجی با Schema
```http
POST /api/quality/validation/schema
Content-Type: application/json

{
    "project_id": "uuid",
    "schema": {
        "fields": {
            "name": {"type": "string", "required": true, "min_length": 1},
            "age": {"type": "integer", "min": 0, "max": 150},
            "email": {"type": "email", "required": true},
            "tags": {"type": "array", "items": {"type": "string"}}
        },
        "allow_extra_fields": false
    }
}
```

**پاسخ:**
```json
{
    "total_items": 1000,
    "valid_count": 950,
    "invalid_count": 50,
    "error_summary": {
        "required_field_missing": 30,
        "type_mismatch": 15,
        "invalid_email": 5
    },
    "validity_rate": 0.95
}
```

### انواع فیلدهای پشتیبانی شده
- `string`, `integer`, `float`, `boolean`
- `array`, `object`, `null`
- `email`, `url`, `date`, `datetime`

---

## 6. Missing Values Management

### چرا مهم است؟
شناسایی و مدیریت داده‌های ناقص

### API Endpoints

#### بررسی کامل بودن
```http
GET /api/quality/validation/completeness/{project_id}?fields=name,age,email
```

**پاسخ:**
```json
{
    "total_items": 1000,
    "fields_analyzed": 3,
    "field_stats": {
        "name": {
            "missing": 0,
            "null": 5,
            "empty_string": 10,
            "total_missing": 15,
            "completeness": 0.985
        },
        "age": {...},
        "email": {...}
    },
    "overall_completeness": 0.97
}
```

### استراتژی‌های Imputation
- `mean`: میانگین (عددی)
- `median`: میانه (عددی)
- `mode`: مد (همه انواع)
- `constant:value`: مقدار ثابت
- `drop`: علامت‌گذاری برای حذف

---

## 7. POS Tagging & Stemming/Lemmatization

### چرا مهم است؟
پردازش پیشرفته متن برای NLP

### استفاده در کد

```python
from app.services.nlp_processor import nlp_processor

# POS Tagging
tagged = nlp_processor.pos_tag("The quick brown fox jumps over the lazy dog")
# [('The', 'DT'), ('quick', 'JJ'), ('brown', 'JJ'), ('fox', 'NN'), ...]

# Stemming
stemmed = nlp_processor.stem("running")  # "run"
stemmed_text = nlp_processor.stem_text("The dogs are running quickly")
# "the dog are run quick"

# Lemmatization
lemma = nlp_processor.lemmatize("better", "JJ")  # "good"
lemma_text = nlp_processor.lemmatize_text("The children were running")
# "the child be run"

# استخراج اجزای کلام
nouns = nlp_processor.extract_nouns(text)
verbs = nlp_processor.extract_verbs(text)
adjectives = nlp_processor.extract_adjectives(text)

# حذف Stop Words (فارسی و انگلیسی)
cleaned = nlp_processor.remove_stopwords(text, language="fa")
```

### POS Tags (Penn Treebank)
| Tag | توضیح |
|-----|-------|
| NN | Noun |
| VB | Verb |
| JJ | Adjective |
| RB | Adverb |
| DT | Determiner |
| IN | Preposition |

---

## 8. Backup System

### چرا مهم است؟
محافظت از داده‌ها در برابر از دست رفتن

### API Endpoints

#### ایجاد Backup
```http
POST /api/quality/backup/create
Content-Type: application/json

{
    "project_id": "uuid",
    "include_files": true,
    "compress": true
}
```

**پاسخ:**
```json
{
    "success": true,
    "backup_id": "project_uuid_20241215_120000",
    "backup_path": "/backups/project_uuid_20241215_120000.tar.gz",
    "manifest": {
        "item_count": 5000,
        "files_backed_up": 1000,
        "components": ["project.json", "data_items.json", "files/"]
    }
}
```

#### Restore از Backup
```http
POST /api/quality/backup/restore
Content-Type: application/json

{
    "backup_path": "/backups/project_uuid_20241215_120000.tar.gz",
    "new_project_name": "My Project (Restored)"
}
```

#### لیست Backups
```http
GET /api/quality/backup/list?project_id=uuid
```

#### حذف Backup
```http
DELETE /api/quality/backup/{backup_name}
```

#### پاکسازی خودکار
```http
POST /api/quality/backup/cleanup?max_age_days=30&max_backups_per_project=5
```

### محتویات Backup
- ✅ Project metadata
- ✅ Data items with all metadata
- ✅ Dataset versions
- ✅ Dataset card
- ✅ Media files (optional)

---

## 📊 خلاصه APIها

| Endpoint | Method | توضیح |
|----------|--------|-------|
| `/api/quality/agreement/calculate` | POST | محاسبه توافق annotators |
| `/api/quality/agreement/disagreements/{project_id}` | GET | موارد اختلاف |
| `/api/quality/leakage/check` | POST | بررسی کامل leakage |
| `/api/quality/metrics/item/{item_id}` | GET | تحلیل کیفیت آیتم |
| `/api/quality/validation/schema` | POST | اعتبارسنجی schema |
| `/api/quality/validation/completeness/{project_id}` | GET | بررسی completeness |
| `/api/quality/validation/outliers` | POST | تشخیص outliers |
| `/api/quality/splits/temporal` | POST | Temporal split |
| `/api/quality/backup/create` | POST | ایجاد backup |
| `/api/quality/backup/restore` | POST | Restore از backup |

---

## 🛠️ نصب وابستگی‌ها

```bash
pip install nltk>=3.9.0
python -c "import nltk; nltk.download('averaged_perceptron_tagger'); nltk.download('punkt'); nltk.download('wordnet')"
```

---

*آخرین بروزرسانی: دسامبر 2024*
