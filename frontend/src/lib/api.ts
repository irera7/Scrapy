import axios from 'axios'

// Use relative path in production (goes through nginx), or localhost for local dev
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    // In browser: use relative path if on production domain, otherwise use env var
    const hostname = window.location.hostname
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return '' // Relative path - goes through nginx
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8099'
}

const API_URL = getApiUrl()

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Helper to get locale-aware login path
const getLoginPath = () => {
  if (typeof window !== 'undefined') {
    // Extract locale from current path (e.g., /en/dashboard -> en)
    const pathParts = window.location.pathname.split('/')
    const locale = pathParts[1] || 'en'
    // Check if it's a valid locale (2 letter code)
    if (locale.length === 2) {
      return `/${locale}/auth/login`
    }
  }
  return '/en/auth/login'
}

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Skip redirect if already on auth pages
      if (typeof window !== 'undefined' && window.location.pathname.includes('/auth/')) {
        return Promise.reject(error)
      }
      
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          })
          
          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)
          
          // Retry original request
          error.config.headers.Authorization = `Bearer ${access_token}`
          return api(error.config)
        } catch {
          // Refresh failed, logout
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = getLoginPath()
        }
      } else {
        localStorage.removeItem('access_token')
        window.location.href = getLoginPath()
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  register: async (data: { email: string; password: string; full_name?: string }) => {
    const response = await api.post('/auth/register', data)
    return response.data
  },
  
  login: async (data: { email: string; password: string }) => {
    const response = await api.post('/auth/login', data)
    return response.data
  },
  
  refresh: async (refreshToken: string) => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },
  
  me: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },
  
  updateMe: async (data: { full_name?: string; password?: string }) => {
    const response = await api.patch('/auth/me', data)
    return response.data
  },
}

// Projects API
export const projectsApi = {
  list: async (params?: { skip?: number; limit?: number; is_active?: boolean }) => {
    const response = await api.get('/projects', { params })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/projects/${id}`)
    return response.data
  },
  
  create: async (data: { name: string; description?: string; data_type: string; settings?: object }) => {
    const response = await api.post('/projects', data)
    return response.data
  },
  
  update: async (id: string, data: Partial<{ name: string; description: string; data_type: string; settings: object; is_active: boolean }>) => {
    const response = await api.patch(`/projects/${id}`, data)
    return response.data
  },
  
  delete: async (id: string) => {
    await api.delete(`/projects/${id}`)
  },
  
  getStats: async (id: string) => {
    const response = await api.get(`/projects/${id}/stats`)
    return response.data
  },
}

// Jobs API
export const jobsApi = {
  list: async (params?: { project_id?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const response = await api.get('/jobs', { params })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/jobs/${id}`)
    return response.data
  },
  
  create: async (data: { project_id: string; name: string; provider: string; config: object; schedule?: string }) => {
    const response = await api.post('/jobs', data)
    return response.data
  },
  
  update: async (id: string, data: object) => {
    const response = await api.patch(`/jobs/${id}`, data)
    return response.data
  },
  
  delete: async (id: string) => {
    await api.delete(`/jobs/${id}`)
  },
  
  run: async (id: string, force?: boolean) => {
    const response = await api.post(`/jobs/${id}/run`, { force })
    return response.data
  },
  
  cancel: async (id: string) => {
    const response = await api.post(`/jobs/${id}/cancel`)
    return response.data
  },
  
  retry: async (id: string) => {
    const response = await api.post(`/jobs/${id}/retry`)
    return response.data
  },
  
  reset: async (id: string) => {
    const response = await api.post(`/jobs/${id}/reset`)
    return response.data
  },
  
  getLogs: async (id: string, params?: { level?: string; skip?: number; limit?: number }) => {
    const response = await api.get(`/jobs/${id}/logs`, { params })
    return response.data
  },
}

// Data Items API
export const dataApi = {
  list: async (project_id: string, params?: { data_type?: string; is_labeled?: boolean; is_processed?: boolean; skip?: number; limit?: number }) => {
    const response = await api.get('/data', { params: { project_id, ...params } })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/data/${id}`)
    return response.data
  },
  
  create: async (data: { project_id: string; data_type: string; content?: string; source_url?: string; metadata?: object }) => {
    const response = await api.post('/data', data)
    return response.data
  },
  
  update: async (id: string, data: object) => {
    const response = await api.patch(`/data/${id}`, data)
    return response.data
  },
  
  delete: async (id: string) => {
    await api.delete(`/data/${id}`)
  },
  
  bulkLabel: async (data: { item_ids: string[]; labels: string[]; action: 'add' | 'remove' | 'replace' }) => {
    const response = await api.post('/data/bulk-label', data)
    return response.data
  },
  
  upload: async (projectId: string, dataType: string, file: File, metadata?: object) => {
    const formData = new FormData()
    formData.append('project_id', projectId)
    formData.append('data_type', dataType)
    formData.append('file', file)
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata))
    }
    const response = await api.post('/data/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
  
  getCategories: async (projectId: string) => {
    const response = await api.get(`/data/categories/${projectId}`)
    return response.data
  },
  
  createCategory: async (data: { project_id: string; name: string; color?: string; description?: string }) => {
    const response = await api.post('/data/categories', data)
    return response.data
  },
  
  deleteCategory: async (id: string) => {
    await api.delete(`/data/categories/${id}`)
  },
  
  computeQualityScores: async (projectId: string, recompute = false) => {
    const response = await api.post('/processing/compute-quality-scores', null, {
      params: { project_id: projectId, recompute }
    })
    return response.data
  },
  
  extractLabels: async (projectId: string) => {
    const response = await api.post('/processing/extract-labels', null, {
      params: { project_id: projectId }
    })
    return response.data
  },
}

// Exports API
export const exportsApi = {
  list: async (params?: { project_id?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const response = await api.get('/exports', { params })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/exports/${id}`)
    return response.data
  },
  
  create: async (data: { project_id: string; name: string; format: string; filters?: object }) => {
    const response = await api.post('/exports', data)
    return response.data
  },
  
  delete: async (id: string) => {
    await api.delete(`/exports/${id}`)
  },
  
  download: async (id: string) => {
    const response = await api.get(`/exports/${id}/download`, { responseType: 'blob' })
    return response.data
  },
}

// Providers API
export const providersApi = {
  list: async () => {
    const response = await api.get('/providers')
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/providers/${id}`)
    return response.data
  },
  
  listApiKeys: async () => {
    const response = await api.get('/providers/keys/list')
    return response.data
  },
  
  saveApiKey: async (data: { provider: string; api_key: string }) => {
    const response = await api.post('/providers/keys', data)
    return response.data
  },
  
  deleteApiKey: async (id: string) => {
    await api.delete(`/providers/keys/${id}`)
  },
  
  testApiKey: async (id: string) => {
    const response = await api.post(`/providers/keys/${id}/test`)
    return response.data
  },
}

// Processing API
export const processingApi = {
  processItem: async (itemId: string, options: {
    processing_type?: 'text' | 'image' | 'audio' | 'video' | 'auto';
    text_options?: object;
    image_options?: object;
    audio_options?: object;
    video_options?: object;
  } = {}) => {
    const response = await api.post(`/processing/${itemId}/process`, options)
    return response.data
  },
  
  batchProcess: async (data: {
    item_ids: string[];
    processing_type?: string;
    text_options?: object;
    image_options?: object;
    audio_options?: object;
    video_options?: object;
  }) => {
    const response = await api.post('/processing/batch', data)
    return response.data
  },
  
  processAll: async (
    projectId: string, 
    processingType: 'text' | 'image' | 'audio' | 'video' | 'auto' = 'auto',
    reprocess = false
  ) => {
    const response = await api.post('/processing/process-all', null, {
      params: { 
        project_id: projectId, 
        processing_type: processingType,
        reprocess
      }
    })
    return response.data
  },
  
  computeQualityScores: async (projectId: string, recompute = false) => {
    const response = await api.post('/processing/compute-quality-scores', null, {
      params: { project_id: projectId, recompute }
    })
    return response.data
  },
  
  analyzeText: async (text: string) => {
    const response = await api.post('/processing/text/analyze', { text })
    return response.data
  },
  
  cleanText: async (text: string, options?: object) => {
    const response = await api.post('/processing/text/clean', { text, options })
    return response.data
  },
  
  detectDuplicates: async (projectId: string, threshold?: number) => {
    const response = await api.post('/processing/text/detect-duplicates', null, {
      params: { project_id: projectId, threshold }
    })
    return response.data
  },
}

// Health API
export const healthApi = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
  
  detailed: async () => {
    const response = await api.get('/health/detailed')
    return response.data
  },
}

// Visual Scraper API
export const visualScraperApi = {
  createSession: async () => {
    const response = await api.post('/visual-scraper/sessions')
    return response.data
  },
  
  endSession: async (sessionId: string) => {
    await api.delete(`/visual-scraper/sessions/${sessionId}`)
  },
  
  navigate: async (sessionId: string, url: string) => {
    const response = await api.post(`/visual-scraper/sessions/${sessionId}/navigate`, { url })
    return response.data
  },
  
  getElement: async (sessionId: string, x: number, y: number) => {
    const response = await api.post(`/visual-scraper/sessions/${sessionId}/element`, { x, y })
    return response.data
  },
  
  testSelector: async (sessionId: string, selector: string) => {
    const response = await api.post(`/visual-scraper/sessions/${sessionId}/test-selector`, { selector })
    return response.data
  },
  
  extractData: async (sessionId: string, rules: Array<{
    name: string;
    selector: string;
    extract_type?: string;
    attribute_name?: string;
    multiple?: boolean;
    transform?: string;
  }>) => {
    const response = await api.post(`/visual-scraper/sessions/${sessionId}/extract`, { rules })
    return response.data
  },
  
  takeScreenshot: async (sessionId: string, fullPage?: boolean) => {
    const response = await api.get(`/visual-scraper/sessions/${sessionId}/screenshot`, {
      params: { full_page: fullPage }
    })
    return response.data
  },
  
  highlightElements: async (sessionId: string, selector: string) => {
    const response = await api.post(`/visual-scraper/sessions/${sessionId}/highlight`, { selector })
    return response.data
  },
  
  createRecipe: async (sessionId: string, data: {
    name: string;
    rules: Array<any>;
    pagination?: object;
    wait_for?: string;
    scroll_to_bottom?: boolean;
  }) => {
    const response = await api.post(`/visual-scraper/sessions/${sessionId}/recipe`, data)
    return response.data
  },
}

// Templates API
export const templatesApi = {
  list: async (params?: { category?: string; tags?: string; query?: string }) => {
    const response = await api.get('/templates', { params })
    return response.data
  },
  
  get: async (id: string) => {
    const response = await api.get(`/templates/${id}`)
    return response.data
  },
  
  getCategories: async () => {
    const response = await api.get('/templates/categories')
    return response.data
  },
  
  matchUrl: async (url: string) => {
    const response = await api.post('/templates/match', { url })
    return response.data
  },
  
  create: async (data: {
    id: string;
    name: string;
    description: string;
    category: string;
    url_patterns: string[];
    fields: Array<any>;
    pagination_selector?: string;
    pagination_type?: string;
    max_pages?: number;
    wait_for_selector?: string;
    javascript_required?: boolean;
    tags?: string[];
  }) => {
    const response = await api.post('/templates', data)
    return response.data
  },
  
  delete: async (id: string) => {
    await api.delete(`/templates/${id}`)
  },
}

// Dataset Management API
export const datasetApi = {
  // Splits
  getSplitStats: async (projectId: string) => {
    const response = await api.get(`/dataset/splits/${projectId}/stats`)
    return response.data
  },
  
  assignSplits: async (data: { item_ids: string[]; split: 'train' | 'val' | 'test' | 'unassigned' }) => {
    const response = await api.post('/dataset/splits/assign', data)
    return response.data
  },
  
  autoSplit: async (data: {
    project_id: string;
    config: {
      train_ratio: number;
      val_ratio: number;
      test_ratio: number;
      stratify_by?: string;
      random_seed?: number;
      shuffle?: boolean;
    };
    filter_labeled_only?: boolean;
    filter_processed_only?: boolean;
    min_quality_score?: number;
    create_version?: boolean;
    version_name?: string;
    version_description?: string;
  }) => {
    const response = await api.post('/dataset/splits/auto', data)
    return response.data
  },
  
  resetSplits: async (projectId: string) => {
    const response = await api.post(`/dataset/splits/reset/${projectId}`)
    return response.data
  },
  
  // Statistics
  getStatistics: async (projectId: string) => {
    const response = await api.get(`/dataset/statistics/${projectId}`)
    return response.data
  },
  
  // Versions
  listVersions: async (projectId: string) => {
    const response = await api.get(`/dataset/versions/${projectId}`)
    return response.data
  },
  
  createVersion: async (data: {
    project_id: string;
    version: string;
    description?: string;
    parent_version_id?: string;
  }) => {
    const response = await api.post('/dataset/versions', data)
    return response.data
  },
  
  getVersion: async (projectId: string, versionId: string) => {
    const response = await api.get(`/dataset/versions/${projectId}/${versionId}`)
    return response.data
  },
  
  diffVersions: async (projectId: string, version1Id: string, version2Id: string) => {
    const response = await api.get(`/dataset/versions/${projectId}/diff/${version1Id}/${version2Id}`)
    return response.data
  },
  
  publishVersion: async (versionId: string) => {
    const response = await api.post(`/dataset/versions/${versionId}/publish`)
    return response.data
  },
  
  // Dataset Card
  getDatasetCard: async (projectId: string) => {
    const response = await api.get(`/dataset/cards/${projectId}`)
    return response.data
  },
  
  createDatasetCard: async (data: {
    project_id: string;
    title: string;
    description?: string;
    license?: string;
    languages?: string[];
    task_categories?: string[];
    tags?: string[];
  }) => {
    const response = await api.post('/dataset/cards', data)
    return response.data
  },
  
  updateDatasetCard: async (projectId: string, data: object) => {
    const response = await api.patch(`/dataset/cards/${projectId}`, data)
    return response.data
  },
  
  // Annotations
  listAnnotationTypes: async (projectId: string) => {
    const response = await api.get(`/dataset/annotations/types/${projectId}`)
    return response.data
  },
  
  createAnnotationType: async (data: {
    project_id: string;
    name: string;
    annotation_kind: string;
    schema?: object;
    color?: string;
    shortcut_key?: string;
  }) => {
    const response = await api.post('/dataset/annotations/types', data)
    return response.data
  },
  
  deleteAnnotationType: async (typeId: string) => {
    await api.delete(`/dataset/annotations/types/${typeId}`)
  },
  
  getItemAnnotations: async (itemId: string) => {
    const response = await api.get(`/dataset/annotations/items/${itemId}`)
    return response.data
  },
  
  annotateItem: async (itemId: string, data: { annotations: object; merge?: boolean }) => {
    const response = await api.post(`/dataset/annotations/items/${itemId}`, data)
    return response.data
  },
  
  // Augmentation
  listAugmentationRules: async (projectId: string) => {
    const response = await api.get(`/dataset/augmentation/rules/${projectId}`)
    return response.data
  },
  
  createAugmentationRule: async (data: {
    project_id: string;
    name: string;
    data_type: string;
    augmentation_type: string;
    parameters?: object;
    probability?: number;
    is_active?: boolean;
  }) => {
    const response = await api.post('/dataset/augmentation/rules', data)
    return response.data
  },
  
  deleteAugmentationRule: async (ruleId: string) => {
    await api.delete(`/dataset/augmentation/rules/${ruleId}`)
  },
  
  runAugmentation: async (data: {
    project_id: string;
    rule_ids?: string[];
    item_ids?: string[];
    max_augmented_per_item?: number;
    only_labeled?: boolean;
  }) => {
    const response = await api.post('/dataset/augmentation/run', data)
    return response.data
  },
  
  // Embeddings
  generateEmbeddings: async (projectId: string, recompute = false) => {
    const response = await api.post(`/dataset/embeddings/${projectId}/generate`, null, {
      params: { recompute }
    })
    return response.data
  },
  
  findSimilar: async (projectId: string, itemId: string, topK = 10) => {
    const response = await api.get(`/dataset/embeddings/${projectId}/similar/${itemId}`, {
      params: { top_k: topK }
    })
    return response.data
  },
  
  findDuplicatesByEmbedding: async (projectId: string, threshold = 0.95) => {
    const response = await api.get(`/dataset/embeddings/${projectId}/duplicates`, {
      params: { threshold }
    })
    return response.data
  },
  
  // Active Learning
  getActiveLearning: async (projectId: string, config: {
    strategy?: string;
    batch_size?: number;
    min_confidence?: number;
    max_confidence?: number;
    exclude_labeled?: boolean;
  } = {}) => {
    const response = await api.post(`/dataset/active-learning/${projectId}/suggestions`, config)
    return response.data
  },
}

// Scheduler API
export const schedulerApi = {
  start: async () => {
    const response = await api.post('/scheduler/start')
    return response.data
  },
  
  stop: async () => {
    const response = await api.post('/scheduler/stop')
    return response.data
  },
  
  getStats: async () => {
    const response = await api.get('/scheduler/stats')
    return response.data
  },
  
  listJobs: async (params?: { project_id?: string; active_only?: boolean }) => {
    const response = await api.get('/scheduler/jobs', { params })
    return response.data
  },
  
  getJob: async (id: string) => {
    const response = await api.get(`/scheduler/jobs/${id}`)
    return response.data
  },
  
  createJob: async (data: {
    name: string;
    schedule: {
      schedule_type: string;
      cron_expression?: string;
      interval_seconds?: number;
      run_at?: string;
      check_interval_seconds?: number;
      change_detection_selector?: string;
      condition_url?: string;
      condition_selector?: string;
      condition_value?: string;
      timezone?: string;
      max_runs?: number;
      expires_at?: string;
      retry_on_failure?: boolean;
      random_delay_seconds?: number;
      blackout_windows?: Array<{ start: string; end: string }>;
    };
    scrape_config: object;
    project_id: string;
    on_complete_webhook?: string;
    on_error_webhook?: string;
  }) => {
    const response = await api.post('/scheduler/jobs', data)
    return response.data
  },
  
  deleteJob: async (id: string) => {
    await api.delete(`/scheduler/jobs/${id}`)
  },
  
  pauseJob: async (id: string) => {
    const response = await api.post(`/scheduler/jobs/${id}/pause`)
    return response.data
  },
  
  resumeJob: async (id: string) => {
    const response = await api.post(`/scheduler/jobs/${id}/resume`)
    return response.data
  },
  
  getNextRuns: async (id: string, count?: number) => {
    const response = await api.get(`/scheduler/jobs/${id}/next-runs`, { params: { count } })
    return response.data
  },
  
  getDueJobs: async () => {
    const response = await api.get('/scheduler/jobs/due')
    return response.data
  },
  
  parseCron: async (expression: string) => {
    const response = await api.post('/scheduler/cron/parse', { expression })
    return response.data
  },
  
  getCronPresets: async () => {
    const response = await api.get('/scheduler/cron/presets')
    return response.data
  },
}

// Quality & Validation API
export const qualityApi = {
  // Inter-Annotator Agreement
  calculateAgreement: async (projectId: string, annotationField = 'labels') => {
    const response = await api.post('/quality/agreement/calculate', {
      project_id: projectId,
      annotation_field: annotationField
    })
    return response.data
  },
  
  getDisagreements: async (projectId: string, minAnnotators = 2) => {
    const response = await api.get(`/quality/agreement/disagreements/${projectId}`, {
      params: { min_annotators: minAnnotators }
    })
    return response.data
  },
  
  resolveDisagreement: async (itemId: string, finalLabel: string, resolutionNotes?: string) => {
    const response = await api.post(`/quality/agreement/resolve/${itemId}`, null, {
      params: { final_label: finalLabel, resolution_notes: resolutionNotes }
    })
    return response.data
  },
  
  // Data Leakage Detection
  checkLeakage: async (projectId: string, similarityThreshold = 0.8) => {
    const response = await api.post('/quality/leakage/check', {
      project_id: projectId,
      similarity_threshold: similarityThreshold
    })
    return response.data
  },
  
  checkExactDuplicates: async (projectId: string) => {
    const response = await api.get(`/quality/leakage/exact-duplicates/${projectId}`)
    return response.data
  },
  
  checkNearDuplicates: async (projectId: string, threshold = 0.8, sampleSize = 500) => {
    const response = await api.get(`/quality/leakage/near-duplicates/${projectId}`, {
      params: { threshold, sample_size: sampleSize }
    })
    return response.data
  },
  
  checkTemporalLeakage: async (projectId: string) => {
    const response = await api.get(`/quality/leakage/temporal/${projectId}`)
    return response.data
  },
  
  // Advanced Quality Metrics
  analyzeItemQuality: async (itemId: string) => {
    const response = await api.get(`/quality/metrics/item/${itemId}`)
    return response.data
  },
  
  batchQualityCheck: async (projectId: string, dataType?: string, limit = 100) => {
    const response = await api.get(`/quality/metrics/batch/${projectId}`, {
      params: { data_type: dataType, limit }
    })
    return response.data
  },
  
  // Data Validation
  validateSchema: async (projectId: string, schema: object) => {
    const response = await api.post('/quality/validation/schema', {
      project_id: projectId,
      schema
    })
    return response.data
  },
  
  checkCompleteness: async (projectId: string, fields?: string[]) => {
    const response = await api.get(`/quality/validation/completeness/${projectId}`, {
      params: { fields: fields?.join(',') }
    })
    return response.data
  },
  
  detectOutliers: async (projectId: string, field: string, method: 'iqr' | 'zscore' = 'iqr') => {
    const response = await api.post('/quality/validation/outliers', {
      project_id: projectId,
      field,
      method
    })
    return response.data
  },
  
  // Temporal Split
  temporalSplit: async (data: {
    project_id: string;
    train_ratio?: number;
    val_ratio?: number;
    test_ratio?: number;
    gap_days?: number;
  }) => {
    const response = await api.post('/quality/splits/temporal', data)
    return response.data
  },
  
  slidingWindowSplit: async (projectId: string, windowSizeDays = 30, stepSizeDays = 7, forecastHorizonDays = 7) => {
    const response = await api.get(`/quality/splits/sliding-window/${projectId}`, {
      params: {
        window_size_days: windowSizeDays,
        step_size_days: stepSizeDays,
        forecast_horizon_days: forecastHorizonDays
      }
    })
    return response.data
  },
  
  // Backup Management
  createBackup: async (projectId: string, includeFiles = true, compress = true) => {
    const response = await api.post('/quality/backup/create', {
      project_id: projectId,
      include_files: includeFiles,
      compress
    })
    return response.data
  },
  
  restoreBackup: async (backupPath: string, newProjectName?: string) => {
    const response = await api.post('/quality/backup/restore', {
      backup_path: backupPath,
      new_project_name: newProjectName
    })
    return response.data
  },
  
  listBackups: async (projectId?: string) => {
    const response = await api.get('/quality/backup/list', {
      params: { project_id: projectId }
    })
    return response.data
  },
  
  deleteBackup: async (backupName: string) => {
    const response = await api.delete(`/quality/backup/${backupName}`)
    return response.data
  },
  
  cleanupBackups: async (maxAgeDays = 30, maxBackupsPerProject = 5) => {
    const response = await api.post('/quality/backup/cleanup', null, {
      params: { max_age_days: maxAgeDays, max_backups_per_project: maxBackupsPerProject }
    })
    return response.data
  },
  
  // Audio Processing
  reduceNoise: async (itemId: string, noiseReductionAmount = 1.0, stationary = true) => {
    const response = await api.post('/quality/audio/reduce-noise', {
      item_id: itemId,
      noise_reduction_amount: noiseReductionAmount,
      stationary
    })
    return response.data
  },
  
  detectVoiceActivity: async (itemId: string, energyThreshold = 0.02, minSpeechDuration = 0.3) => {
    const response = await api.get(`/quality/audio/vad/${itemId}`, {
      params: { energy_threshold: energyThreshold, min_speech_duration: minSpeechDuration }
    })
    return response.data
  },
  
  // Speaker Identification
  analyzeSpeakers: async (projectId: string, similarityThreshold = 0.75, sampleLimit = 100) => {
    const response = await api.post('/quality/speaker/analyze', {
      project_id: projectId,
      similarity_threshold: similarityThreshold,
      sample_limit: sampleLimit
    })
    return response.data
  },
  
  diarizeAudio: async (itemId: string, numSpeakers?: number, minSegmentDuration = 1.0) => {
    const response = await api.get(`/quality/speaker/diarize/${itemId}`, {
      params: { num_speakers: numSpeakers, min_segment_duration: minSegmentDuration }
    })
    return response.data
  },
  
  // Multimodal
  createMultimodalGroup: async (projectId: string, itemIds: string[], groupName?: string, alignmentType = 'parallel') => {
    const response = await api.post('/quality/multimodal/group', {
      project_id: projectId,
      item_ids: itemIds,
      group_name: groupName,
      alignment_type: alignmentType
    })
    return response.data
  },
  
  getMultimodalGroup: async (groupId: string) => {
    const response = await api.get(`/quality/multimodal/group/${groupId}`)
    return response.data
  },
  
  computeMultimodalAlignment: async (groupId: string) => {
    const response = await api.get(`/quality/multimodal/alignment/${groupId}`)
    return response.data
  },
  
  autoAlignMultimodal: async (projectId: string, timeWindowSeconds = 60) => {
    const response = await api.post(`/quality/multimodal/auto-align/${projectId}`, null, {
      params: { time_window_seconds: timeWindowSeconds }
    })
    return response.data
  },
  
  getUnalignedItems: async (projectId: string) => {
    const response = await api.get(`/quality/multimodal/unaligned/${projectId}`)
    return response.data
  },
  
  listMultimodalGroups: async (projectId: string) => {
    const response = await api.get(`/quality/multimodal/list/${projectId}`)
    return response.data
  },
  
  deleteMultimodalGroup: async (groupId: string) => {
    const response = await api.delete(`/quality/multimodal/group/${groupId}`)
    return response.data
  },
  
  crossModalSearch: async (projectId: string, queryText: string, targetModality = 'image', limit = 10) => {
    const response = await api.post('/quality/multimodal/search', {
      project_id: projectId,
      query_text: queryText,
      target_modality: targetModality,
      limit
    })
    return response.data
  },
  
  mergeMultimodalGroups: async (groupIds: string[], newGroupName?: string) => {
    const response = await api.post('/quality/multimodal/merge', {
      group_ids: groupIds,
      new_group_name: newGroupName
    })
    return response.data
  },
  
  autoAlignByContent: async (projectId: string, similarityThreshold = 0.3, maxGroupSize = 5) => {
    const response = await api.post(`/quality/multimodal/auto-align-content/${projectId}`, null, {
      params: { similarity_threshold: similarityThreshold, max_group_size: maxGroupSize }
    })
    return response.data
  },
  
  getMultimodalStatistics: async (projectId: string) => {
    const response = await api.get(`/quality/multimodal/statistics/${projectId}`)
    return response.data
  },
  
  // Time Series
  analyzeTimeSeries: async (series: number[], includeStationarity = true, includeDecomposition = true, includeAnomalies = true) => {
    const response = await api.post('/quality/timeseries/analyze', {
      series,
      include_stationarity: includeStationarity,
      include_decomposition: includeDecomposition,
      include_anomalies: includeAnomalies
    })
    return response.data
  },
  
  analyzeProjectTimeSeries: async (projectId: string, valueField = 'value') => {
    const response = await api.get(`/quality/timeseries/project/${projectId}`, {
      params: { value_field: valueField }
    })
    return response.data
  },
  
  interpolateMissing: async (series: (number | null)[], method = 'linear') => {
    const response = await api.post('/quality/timeseries/interpolate', {
      series,
      method
    })
    return response.data
  },
  
  detectTimeSeriesAnomalies: async (series: number[], method = 'zscore', threshold = 3.0) => {
    const response = await api.post('/quality/timeseries/anomalies', {
      series,
      method,
      threshold
    })
    return response.data
  },
  
  // Video Quality
  computeVideoHash: async (itemId: string) => {
    const response = await api.post(`/quality/video/hash/${itemId}`)
    return response.data
  },
  
  findDuplicateVideos: async (projectId: string, similarityThreshold = 0.85) => {
    const response = await api.get(`/quality/video/duplicates/${projectId}`, {
      params: { similarity_threshold: similarityThreshold }
    })
    return response.data
  },
  
  detectVideoScenes: async (itemId: string, threshold = 0.3, minSceneLength = 1.0) => {
    const response = await api.get(`/quality/video/scenes/${itemId}`, {
      params: { threshold, min_scene_length: minSceneLength }
    })
    return response.data
  },
  
  analyzeVideoQuality: async (itemId: string) => {
    const response = await api.get(`/quality/video/quality/${itemId}`)
    return response.data
  },
  
  generateSmartThumbnail: async (itemId: string) => {
    const response = await api.post(`/quality/video/thumbnail/${itemId}`)
    return response.data
  },
  
  batchAnalyzeVideos: async (projectId: string) => {
    const response = await api.get(`/quality/video/batch-analyze/${projectId}`)
    return response.data
  },
  
  // Image Quality
  extractImageExif: async (itemId: string) => {
    const response = await api.get(`/quality/image/exif/${itemId}`)
    return response.data
  },
  
  analyzeImageColors: async (itemId: string, includeHistogram = false) => {
    const response = await api.get(`/quality/image/colors/${itemId}`, {
      params: { include_histogram: includeHistogram }
    })
    return response.data
  },
  
  computeImageHash: async (itemId: string) => {
    const response = await api.post(`/quality/image/hash/${itemId}`)
    return response.data
  },
  
  findSimilarImages: async (projectId: string, similarityThreshold = 0.9) => {
    const response = await api.get(`/quality/image/similar/${projectId}`, {
      params: { similarity_threshold: similarityThreshold }
    })
    return response.data
  },
  
  batchAnalyzeImages: async (projectId: string) => {
    const response = await api.get(`/quality/image/batch-analyze/${projectId}`)
    return response.data
  },
  
  // Tabular Data
  analyzeTabularSchema: async (projectId: string, sampleSize = 100) => {
    const response = await api.get(`/quality/tabular/schema/${projectId}`, {
      params: { sample_size: sampleSize }
    })
    return response.data
  },
  
  computeTabularCorrelations: async (projectId: string, method = 'pearson') => {
    const response = await api.get(`/quality/tabular/correlations/${projectId}`, {
      params: { method }
    })
    return response.data
  },
  
  computeTabularStatistics: async (projectId: string) => {
    const response = await api.get(`/quality/tabular/statistics/${projectId}`)
    return response.data
  },
  
  detectTabularQualityIssues: async (projectId: string) => {
    const response = await api.get(`/quality/tabular/quality-issues/${projectId}`)
    return response.data
  },
  
  // External Annotation Tools
  exportToCvat: async (projectId: string) => {
    const response = await api.get(`/quality/export/cvat/${projectId}`)
    return response.data
  },
  
  exportToLabelbox: async (projectId: string, includePredictions = false) => {
    const response = await api.get(`/quality/export/labelbox/${projectId}`, {
      params: { include_predictions: includePredictions }
    })
    return response.data
  },
  
  exportToLabelStudio: async (projectId: string) => {
    const response = await api.get(`/quality/export/label-studio/${projectId}`)
    return response.data
  },
  
  // Graph Dataset
  createGraph: async (projectId: string, nodeField = 'id', edgeSourceField = 'source', edgeTargetField = 'target') => {
    const response = await api.get(`/quality/graph/create/${projectId}`, {
      params: { node_field: nodeField, edge_source_field: edgeSourceField, edge_target_field: edgeTargetField }
    })
    return response.data
  },
  
  analyzeGraph: async (projectId: string) => {
    const response = await api.get(`/quality/graph/analyze/${projectId}`)
    return response.data
  },
  
  exportGraph: async (projectId: string, format = 'graphml') => {
    const response = await api.get(`/quality/graph/export/${projectId}`, {
      params: { format }
    })
    return response.data
  },
  
  computePageRank: async (projectId: string, damping = 0.85) => {
    const response = await api.get(`/quality/graph/pagerank/${projectId}`, {
      params: { damping }
    })
    return response.data
  },
  
  findGraphPath: async (projectId: string, start: string, end: string) => {
    const response = await api.get(`/quality/graph/path/${projectId}`, {
      params: { start, end }
    })
    return response.data
  },
  
  getGraphComponents: async (projectId: string) => {
    const response = await api.get(`/quality/graph/components/${projectId}`)
    return response.data
  },
  
  // 3D Dataset
  parsePointCloud: async (itemId: string) => {
    const response = await api.get(`/quality/3d/parse/${itemId}`)
    return response.data
  },
  
  analyze3dData: async (projectId: string) => {
    const response = await api.get(`/quality/3d/analyze/${projectId}`)
    return response.data
  },
  
  export3d: async (itemId: string, format = 'ply') => {
    const response = await api.get(`/quality/3d/export/${itemId}`, {
      params: { format }
    })
    return response.data
  },
  
  detectGroundPlane: async (itemId: string, zThreshold = 0.1) => {
    const response = await api.get(`/quality/3d/ground-plane/${itemId}`, {
      params: { z_threshold: zThreshold }
    })
    return response.data
  },
  
  segmentByHeight: async (itemId: string, numSegments = 5) => {
    const response = await api.get(`/quality/3d/segments/${itemId}`, {
      params: { num_segments: numSegments }
    })
    return response.data
  },
  
  downsamplePointCloud: async (itemId: string, voxelSize = 0.1) => {
    const response = await api.post(`/quality/3d/downsample/${itemId}`, null, {
      params: { voxel_size: voxelSize }
    })
    return response.data
  },
  
  removePointCloudOutliers: async (itemId: string, kNeighbors = 10, stdRatio = 2.0) => {
    const response = await api.post(`/quality/3d/remove-outliers/${itemId}`, null, {
      params: { k_neighbors: kNeighbors, std_ratio: stdRatio }
    })
    return response.data
  },
}

// Worker Monitor API
export const workersApi = {
  getStatus: async () => {
    const response = await api.get('/workers/status')
    return response.data
  },
  
  getActiveTasks: async () => {
    const response = await api.get('/workers/tasks/active')
    return response.data
  },
  
  getScheduledTasks: async () => {
    const response = await api.get('/workers/tasks/scheduled')
    return response.data
  },
  
  getReservedTasks: async () => {
    const response = await api.get('/workers/tasks/reserved')
    return response.data
  },
  
  getQueues: async () => {
    const response = await api.get('/workers/queues')
    return response.data
  },
  
  getStats: async () => {
    const response = await api.get('/workers/stats')
    return response.data
  },
  
  getTaskResult: async (taskId: string) => {
    const response = await api.get(`/workers/task/${taskId}`)
    return response.data
  },
  
  revokeTask: async (taskId: string, terminate = false) => {
    const response = await api.post(`/workers/tasks/${taskId}/revoke`, null, {
      params: { terminate }
    })
    return response.data
  },
  
  purgeQueue: async (queueName: string) => {
    const response = await api.post(`/workers/purge/${queueName}`)
    return response.data
  },
}

export default api
