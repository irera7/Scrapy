# 📊 راهنمای جامع ساخت دیتاست - نکات مهم برای انواع دیتاست

این سند راهنمای کامل نکات مهم برای ساخت دیتاست‌های با کیفیت برای انواع مختلف داده است.

---

## 📑 فهرست مطالب

1. [نکات عمومی برای همه انواع دیتاست](#-نکات-عمومی-برای-همه-انواع-دیتاست)
2. [دیتاست متنی (Text Dataset)](#-دیتاست-متنی-text-dataset)
3. [دیتاست تصویری (Image Dataset)](#-دیتاست-تصویری-image-dataset)
4. [دیتاست صوتی (Audio Dataset)](#-دیتاست-صوتی-audio-dataset)
5. [دیتاست ویدیویی (Video Dataset)](#-دیتاست-ویدیویی-video-dataset)
6. [دیتاست ساختاریافته (Structured Dataset)](#-دیتاست-ساختاریافته-structured-dataset)
7. [دیتاست جدولی (Tabular Dataset)](#-دیتاست-جدولی-tabular-dataset)
8. [دیتاست سری زمانی (Time Series Dataset)](#-دیتاست-سری-زمانی-time-series-dataset)
9. [دیتاست چندرسانه‌ای (Multimodal Dataset)](#-دیتاست-چندرسانه‌ای-multimodal-dataset)
10. [دیتاست گراف (Graph Dataset)](#-دیتاست-گراف-graph-dataset)
11. [دیتاست سه‌بعدی (3D Dataset)](#-دیتاست-سه‌بعدی-3d-dataset)

---

## 🌟 نکات عمومی برای همه انواع دیتاست

### 1. تعریف هدف و نیازمندی‌ها
- ✅ **هدف پروژه**: مشخص کنید برای چه task ای دیتاست می‌سازید (classification, detection, generation, etc.)
- ✅ **معیارهای موفقیت**: معیارهای ارزیابی را از ابتدا تعریف کنید
- ✅ **محدودیت‌ها**: بودجه، زمان، منابع محاسباتی را در نظر بگیرید

### 2. کیفیت داده
- ✅ **دقت**: داده‌ها باید دقیق و بدون خطا باشند
- ✅ **کامل بودن**: داده‌های ناقص را شناسایی و حذف کنید
- ✅ **یکنواختی**: فرمت و ساختار داده‌ها باید یکسان باشد
- ✅ **اعتبار**: منبع داده‌ها قابل اعتماد باشد

### 3. حجم و اندازه
- ✅ **حداقل حجم**: برای ML معمولاً به حداقل 1000 نمونه نیاز دارید
- ✅ **تعادل کلاس‌ها**: توزیع کلاس‌ها باید متعادل باشد (یا از تکنیک‌های balancing استفاده کنید)
- ✅ **نمونه‌برداری**: از stratified sampling برای حفظ توزیع استفاده کنید

### 4. برچسب‌گذاری (Labeling)
- ✅ **دستورالعمل‌های واضح**: دستورالعمل‌های دقیق برای labelers بنویسید
- ✅ **کنترل کیفیت**: حداقل 10% داده‌ها را توسط چند labeler بررسی کنید
- ✅ **Inter-annotator Agreement**: توافق بین labelerها باید بالای 80% باشد
- ✅ **نسخه‌بندی برچسب‌ها**: تغییرات برچسب‌ها را track کنید

### 5. تقسیم‌بندی (Splitting)
- ✅ **Train/Validation/Test**: نسبت مناسب (معمولاً 70/15/15 یا 80/10/10)
- ✅ **Stratified Split**: توزیع کلاس‌ها در هر split حفظ شود
- ✅ **Temporal Split**: برای داده‌های زمانی، از split زمانی استفاده کنید
- ✅ **Data Leakage**: مطمئن شوید هیچ leakage وجود ندارد

### 6. مستندسازی
- ✅ **Dataset Card**: اطلاعات کامل دیتاست را مستند کنید
- ✅ **Metadata**: منبع، تاریخ، روش جمع‌آوری را ثبت کنید
- ✅ **نسخه‌بندی**: تغییرات را با versioning track کنید
- ✅ **مجوز و اخلاق**: مسائل حقوقی و اخلاقی را بررسی کنید

### 7. پیش‌پردازش
- ✅ **تمیز کردن**: داده‌های نامرتب و نویز را حذف کنید
- ✅ **نرمال‌سازی**: فرمت داده‌ها را یکسان کنید
- ✅ **حذف تکراری**: duplicate ها را شناسایی و حذف کنید
- ✅ **تبدیل فرمت**: به فرمت مناسب برای task تبدیل کنید

### 8. ذخیره‌سازی و دسترسی
- ✅ **فرمت مناسب**: فرمت بهینه برای حجم و سرعت انتخاب کنید
- ✅ **سازماندهی**: ساختار پوشه‌ها و فایل‌ها منطقی باشد
- ✅ **Backup**: نسخه‌های پشتیبان منظم داشته باشید
- ✅ **دسترسی**: کنترل دسترسی و امنیت را در نظر بگیرید

---

## 📝 دیتاست متنی (Text Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع متنوع**: از منابع مختلف (وب، کتاب، مقالات، شبکه‌های اجتماعی)
- ✅ **زبان**: زبان داده‌ها را مشخص کنید (monolingual/multilingual)
- ✅ **حوزه**: دامنه موضوعی را محدود کنید (general/domain-specific)
- ✅ **طول متن**: طول متن‌ها باید متناسب با task باشد

#### 2. کیفیت متن
- ✅ **Encoding**: از UTF-8 استفاده کنید
- ✅ **Normalization**: نرمال‌سازی Unicode (NFD/NFC)
- ✅ **Tokenization**: روش tokenization را مشخص کنید
- ✅ **حذف HTML/XML**: تگ‌ها و markup را حذف کنید
- ✅ **حذف whitespace**: فضاهای اضافی را حذف کنید

#### 3. پیش‌پردازش
- ✅ **حذف stop words**: در صورت نیاز
- ✅ **Stemming/Lemmatization**: برای برخی taskها
- ✅ **حذف کاراکترهای خاص**: emoji، symbolهای غیرضروری
- ✅ **حذف متن‌های کوتاه**: متن‌های کمتر از N کاراکتر
- ✅ **حذف متن‌های تکراری**: duplicate detection

#### 4. برچسب‌گذاری
- ✅ **Classification**: برچسب کلاس برای هر متن
- ✅ **NER**: موجودیت‌های نامدار (Person, Location, Organization)
- ✅ **Sentiment**: تحلیل احساسات (positive/negative/neutral)
- ✅ **POS Tagging**: برچسب‌های دستوری
- ✅ **Relation Extraction**: روابط بین موجودیت‌ها

#### 5. معیارهای کیفیت
- ✅ **حداقل طول**: معمولاً 20-50 کاراکتر
- ✅ **حداقل کلمات**: حداقل 3-5 کلمه
- ✅ **تنوع واژگان**: نسبت unique words به total words
- ✅ **خوانایی**: امتیاز خوانایی (Flesch, etc.)
- ✅ **زبان**: تشخیص خودکار زبان و فیلتر

#### 6. فرمت ذخیره‌سازی
- ✅ **JSONL**: هر خط یک JSON object
- ✅ **CSV**: برای داده‌های ساده
- ✅ **Parquet**: برای حجم بالا و فشرده
- ✅ **HuggingFace Dataset**: برای استفاده مستقیم

#### 7. مثال ساختار
```json
{
  "id": "text_001",
  "content": "متن اصلی...",
  "labels": ["tech", "positive"],
  "language": "fa",
  "source": "news.com",
  "metadata": {
    "length": 250,
    "word_count": 45,
    "created_at": "2024-01-01"
  }
}
```

---

## 🖼️ دیتاست تصویری (Image Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: وب، API، دوربین، سنسورها
- ✅ **تنوع**: زاویه‌ها، نور، پس‌زمینه، شرایط مختلف
- ✅ **Resolution**: رزولوشن یکسان یا حداقل حداقل رزولوشن
- ✅ **فرمت**: PNG (lossless) یا JPEG (compressed)

#### 2. کیفیت تصویر
- ✅ **رزولوشن**: حداقل 224x224 برای CNN، 512x512+ برای vision transformers
- ✅ **نسبت ابعاد**: حفظ aspect ratio یا crop مناسب
- ✅ **کیفیت**: حداقل 70% JPEG quality
- ✅ **حذف تصاویر تار**: blur detection
- ✅ **حذف تصاویر تیره/روشن**: brightness/contrast check

#### 3. پیش‌پردازش
- ✅ **Resize**: به اندازه استاندارد
- ✅ **Normalization**: pixel values به [0,1] یا [-1,1]
- ✅ **Color space**: RGB, Grayscale, HSV
- ✅ **حذف corrupt files**: بررسی integrity فایل‌ها
- ✅ **EXIF data**: حذف metadata اگر لازم است

#### 4. برچسب‌گذاری
- ✅ **Classification**: برچسب کلاس برای کل تصویر
- ✅ **Object Detection**: Bounding box + class
- ✅ **Segmentation**: Pixel-level masks
- ✅ **Keypoints**: نقاط کلیدی (pose, landmarks)
- ✅ **Captioning**: توضیحات متنی تصویر

#### 5. Annotation Tools
- ✅ **LabelImg**: برای bounding box
- ✅ **LabelMe**: برای polygon segmentation
- ✅ **CVAT**: ابزار حرفه‌ای annotation
- ✅ **COCO Format**: فرمت استاندارد

#### 6. معیارهای کیفیت
- ✅ **حداقل رزولوشن**: متناسب با task
- ✅ **تنوع**: زاویه، نور، پس‌زمینه
- ✅ **تعادل کلاس‌ها**: تعداد تصاویر هر کلاس
- ✅ **حذف duplicate**: perceptual hashing
- ✅ **حذف inappropriate**: فیلتر محتوای نامناسب

#### 7. فرمت ذخیره‌سازی
- ✅ **فایل‌های جداگانه**: هر تصویر یک فایل
- ✅ **TFRecord**: برای TensorFlow
- ✅ **LMDB**: برای دسترسی سریع
- ✅ **HDF5**: برای داده‌های بزرگ
- ✅ **COCO JSON**: برای annotations

#### 8. مثال ساختار COCO
```json
{
  "images": [{"id": 1, "file_name": "img1.jpg", "width": 640, "height": 480}],
  "annotations": [{
    "id": 1,
    "image_id": 1,
    "category_id": 1,
    "bbox": [x, y, width, height],
    "area": 1000,
    "segmentation": [[x1,y1,x2,y2,...]]
  }],
  "categories": [{"id": 1, "name": "person"}]
}
```

---

## 🎵 دیتاست صوتی (Audio Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: ضبط مستقیم، API، پایگاه‌های داده
- ✅ **تنوع**: گویندگان مختلف، محیط‌های مختلف
- ✅ **فرمت**: WAV (uncompressed) یا FLAC (lossless)
- ✅ **Sample Rate**: 16kHz (speech) یا 44.1kHz (music)

#### 2. کیفیت صوتی
- ✅ **Sample Rate**: حداقل 16kHz برای speech
- ✅ **Bit Depth**: 16-bit یا 24-bit
- ✅ **Channel**: Mono یا Stereo
- ✅ **Duration**: طول فایل‌های صوتی
- ✅ **حذف نویز**: noise reduction

#### 3. پیش‌پردازش
- ✅ **Normalization**: amplitude normalization
- ✅ **Silence Removal**: حذف سکوت ابتدا و انتها
- ✅ **Resampling**: تبدیل به sample rate یکسان
- ✅ **Noise Reduction**: کاهش نویز پس‌زمینه
- ✅ **VAD (Voice Activity Detection)**: تشخیص گفتار

#### 4. برچسب‌گذاری
- ✅ **Transcription**: متن گفتار (ASR)
- ✅ **Speaker ID**: شناسایی گوینده
- ✅ **Emotion**: تشخیص احساسات
- ✅ **Language**: تشخیص زبان
- ✅ **Music Tags**: ژانر، mood، instruments

#### 5. معیارهای کیفیت
- ✅ **SNR (Signal-to-Noise Ratio)**: حداقل 20dB
- ✅ **Duration**: حداقل 1-2 ثانیه
- ✅ **Clarity**: وضوح گفتار
- ✅ **حذف corrupt files**: بررسی integrity
- ✅ **تنوع گویندگان**: حداقل 10-20 گوینده

#### 6. فرمت ذخیره‌سازی
- ✅ **WAV**: فرمت استاندارد
- ✅ **FLAC**: فشرده lossless
- ✅ **JSONL + paths**: مسیر فایل‌ها + metadata
- ✅ **TFRecord**: برای TensorFlow

#### 7. مثال ساختار
```json
{
  "id": "audio_001",
  "file_path": "audio/sample.wav",
  "transcription": "متن گفتار",
  "duration": 3.5,
  "sample_rate": 16000,
  "language": "fa",
  "speaker_id": "spk_001",
  "metadata": {
    "gender": "male",
    "age": 30,
    "environment": "quiet"
  }
}
```

---

## 🎬 دیتاست ویدیویی (Video Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: YouTube, Vimeo, ضبط مستقیم
- ✅ **تنوع**: زاویه، نور، حرکت
- ✅ **فرمت**: MP4 (H.264), AVI, MOV
- ✅ **رزولوشن**: 720p حداقل، 1080p+ بهتر

#### 2. کیفیت ویدیو
- ✅ **رزولوشن**: حداقل 720x480
- ✅ **Frame Rate**: 24/30/60 fps
- ✅ **Duration**: طول کلیپ‌ها
- ✅ **Codec**: H.264 یا H.265
- ✅ **Bitrate**: حداقل 2-5 Mbps

#### 3. پیش‌پردازش
- ✅ **Frame Extraction**: استخراج فریم‌های کلیدی
- ✅ **Resize**: تغییر اندازه
- ✅ **Temporal Sampling**: نمونه‌برداری زمانی
- ✅ **حذف corrupt videos**: بررسی integrity
- ✅ **Normalization**: normalization pixel values

#### 4. برچسب‌گذاری
- ✅ **Action Recognition**: تشخیص عمل
- ✅ **Object Tracking**: ردیابی اشیاء
- ✅ **Temporal Segmentation**: تقسیم زمانی
- ✅ **Captioning**: توضیحات ویدیو
- ✅ **Scene Detection**: تشخیص صحنه

#### 5. Annotation Tools
- ✅ **CVAT**: برای video annotation
- ✅ **Labelbox**: پلتفرم annotation
- ✅ **VIA**: Video Image Annotator
- ✅ **YOLO Format**: برای object detection

#### 6. معیارهای کیفیت
- ✅ **حداقل duration**: 1-5 ثانیه
- ✅ **تنوع**: زاویه، نور، حرکت
- ✅ **تعادل کلاس‌ها**: تعداد ویدیوهای هر کلاس
- ✅ **حذف duplicate**: perceptual hashing
- ✅ **Stability**: ویدیوهای بدون لرزش زیاد

#### 7. فرمت ذخیره‌سازی
- ✅ **فایل‌های جداگانه**: هر ویدیو یک فایل
- ✅ **Frame sequences**: ذخیره فریم‌ها به صورت تصویر
- ✅ **TFRecord**: برای TensorFlow
- ✅ **JSONL + paths**: metadata + مسیر فایل‌ها

#### 8. مثال ساختار
```json
{
  "id": "video_001",
  "file_path": "videos/sample.mp4",
  "duration": 10.5,
  "fps": 30,
  "resolution": "1920x1080",
  "labels": ["walking", "outdoor"],
  "annotations": [{
    "frame_start": 0,
    "frame_end": 150,
    "action": "walking",
    "objects": [{"bbox": [x,y,w,h], "class": "person"}]
  }]
}
```

---

## 📊 دیتاست ساختاریافته (Structured Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: API, Database, Web scraping
- ✅ **فرمت**: JSON, XML, CSV
- ✅ **Schema**: ساختار داده مشخص باشد
- ✅ **Validation**: اعتبارسنجی ساختار

#### 2. کیفیت داده
- ✅ **Completeness**: فیلدهای اجباری پر باشند
- ✅ **Consistency**: مقادیر در محدوده معتبر
- ✅ **Accuracy**: داده‌ها دقیق باشند
- ✅ **Uniqueness**: کلیدهای یکتا
- ✅ **Timeliness**: داده‌ها به‌روز باشند

#### 3. پیش‌پردازش
- ✅ **Schema Validation**: بررسی ساختار
- ✅ **Type Conversion**: تبدیل نوع داده
- ✅ **Missing Values**: مدیریت مقادیر خالی
- ✅ **Outlier Detection**: شناسایی outliers
- ✅ **Normalization**: نرمال‌سازی مقادیر

#### 4. برچسب‌گذاری
- ✅ **Classification**: برچسب کلاس
- ✅ **Regression**: مقادیر عددی
- ✅ **Entity Linking**: ارتباط با entities
- ✅ **Relation Extraction**: استخراج روابط

#### 5. معیارهای کیفیت
- ✅ **Completeness Rate**: درصد فیلدهای پر
- ✅ **Accuracy Rate**: دقت داده‌ها
- ✅ **Consistency Score**: نمره یکنواختی
- ✅ **Duplicate Rate**: درصد تکراری‌ها

#### 6. فرمت ذخیره‌سازی
- ✅ **JSON/JSONL**: برای داده‌های nested
- ✅ **CSV**: برای داده‌های ساده
- ✅ **Parquet**: برای حجم بالا
- ✅ **Database**: PostgreSQL, MongoDB

#### 7. مثال ساختار
```json
{
  "id": "record_001",
  "name": "محصول",
  "price": 100000,
  "category": "electronics",
  "attributes": {
    "brand": "Samsung",
    "model": "Galaxy S21"
  },
  "metadata": {
    "source": "api",
    "collected_at": "2024-01-01"
  }
}
```

---

## 📈 دیتاست جدولی (Tabular Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: Database, CSV, Excel, API
- ✅ **ساختار**: ردیف‌ها و ستون‌ها مشخص
- ✅ **Schema**: نوع هر ستون مشخص باشد
- ✅ **Primary Key**: کلید اصلی مشخص

#### 2. کیفیت داده
- ✅ **Missing Values**: مدیریت مقادیر خالی
- ✅ **Data Types**: نوع صحیح هر ستون
- ✅ **Range Validation**: مقادیر در محدوده معتبر
- ✅ **Format Consistency**: فرمت یکسان
- ✅ **Referential Integrity**: یکپارچگی ارجاعی

#### 3. پیش‌پردازش
- ✅ **Imputation**: پر کردن مقادیر خالی
- ✅ **Encoding**: تبدیل categorical به numerical
- ✅ **Scaling**: نرمال‌سازی (MinMax, Standard)
- ✅ **Feature Engineering**: ایجاد ویژگی‌های جدید
- ✅ **Outlier Handling**: مدیریت outliers

#### 4. برچسب‌گذاری
- ✅ **Target Variable**: متغیر هدف مشخص
- ✅ **Feature Selection**: انتخاب ویژگی‌های مهم
- ✅ **Class Balance**: تعادل کلاس‌ها
- ✅ **Train/Test Split**: تقسیم مناسب

#### 5. معیارهای کیفیت
- ✅ **Completeness**: درصد داده‌های کامل
- ✅ **Accuracy**: دقت داده‌ها
- ✅ **Consistency**: یکنواختی
- ✅ **Timeliness**: به‌روز بودن

#### 6. فرمت ذخیره‌سازی
- ✅ **CSV**: فرمت استاندارد
- ✅ **Parquet**: فشرده و سریع
- ✅ **Excel**: برای ویرایش دستی
- ✅ **Database**: برای query

#### 7. مثال ساختار
```csv
id,name,age,city,label
1,علی,25,تهران,positive
2,مریم,30,اصفهان,negative
```

---

## ⏰ دیتاست سری زمانی (Time Series Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: سنسورها، API، Database
- ✅ **Frequency**: فرکانس نمونه‌برداری (ثانیه، دقیقه، ساعت)
- ✅ **Duration**: طول دوره زمانی
- ✅ **Continuity**: تداوم داده‌ها

#### 2. کیفیت داده
- ✅ **Missing Values**: مدیریت gaps زمانی
- ✅ **Outliers**: شناسایی anomalies
- ✅ **Stationarity**: بررسی stationarity
- ✅ **Trend/Seasonality**: شناسایی روند و فصلی بودن
- ✅ **Noise Level**: سطح نویز

#### 3. پیش‌پردازش
- ✅ **Interpolation**: پر کردن gaps
- ✅ **Smoothing**: هموارسازی
- ✅ **Detrending**: حذف روند
- ✅ **Differencing**: تبدیل به stationary
- ✅ **Normalization**: نرمال‌سازی

#### 4. برچسب‌گذاری
- ✅ **Forecasting**: پیش‌بینی مقادیر آینده
- ✅ **Anomaly Detection**: تشخیص anomalies
- ✅ **Classification**: دسته‌بندی الگوها
- ✅ **Segmentation**: تقسیم به segments

#### 5. معیارهای کیفیت
- ✅ **Coverage**: درصد داده‌های موجود
- ✅ **Consistency**: یکنواختی فرکانس
- ✅ **Signal Quality**: کیفیت سیگنال
- ✅ **Temporal Alignment**: هم‌راستایی زمانی

#### 6. فرمت ذخیره‌سازی
- ✅ **CSV**: با ستون timestamp
- ✅ **Parquet**: برای حجم بالا
- ✅ **HDF5**: برای سری‌های طولانی
- ✅ **Time Series DB**: InfluxDB, TimescaleDB

#### 7. مثال ساختار
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "value": 25.5,
  "sensor_id": "temp_001",
  "metadata": {
    "location": "room1",
    "unit": "celsius"
  }
}
```

---

## 🎭 دیتاست چندرسانه‌ای (Multimodal Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **ترکیب انواع**: متن + تصویر، صوت + متن، ویدیو + متن
- ✅ **هماهنگی**: داده‌های multimodal باید مرتبط باشند
- ✅ **Alignment**: هم‌راستایی بین modalities
- ✅ **تنوع**: ترکیب‌های مختلف

#### 2. کیفیت داده
- ✅ **Alignment Quality**: کیفیت هم‌راستایی
- ✅ **Completeness**: همه modalities موجود باشند
- ✅ **Consistency**: یکنواختی بین modalities
- ✅ **Relevance**: ارتباط بین modalities

#### 3. پیش‌پردازش
- ✅ **Synchronization**: همگام‌سازی زمانی
- ✅ **Alignment**: هم‌راستایی فضایی/زمانی
- ✅ **Feature Extraction**: استخراج ویژگی از هر modality
- ✅ **Fusion**: ترکیب ویژگی‌ها

#### 4. برچسب‌گذاری
- ✅ **Cross-modal Labels**: برچسب‌های مشترک
- ✅ **Modality-specific**: برچسب‌های خاص هر modality
- ✅ **Alignment Annotations**: annotation هم‌راستایی

#### 5. معیارهای کیفیت
- ✅ **Alignment Score**: نمره هم‌راستایی
- ✅ **Completeness**: درصد داده‌های کامل
- ✅ **Relevance**: ارتباط بین modalities

#### 6. فرمت ذخیره‌سازی
- ✅ **JSONL**: با مسیرهای فایل‌ها
- ✅ **TFRecord**: برای TensorFlow
- ✅ **Custom Format**: فرمت سفارشی

#### 7. مثال ساختار
```json
{
  "id": "multimodal_001",
  "text": "توضیحات تصویر",
  "image_path": "images/img1.jpg",
  "audio_path": "audio/audio1.wav",
  "alignment": {
    "text_to_image": "describes",
    "audio_to_text": "transcription"
  },
  "labels": ["positive", "outdoor"]
}
```

---

## 🕸️ دیتاست گراف (Graph Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: شبکه‌های اجتماعی، knowledge graphs، citation networks
- ✅ **نوع گراف**: Directed/Undirected, Weighted/Unweighted
- ✅ **Node Features**: ویژگی‌های nodeها
- ✅ **Edge Features**: ویژگی‌های edgeها

#### 2. کیفیت داده
- ✅ **Connectivity**: اتصال گراف
- ✅ **Node Completeness**: کامل بودن nodeها
- ✅ **Edge Accuracy**: دقت edgeها
- ✅ **Feature Quality**: کیفیت ویژگی‌ها

#### 3. پیش‌پردازش
- ✅ **Graph Construction**: ساخت گراف
- ✅ **Feature Engineering**: ایجاد ویژگی‌های node/edge
- ✅ **Graph Normalization**: نرمال‌سازی
- ✅ **Subgraph Extraction**: استخراج subgraph

#### 4. برچسب‌گذاری
- ✅ **Node Classification**: برچسب nodeها
- ✅ **Edge Classification**: برچسب edgeها
- ✅ **Graph Classification**: برچسب کل گراف
- ✅ **Link Prediction**: پیش‌بینی edge

#### 5. معیارهای کیفیت
- ✅ **Graph Size**: تعداد node و edge
- ✅ **Density**: تراکم گراف
- ✅ **Feature Completeness**: کامل بودن ویژگی‌ها
- ✅ **Label Coverage**: پوشش برچسب‌ها

#### 6. فرمت ذخیره‌سازی
- ✅ **GraphML**: فرمت XML برای گراف
- ✅ **JSON**: برای گراف‌های کوچک
- ✅ **CSR/CSC**: برای گراف‌های بزرگ
- ✅ **NetworkX**: برای Python

#### 7. مثال ساختار
```json
{
  "nodes": [
    {"id": 1, "features": [0.5, 0.3], "label": "A"},
    {"id": 2, "features": [0.2, 0.8], "label": "B"}
  ],
  "edges": [
    {"source": 1, "target": 2, "weight": 0.5}
  ],
  "graph_label": "positive"
}
```

---

## 🎯 دیتاست سه‌بعدی (3D Dataset)

### موارد مهم:

#### 1. جمع‌آوری داده
- ✅ **منابع**: 3D scanners, CAD models, LiDAR
- ✅ **فرمت**: OBJ, PLY, STL, Point Cloud
- ✅ **Resolution**: رزولوشن mesh یا point cloud
- ✅ **تنوع**: زاویه‌ها و دیدگاه‌های مختلف

#### 2. کیفیت داده
- ✅ **Mesh Quality**: کیفیت mesh (watertight, manifold)
- ✅ **Point Density**: تراکم نقاط
- ✅ **Noise Level**: سطح نویز
- ✅ **Completeness**: کامل بودن مدل

#### 3. پیش‌پردازش
- ✅ **Normalization**: نرمال‌سازی scale و orientation
- ✅ **Noise Removal**: حذف نویز
- ✅ **Simplification**: ساده‌سازی mesh
- ✅ **Feature Extraction**: استخراج ویژگی‌های هندسی

#### 4. برچسب‌گذاری
- ✅ **Classification**: برچسب کلاس
- ✅ **Segmentation**: تقسیم به parts
- ✅ **Keypoint Detection**: نقاط کلیدی
- ✅ **Pose Estimation**: تخمین pose

#### 5. معیارهای کیفیت
- ✅ **Mesh Quality**: manifold, watertight
- ✅ **Point Density**: حداقل نقاط
- ✅ **Geometric Accuracy**: دقت هندسی
- ✅ **Completeness**: کامل بودن

#### 6. فرمت ذخیره‌سازی
- ✅ **OBJ/PLY**: فرمت‌های استاندارد mesh
- ✅ **Point Cloud**: PCD, XYZ
- ✅ **Voxel Grid**: برای voxel-based methods
- ✅ **JSON + paths**: metadata + مسیر فایل‌ها

#### 7. مثال ساختار
```json
{
  "id": "3d_001",
  "file_path": "models/model.obj",
  "format": "obj",
  "vertex_count": 10000,
  "face_count": 20000,
  "label": "chair",
  "metadata": {
    "scale": [1.0, 1.0, 1.0],
    "center": [0.0, 0.0, 0.0]
  }
}
```

---

## ✅ چک‌لیست نهایی برای ساخت دیتاست

### قبل از شروع
- [ ] هدف و task مشخص است
- [ ] نیازمندی‌های داده تعریف شده
- [ ] بودجه و زمان مشخص است
- [ ] منابع داده شناسایی شده

### جمع‌آوری
- [ ] داده‌های متنوع جمع‌آوری شده
- [ ] کیفیت اولیه بررسی شده
- [ ] حجم کافی جمع‌آوری شده
- [ ] metadata ثبت شده

### پیش‌پردازش
- [ ] داده‌ها تمیز شده
- [ ] فرمت یکسان شده
- [ ] تکراری‌ها حذف شده
- [ ] نرمال‌سازی انجام شده

### برچسب‌گذاری
- [ ] دستورالعمل‌های واضح نوشته شده
- [ ] برچسب‌گذاری انجام شده
- [ ] کنترل کیفیت انجام شده
- [ ] Inter-annotator agreement بررسی شده

### تقسیم‌بندی
- [ ] Train/Val/Test تقسیم شده
- [ ] Stratified split انجام شده
- [ ] Data leakage بررسی شده
- [ ] توزیع کلاس‌ها بررسی شده

### مستندسازی
- [ ] Dataset card ایجاد شده
- [ ] Metadata کامل است
- [ ] نسخه‌بندی انجام شده
- [ ] مسائل حقوقی بررسی شده

### ذخیره‌سازی
- [ ] فرمت مناسب انتخاب شده
- [ ] ساختار منطقی است
- [ ] Backup ایجاد شده
- [ ] دسترسی کنترل شده

---

## 📚 منابع و مراجع

### استانداردها
- **HuggingFace Dataset Card**: استاندارد مستندسازی
- **COCO Format**: برای object detection
- **W3C Data on the Web**: بهترین شیوه‌ها

### ابزارها
- **Labeling**: LabelImg, CVAT, Labelbox
- **Processing**: Pandas, NumPy, OpenCV
- **Storage**: Parquet, HDF5, TFRecord

### مقالات
- "Data Quality for Machine Learning" - Google Research
- "The Dataset Nutrition Label" - MIT
- "Datasheets for Datasets" - Microsoft Research

---

*آخرین بروزرسانی: دسامبر 2024*
