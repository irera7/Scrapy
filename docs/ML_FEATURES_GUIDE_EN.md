# 🚀 ML Dataset Features - Complete User Guide

A comprehensive guide to the new platform features for creating ML-ready training datasets.

---

## 📑 Table of Contents

1. [ML Dataset Dashboard](#-ml-dataset-dashboard)
2. [Dataset Splitting](#-dataset-splitting)
3. [Dataset Versioning](#-dataset-versioning)
4. [Annotation Studio](#-annotation-studio)
5. [Data Augmentation](#-data-augmentation)
6. [Similarity Search](#-similarity-search)
7. [Active Learning](#-active-learning)
8. [Dataset Card](#-dataset-card)
9. [Advanced Export](#-advanced-export)

---

## 📊 ML Dataset Dashboard

### Access
From the main menu, click on **"ML Dataset"**.

### Features

#### Overall Dataset Statistics
- **Total Items**: Total number of collected data items
- **Labeled Items**: Number of items with labels/annotations
- **Storage Size**: Disk space used by data
- **Class Balance**: Label distribution visualization (to identify imbalanced datasets)

#### Distribution Charts
- **Split Distribution**: Pie chart showing train/validation/test distribution
- **Label Distribution**: Frequency of each label in the dataset
- **Data Type Distribution**: Count of text, image, audio, etc.
- **Quality Distribution**: Distribution of data quality status

---

## ✂️ Dataset Splitting

### Why It Matters
For training ML models, you need to split your dataset into three parts:
- **Train**: Data the model learns from
- **Validation**: For tuning hyperparameters
- **Test**: For final performance evaluation

### How to Use

#### Automatic Split (Auto Split)
1. Go to ML Dataset dashboard
2. In the "Split Distribution" section, click **"Auto Split"**
3. Set the ratios:
   - Train: Usually 70-80%
   - Validation: Usually 10-15%
   - Test: Usually 10-15%
4. Confirm

#### Manual Split
1. Go to **Data** page
2. Select desired items
3. From the dropdown, select the desired Split

### Important Notes
- ⚠️ Ratios must sum to 100%
- 🔄 Click "Reset Splits" to reset all to "unassigned"
- 📊 Distribution updates in real-time

---

## 📚 Dataset Versioning

### Why It Matters
Versioning allows you to:
- Track dataset changes over time
- Roll back to previous versions
- Document dataset evolution history

### Creating a New Version

1. In ML Dataset dashboard, find the **"Versions"** section
2. Click **"Create Version"**
3. Fill in:
   - **Version**: Version number (e.g., v1.0, v2.0)
   - **Description**: Description of changes in this version
4. Confirm

### Viewing Versions
- List of all versions with creation dates
- Each version includes:
  - Version number
  - Description
  - Creation date
  - Item count in that version

---

## 🎨 Annotation Studio

### Access
From ML Dataset dashboard, click **"Annotation Studio"**.

### Supported Annotation Types

#### 1. Bounding Box
Used for object detection in images.

**How to use:**
1. Select the "Draw Box" tool
2. Click and drag on the image
3. Select appropriate label
4. Adjust color and other properties

**Use cases:** Object Detection, Face Detection

#### 2. Named Entity Recognition (NER)
For identifying named entities in text.

**How to use:**
1. Display the text
2. Select the desired portion with mouse
3. Specify entity type (person, location, organization, ...)

**Use cases:** Information Extraction, Chatbots

#### 3. Classification
For assigning a label to entire data item.

**Use cases:** Sentiment Analysis, Spam Detection

#### 4. Polygon
For precise object segmentation.

**Use cases:** Semantic Segmentation

#### 5. Keypoints
For pose and landmark detection.

**Use cases:** Pose Estimation, Face Landmarks

#### 6. Relations
For specifying relationships between entities.

**Use cases:** Knowledge Graph, Relation Extraction

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `Escape` | Cancel selection |
| `Delete` | Delete selected |
| `Ctrl+S` | Save |
| `+` / `-` | Zoom image |

### Saving Annotations
- Click **"Save Annotations"**
- Or use `Ctrl+S` shortcut

---

## 🔄 Data Augmentation

### Access
From ML Dataset dashboard, click **"Data Augmentation"**.

### Why It Matters
Data augmentation helps you:
- Increase dataset size
- Make model robust to variations
- Prevent overfitting

### Text Augmentation Techniques

| Technique | Description | Parameters |
|-----------|-------------|------------|
| **Synonym Replacement** | Replace words with synonyms | Number of words |
| **Random Swap** | Randomly swap words | Number of swaps |
| **Random Deletion** | Randomly delete words | Deletion ratio |
| **Random Insertion** | Insert random words | Number of insertions |
| **Character Noise** | Add character-level noise | Noise ratio |

### Image Augmentation Techniques

| Technique | Description | Parameters |
|-----------|-------------|------------|
| **Horizontal Flip** | Flip horizontally | - |
| **Vertical Flip** | Flip vertically | - |
| **Rotation** | Rotate by angle | Degrees (0-360) |
| **Brightness** | Adjust brightness | Factor (0.5-2.0) |
| **Contrast** | Adjust contrast | Factor (0.5-2.0) |
| **Random Crop** | Random cropping | Crop percentage |
| **Gaussian Noise** | Gaussian noise | Noise intensity |
| **Blur** | Apply blur | Blur radius |
| **Grayscale** | Convert to grayscale | - |
| **Color Jitter** | Random color changes | Jitter intensity |

### How to Use

#### Creating Augmentation Rule
1. Click **"Add Rule"**
2. Select:
   - **Name**: Rule name
   - **Type**: Data type (text/image)
   - **Technique**: Desired technique
   - **Parameters**: Technique parameters
3. Save

#### Running Augmentation
1. In **"Run Augmentation"** panel:
   - Specify number of copies per item
   - Select desired rules
2. Click **"Run Augmentation"**
3. Wait for operation to complete

### Important Notes
- ⚠️ Augmented data is marked as "augmented"
- 🔗 Each augmented item links to its original
- 📊 You can filter only original or augmented data

---

## 🔍 Similarity Search

### Why It Matters
- Find duplicate data
- Discover similar items
- Check dataset quality

### Generating Embeddings
1. Go to **"Embeddings"** section in API
2. Generate embeddings for your project:
   ```
   POST /api/dataset/embeddings/{project_id}/generate
   ```

### Similarity Search
After generating embeddings:
1. Select an item
2. Run similarity search:
   ```
   GET /api/dataset/embeddings/{project_id}/similar/{item_id}?top_k=10
   ```

### Finding Duplicates
To identify duplicate or very similar data:
```
GET /api/dataset/embeddings/{project_id}/duplicates?threshold=0.95
```

**threshold**: Similarity threshold (0-1). Higher = more similar

---

## 🧠 Active Learning

### Why It Matters
Active learning helps you get best results with minimal labeling.

### Strategies

#### 1. Uncertainty Sampling
Suggests items the model is least confident about.

**Use case:** When you want the model to improve on hard cases

#### 2. Diversity Sampling
Suggests items with the most diversity.

**Use case:** When you want better dataset coverage

### How to Use
```
POST /api/dataset/active-learning/{project_id}/suggest
Body: {
    "strategy": "uncertainty",  // or "diversity"
    "count": 50
}
```

### Output
List of items with scores recommended for labeling.

---

## 📋 Dataset Card

### Why It Matters
Dataset Card (inspired by HuggingFace) is standard documentation for your dataset.

### Card Contents
- **Name & Description**: Dataset introduction
- **License**: Usage terms
- **Languages**: Languages in the dataset
- **Tasks**: Possible ML tasks
- **Tags**: Descriptive tags
- **Creation Info**: Data collection method

### Creating/Editing Card
```
POST /api/dataset/cards/{project_id}
Body: {
    "name": "My Dataset",
    "description": "Complete dataset description",
    "license": "MIT",
    "languages": ["en", "fa"],
    "tasks": ["text-classification", "sentiment-analysis"],
    "tags": ["nlp", "persian"],
    "creation_info": {
        "method": "web-scraping",
        "source": "example.com"
    }
}
```

### YAML Export
Dataset card is available in YAML format (HuggingFace compatible).

---

## 📤 Advanced Export

### New Features

#### Filter by Split
When creating export, you can select specific splits:
- ✅ Train
- ✅ Validation  
- ✅ Test

#### Stratified Sampling
To preserve class distribution in sampling:
1. Enable **"Stratified Sample"** option
2. Specify sample size

#### Include Annotations
Enable **"Include Annotations"** to include annotations in export.

#### Incremental Export
Get only changes since previous export:
1. Select base export
2. Enable **"Incremental"** option

### How to Use
1. Go to **"Exports" > "New Export"**
2. Select export format
3. Configure filters:
   - Desired splits
   - Stratified sampling
   - Include annotations
4. Click **"Create Export"**

---

## 🔧 Quick API Reference

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

## 💡 Best Practices

### 1. Before Starting
- [ ] Define your ML project goals
- [ ] Determine task type (classification, detection, ...)
- [ ] Review data requirements

### 2. Data Collection
- [ ] Collect diverse data
- [ ] Check data quality
- [ ] Remove duplicates

### 3. Labeling
- [ ] Write labeling guidelines
- [ ] Use Active Learning
- [ ] Verify label quality

### 4. Splitting
- [ ] Choose appropriate ratios (70/15/15 or 80/10/10)
- [ ] Use Stratified Split
- [ ] Verify each split's distribution

### 5. Data Augmentation
- [ ] Choose techniques appropriate for your task
- [ ] Tune parameters carefully
- [ ] Verify augmented data quality

### 6. Documentation
- [ ] Complete dataset card
- [ ] Maintain regular versioning
- [ ] Document changes

---

## ❓ FAQ

### How do I find duplicate data?
Use **Similarity Search** with high threshold (like 0.95).

### What's the best train/val/test ratio?
- Large dataset: 80/10/10
- Small dataset: 70/15/15 or even 60/20/20

### Should I augment the test set?
❌ No! Only augment train set. Test set should contain real data.

### How do I prevent overfitting?
- Use data augmentation
- Maintain class balance
- Keep validation set separate

---

## 📞 Support

For questions and issues:
- Check API documentation
- Review system logs
- Contact development team

---

*Last updated: December 2024*
