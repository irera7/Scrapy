# 🚀 راهنمای جامع ویژگی‌های ML Dataset

این سند، راهنمای کامل ویژگی‌های جدید پلتفرم برای ایجاد دیتاست‌های آماده آموزش مدل‌های یادگیری ماشین است.

---

## 📑 فهرست مطالب

1. [داشبورد دیتاست ML](#-داشبورد-دیتاست-ml)
2. [تقسیم‌بندی دیتاست (Dataset Splitting)](#-تقسیم‌بندی-دیتاست)
3. [نسخه‌بندی دیتاست (Versioning)](#-نسخه‌بندی-دیتاست)
4. [استودیو حاشیه‌نویسی (Annotation Studio)](#-استودیو-حاشیه‌نویسی)
5. [افزایش داده (Data Augmentation)](#-افزایش-داده)
6. [جستجوی شباهت (Similarity Search)](#-جستجوی-شباهت)
7. [یادگیری فعال (Active Learning)](#-یادگیری-فعال)
8. [کارت دیتاست (Dataset Card)](#-کارت-دیتاست)
9. [خروجی پیشرفته (Advanced Export)](#-خروجی-پیشرفته)

---

## 📊 داشبورد دیتاست ML

### دسترسی
از منوی اصلی، روی **"ML Dataset"** کلیک کنید.

### قابلیت‌ها

#### آمار کلی دیتاست
- **تعداد کل آیتم‌ها**: تعداد کل داده‌های جمع‌آوری شده
- **آیتم‌های برچسب‌دار**: تعداد داده‌هایی که برچسب/لیبل دارند
- **حجم ذخیره‌سازی**: فضای اشغال شده توسط داده‌ها
- **تعادل کلاس‌ها**: نمایش توزیع برچسب‌ها (برای شناسایی عدم تعادل در دیتاست)

#### نمودارهای توزیع
- **توزیع Split**: نمودار دایره‌ای نشان‌دهنده توزیع train/validation/test
- **توزیع لیبل‌ها**: فراوانی هر برچسب در دیتاست
- **توزیع نوع داده**: تعداد متن، تصویر، صوت و...
- **توزیع کیفیت**: توزیع وضعیت کیفیت داده‌ها

---

## ✂️ تقسیم‌بندی دیتاست

### چرا مهم است؟
برای آموزش مدل‌های ML، نیاز دارید دیتاست را به سه بخش تقسیم کنید:
- **Train (آموزش)**: داده‌هایی که مدل از آن‌ها یاد می‌گیرد
- **Validation (اعتبارسنجی)**: برای تنظیم هایپرپارامترها
- **Test (تست)**: برای ارزیابی نهایی عملکرد مدل

### نحوه استفاده

#### تقسیم خودکار (Auto Split)
1. به داشبورد ML Dataset بروید
2. در بخش "Split Distribution"، روی **"Auto Split"** کلیک کنید
3. نسبت‌ها را تنظیم کنید:
   - Train: معمولاً 70-80%
   - Validation: معمولاً 10-15%
   - Test: معمولاً 10-15%
4. تأیید کنید

#### تقسیم دستی
1. به صفحه **Data** بروید
2. آیتم‌های مورد نظر را انتخاب کنید
3. از منوی کشویی، Split مورد نظر را انتخاب کنید

### نکات مهم
- ⚠️ مجموع نسبت‌ها باید 100% باشد
- 🔄 می‌توانید با کلیک روی "Reset Splits" همه را به حالت "unassigned" برگردانید
- 📊 توزیع به صورت بلادرنگ به‌روزرسانی می‌شود

---

## 📚 نسخه‌بندی دیتاست

### چرا مهم است؟
نسخه‌بندی به شما امکان می‌دهد:
- تغییرات دیتاست را در طول زمان پیگیری کنید
- به نسخه‌های قبلی برگردید
- تاریخچه تکامل دیتاست را مستند کنید

### ایجاد نسخه جدید

1. در داشبورد ML Dataset، بخش **"Versions"** را پیدا کنید
2. روی **"Create Version"** کلیک کنید
3. اطلاعات را پر کنید:
   - **Version**: شماره نسخه (مثل v1.0, v2.0)
   - **Description**: توضیح تغییرات این نسخه
4. تأیید کنید

### مشاهده نسخه‌ها
- لیست تمام نسخه‌ها با تاریخ ایجاد نمایش داده می‌شود
- هر نسخه شامل:
  - شماره نسخه
  - توضیحات
  - تاریخ ایجاد
  - تعداد آیتم‌ها در آن نسخه

---

## 🎨 استودیو حاشیه‌نویسی

### دسترسی
از داشبورد ML Dataset، روی **"Annotation Studio"** کلیک کنید.

### انواع حاشیه‌نویسی پشتیبانی شده

#### 1. Bounding Box (کادر محدود)
برای شناسایی اشیاء در تصاویر استفاده می‌شود.

**نحوه استفاده:**
1. ابزار "Draw Box" را انتخاب کنید
2. روی تصویر کلیک و درگ کنید
3. لیبل مناسب را انتخاب کنید
4. رنگ و سایر ویژگی‌ها را تنظیم کنید

**کاربرد:** Object Detection, Face Detection

#### 2. Named Entity Recognition (NER)
برای شناسایی موجودیت‌های نامدار در متن.

**نحوه استفاده:**
1. متن را نمایش دهید
2. بخش مورد نظر را با ماوس انتخاب کنید
3. نوع موجودیت را مشخص کنید (شخص، مکان، سازمان، ...)

**کاربرد:** استخراج اطلاعات، چت‌بات‌ها

#### 3. Classification (دسته‌بندی)
برای تخصیص یک برچسب به کل داده.

**کاربرد:** Sentiment Analysis, Spam Detection

#### 4. Polygon (چندضلعی)
برای segmentation دقیق اشیاء.

**کاربرد:** Semantic Segmentation

#### 5. Keypoints (نقاط کلیدی)
برای تشخیص pose و landmark ها.

**کاربرد:** Pose Estimation, Face Landmarks

#### 6. Relations (روابط)
برای مشخص کردن ارتباط بین موجودیت‌ها.

**کاربرد:** Knowledge Graph, Relation Extraction

### میانبرهای کیبورد
| کلید | عملکرد |
|------|--------|
| `Escape` | لغو انتخاب |
| `Delete` | حذف انتخاب شده |
| `Ctrl+S` | ذخیره |
| `+` / `-` | زوم تصویر |

### ذخیره حاشیه‌نویسی
- روی **"Save Annotations"** کلیک کنید
- یا از میانبر `Ctrl+S` استفاده کنید

---

## 🔄 افزایش داده (Data Augmentation)

### دسترسی
از داشبورد ML Dataset، روی **"Data Augmentation"** کلیک کنید.

### چرا مهم است؟
افزایش داده به شما کمک می‌کند:
- حجم دیتاست را افزایش دهید
- مدل را در برابر تغییرات مقاوم کنید
- از overfitting جلوگیری کنید

### تکنیک‌های متنی (Text Augmentation)

| تکنیک | توضیح | پارامترها |
|-------|-------|----------|
| **Synonym Replacement** | جایگزینی کلمات با مترادف | تعداد کلمات |
| **Random Swap** | جابجایی تصادفی کلمات | تعداد جابجایی |
| **Random Deletion** | حذف تصادفی کلمات | نسبت حذف |
| **Random Insertion** | درج کلمات تصادفی | تعداد درج |
| **Character Noise** | اضافه کردن نویز کاراکتری | نسبت نویز |

### تکنیک‌های تصویری (Image Augmentation)

| تکنیک | توضیح | پارامترها |
|-------|-------|----------|
| **Horizontal Flip** | چرخش افقی | - |
| **Vertical Flip** | چرخش عمودی | - |
| **Rotation** | چرخش با زاویه | درجه (0-360) |
| **Brightness** | تغییر روشنایی | فاکتور (0.5-2.0) |
| **Contrast** | تغییر کنتراست | فاکتور (0.5-2.0) |
| **Random Crop** | برش تصادفی | درصد برش |
| **Gaussian Noise** | نویز گاوسی | شدت نویز |
| **Blur** | تار کردن | شعاع تاری |
| **Grayscale** | تبدیل به خاکستری | - |
| **Color Jitter** | تغییر تصادفی رنگ | شدت تغییر |

### نحوه استفاده

#### ایجاد قانون افزایش
1. روی **"Add Rule"** کلیک کنید
2. انتخاب کنید:
   - **Name**: نام قانون
   - **Type**: نوع داده (text/image)
   - **Technique**: تکنیک مورد نظر
   - **Parameters**: پارامترهای تکنیک
3. ذخیره کنید

#### اجرای افزایش
1. در پنل **"Run Augmentation"**:
   - تعداد نسخه برای هر آیتم را مشخص کنید
   - قوانین مورد نظر را انتخاب کنید
2. روی **"Run Augmentation"** کلیک کنید
3. منتظر بمانید تا عملیات کامل شود

### نکات مهم
- ⚠️ داده‌های augmented شده به عنوان "augmented" علامت‌گذاری می‌شوند
- 🔗 هر داده augmented به داده اصلی خود لینک دارد
- 📊 می‌توانید فقط داده‌های اصلی یا augmented را فیلتر کنید

---

## 🔍 جستجوی شباهت

### چرا مهم است؟
- یافتن داده‌های تکراری
- پیدا کردن داده‌های مشابه
- بررسی کیفیت دیتاست

### تولید Embedding ها
1. به بخش **"Embeddings"** در API بروید
2. برای پروژه خود embedding تولید کنید:
   ```
   POST /api/dataset/embeddings/{project_id}/generate
   ```

### جستجوی شباهت
پس از تولید embedding ها:
1. یک آیتم را انتخاب کنید
2. جستجوی شباهت را اجرا کنید:
   ```
   GET /api/dataset/embeddings/{project_id}/similar/{item_id}?top_k=10
   ```

### یافتن داده‌های تکراری
برای شناسایی داده‌های تکراری یا بسیار مشابه:
```
GET /api/dataset/embeddings/{project_id}/duplicates?threshold=0.95
```

**threshold**: آستانه شباهت (0-1). مقدار بالاتر = شباهت بیشتر

---

## 🧠 یادگیری فعال (Active Learning)

### چرا مهم است؟
یادگیری فعال به شما کمک می‌کند با حداقل برچسب‌گذاری، بهترین نتیجه را بگیرید.

### استراتژی‌ها

#### 1. Uncertainty Sampling (نمونه‌برداری عدم قطعیت)
داده‌هایی را پیشنهاد می‌دهد که مدل کمترین اطمینان را درباره آن‌ها دارد.

**کاربرد:** وقتی می‌خواهید مدل در موارد سخت بهتر شود

#### 2. Diversity Sampling (نمونه‌برداری تنوع)
داده‌هایی را پیشنهاد می‌دهد که بیشترین تنوع را دارند.

**کاربرد:** وقتی می‌خواهید دیتاست پوشش بهتری داشته باشد

### نحوه استفاده
```
POST /api/dataset/active-learning/{project_id}/suggest
Body: {
    "strategy": "uncertainty",  // یا "diversity"
    "count": 50
}
```

### خروجی
لیستی از آیتم‌ها به همراه امتیاز که برای برچسب‌گذاری توصیه می‌شوند.

---

## 📋 کارت دیتاست

### چرا مهم است؟
کارت دیتاست (الهام گرفته از HuggingFace) مستندات استاندارد برای دیتاست شماست.

### محتوای کارت
- **نام و توضیحات**: معرفی دیتاست
- **مجوز**: شرایط استفاده
- **زبان‌ها**: زبان‌های موجود در دیتاست
- **Task ها**: وظایف ML قابل انجام
- **برچسب‌ها**: تگ‌های توصیفی
- **اطلاعات ایجاد**: نحوه جمع‌آوری داده‌ها

### ایجاد/ویرایش کارت
```
POST /api/dataset/cards/{project_id}
Body: {
    "name": "My Dataset",
    "description": "توضیحات کامل دیتاست",
    "license": "MIT",
    "languages": ["fa", "en"],
    "tasks": ["text-classification", "sentiment-analysis"],
    "tags": ["persian", "nlp"],
    "creation_info": {
        "method": "web-scraping",
        "source": "example.com"
    }
}
```

### خروجی YAML
کارت دیتاست به فرمت YAML (سازگار با HuggingFace) قابل دریافت است.

---

## 📤 خروجی پیشرفته

### ویژگی‌های جدید

#### فیلتر بر اساس Split
هنگام ایجاد خروجی، می‌توانید فقط بخش‌های خاص را انتخاب کنید:
- ✅ Train
- ✅ Validation  
- ✅ Test

#### نمونه‌برداری طبقه‌بندی شده (Stratified Sampling)
برای حفظ توزیع کلاس‌ها در نمونه‌گیری:
1. گزینه **"Stratified Sample"** را فعال کنید
2. اندازه نمونه را مشخص کنید

#### شامل کردن Annotation ها
گزینه **"Include Annotations"** را فعال کنید تا حاشیه‌نویسی‌ها نیز در خروجی باشند.

#### خروجی افزایشی (Incremental Export)
فقط تغییرات نسبت به خروجی قبلی را دریافت کنید:
1. خروجی پایه را انتخاب کنید
2. گزینه **"Incremental"** را فعال کنید

### نحوه استفاده
1. به **"Exports" > "New Export"** بروید
2. فرمت خروجی را انتخاب کنید
3. فیلترها را تنظیم کنید:
   - Split های مورد نظر
   - نمونه‌برداری طبقه‌بندی شده
   - شامل annotation ها
4. روی **"Create Export"** کلیک کنید

---

## 🔧 API Reference سریع

### Dataset Statistics
```http
GET /api/dataset/statistics/{project_id}
```

### Split Management
```http
GET  /api/dataset/splits/{project_id}/stats
POST /api/dataset/splits/{project_id}/auto
POST /api/dataset/splits/{project_id}/reset
PUT  /api/dataset/splits/{project_id}/items/{item_id}
```

### Versions
```http
GET  /api/dataset/versions/{project_id}
POST /api/dataset/versions
```

### Annotations
```http
GET  /api/dataset/annotations/types/{project_id}
POST /api/dataset/annotations/types
PUT  /api/dataset/annotations/items/{item_id}
```

### Augmentation
```http
GET  /api/dataset/augmentation/rules/{project_id}
POST /api/dataset/augmentation/rules
POST /api/dataset/augmentation/run/{project_id}
```

### Embeddings
```http
POST /api/dataset/embeddings/{project_id}/generate
GET  /api/dataset/embeddings/{project_id}/similar/{item_id}
GET  /api/dataset/embeddings/{project_id}/duplicates
```

### Active Learning
```http
POST /api/dataset/active-learning/{project_id}/suggest
```

### Dataset Card
```http
GET  /api/dataset/cards/{project_id}
POST /api/dataset/cards/{project_id}
GET  /api/dataset/cards/{project_id}/yaml
```

---

## 💡 بهترین شیوه‌ها

### 1. قبل از شروع
- [ ] اهداف پروژه ML خود را مشخص کنید
- [ ] نوع task را تعیین کنید (classification, detection, ...)
- [ ] نیازمندی‌های داده را بررسی کنید

### 2. جمع‌آوری داده
- [ ] داده‌های متنوع جمع‌آوری کنید
- [ ] کیفیت داده‌ها را بررسی کنید
- [ ] داده‌های تکراری را حذف کنید

### 3. برچسب‌گذاری
- [ ] دستورالعمل برچسب‌گذاری بنویسید
- [ ] از Active Learning استفاده کنید
- [ ] کیفیت برچسب‌ها را بررسی کنید

### 4. تقسیم‌بندی
- [ ] نسبت مناسب انتخاب کنید (70/15/15 یا 80/10/10)
- [ ] از Stratified Split استفاده کنید
- [ ] توزیع هر split را بررسی کنید

### 5. افزایش داده
- [ ] تکنیک‌های مناسب task خود را انتخاب کنید
- [ ] پارامترها را با دقت تنظیم کنید
- [ ] کیفیت داده‌های augmented را بررسی کنید

### 6. مستندسازی
- [ ] کارت دیتاست را پر کنید
- [ ] نسخه‌بندی منظم داشته باشید
- [ ] تغییرات را مستند کنید

---

## ❓ سوالات متداول

### چگونه داده‌های تکراری را پیدا کنم؟
از بخش **Similarity Search** با threshold بالا (مثل 0.95) استفاده کنید.

### چه نسبتی برای train/val/test بهتر است؟
- دیتاست بزرگ: 80/10/10
- دیتاست کوچک: 70/15/15 یا حتی 60/20/20

### آیا افزایش داده برای test set هم باید انجام شود؟
❌ خیر! فقط train set را augment کنید. Test set باید داده‌های واقعی باشد.

### چگونه از overfitting جلوگیری کنم؟
- از افزایش داده استفاده کنید
- تعادل کلاس‌ها را حفظ کنید
- validation set را جدا نگه دارید

---

## 📞 پشتیبانی

برای سوالات و مشکلات:
- مستندات API را بررسی کنید
- لاگ‌های سیستم را چک کنید
- با تیم توسعه تماس بگیرید

---

## 🔗 ادغام ML با Scraping

### ویژگی‌های جدید در جمع‌آوری داده

هنگام scraping، این عملیات ML به صورت خودکار اجرا می‌شوند:

#### 1. Auto-Labeling (برچسب‌گذاری خودکار)
سیستم به صورت خودکار برچسب‌ها را از محتوا استخراج می‌کند:
- **تشخیص موضوع**: technology, business, health, sports, ...
- **تحلیل احساسات**: positive, negative
- **تشخیص از URL**: news, product, video, social, ...

```python
# فعال/غیرفعال کردن در config job
{
    "enable_auto_labeling": true  # پیش‌فرض: true
}
```

#### 2. Smart Deduplication (حذف تکراری هوشمند)
با استفاده از embedding ها، داده‌های مشابه معنایی شناسایی می‌شوند:

```python
{
    "enable_smart_dedup": true,  # پیش‌فرض: true
    "enable_embeddings": true    # تولید embedding برای متن‌ها
}
```

**آستانه پیش‌فرض**: 92% شباهت = تکراری

#### 3. Quality Filtering (فیلتر کیفیت)
داده‌های بی‌کیفیت به صورت خودکار علامت‌گذاری می‌شوند:

```python
{
    "enable_quality_filter": true,
    "min_quality_score": 0.3  # حداقل امتیاز کیفیت (0-1)
}
```

**معیارهای کیفیت متن:**
- طول حداقل 20 کاراکتر
- حداقل 3 کلمه
- بدون الگوهای spam
- تنوع کلمات

---

## ✅ تأثیر ML Dataset بر Export

**بله، تمامی ویژگی‌های ML در خروجی تأثیر می‌گذارند!**

### فیلترهای ML در Export

| فیلتر | توضیح | پیش‌فرض |
|-------|-------|---------|
| `splits` | فقط split های انتخابی | همه |
| `include_augmented` | شامل داده‌های augmented | true |
| `only_augmented` | فقط داده‌های augmented | false |
| `has_annotations` | فقط داده‌های annotate شده | false |
| `exclude_quality_filtered` | حذف داده‌های بی‌کیفیت | false |
| `exclude_duplicates` | حذف تکراری‌ها | false |
| `stratified_sample` | نمونه‌گیری طبقه‌بندی شده | false |
| `include_annotations` | شامل کردن annotations | true |

### فرمت‌های خروجی با پشتیبانی ML

#### JSONL
شامل فیلدهای ML:
```json
{
    "id": "...",
    "content": "...",
    "labels": ["tech", "positive"],
    "split": "train",
    "annotations": {...},
    "quality_score": 0.85,
    "augmented_from": null
}
```

#### HuggingFace
- فایل‌های جداگانه برای هر split (train.jsonl, validation.jsonl, test.jsonl)
- شامل annotations و quality scores
- README با آمار کامل

#### COCO
- شامل bbox، polygon و keypoint annotations از ML Dataset
- دسته‌بندی خودکار از labels
- پشتیبانی از split در metadata

### مثال Export با ML Filters

```python
{
    "format": "huggingface",
    "filters": {
        "splits": ["train", "validation"],
        "exclude_quality_filtered": true,
        "exclude_duplicates": true,
        "include_annotations": true,
        "stratified_sample": true,
        "sample_size": 10000
    }
}
```

---

*آخرین بروزرسانی: دسامبر 2024*
