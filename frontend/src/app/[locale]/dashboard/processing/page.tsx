'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, processingApi } from '@/lib/api'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslations } from 'next-intl'
import {
  Settings,
  FileText,
  Image as ImageIcon,
  Music,
  Video,
  Loader2,
  Play,
  CheckCircle,
  AlertTriangle,
  Wand2,
  Sparkles,
  Languages,
  Scissors,
  Volume2,
  Film,
  Mic,
  FileAudio,
  Clapperboard,
  ScanSearch,
  Subtitles,
  Gauge,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const processingTutorial: TutorialSection[] = [
  {
    title: 'Processing Settings Overview',
    content: 'Configure how your data is processed for ML preparation. Different processing options are available for text, images, audio, and video content.',
    tips: [
      'Processing extracts features and metadata from your raw data',
      'Enable only the options you need to save processing time',
      'Processed data is ready for labeling and training',
    ],
  },
  {
    title: 'Text Processing',
    content: 'Text processing includes cleaning, language detection, keyword extraction, and entity recognition (NER). These features help prepare text data for NLP models.',
    steps: [
      { title: 'Clean Text', description: 'Normalize unicode, remove extra whitespace and HTML tags' },
      { title: 'Detect Language', description: 'Automatically identify the text language' },
      { title: 'Extract Keywords', description: 'Find important terms and phrases' },
      { title: 'Extract Entities', description: 'Identify names, places, organizations (NER)' },
    ],
  },
  {
    title: 'Image Processing',
    content: 'Image processing generates thumbnails, extracts dominant colors, and can detect objects using YOLO models. These features prepare images for computer vision tasks.',
    tips: [
      'Thumbnails speed up data browsing and preview',
      'Color extraction is useful for visual categorization',
      'Object detection adds automatic annotations',
    ],
    warning: 'Object detection requires YOLO models and may take longer for large datasets.',
  },
  {
    title: 'Audio Processing',
    content: 'Audio processing extracts file info, transcribes speech to text using OpenAI Whisper, and can extract audio features like MFCC for audio ML tasks.',
    steps: [
      { title: 'Get Info', description: 'Extract duration, bitrate, and channel information' },
      { title: 'Transcribe', description: 'Convert speech to text using Whisper (select model size)' },
      { title: 'Extract Features', description: 'Compute MFCC and spectral features for audio ML' },
    ],
    warning: 'Whisper transcription: Larger models are more accurate but significantly slower.',
  },
  {
    title: 'Video Processing',
    content: 'Video processing offers comprehensive options: thumbnails, transcription, audio extraction, frame extraction, GIF generation, and scene detection.',
    tips: [
      'Generate thumbnails for quick video preview',
      'Transcribe audio tracks with Whisper for searchable content',
      'Extract frames for image-based analysis of video content',
      'Scene detection helps identify key moments in videos',
    ],
    warning: 'Video processing requires FFmpeg installed on the server.',
  },
  {
    title: 'Running Processing',
    content: 'Select a project and processing type, then click "Process All Items" to begin. Enable "Reprocess" to re-run processing on already processed items.',
    steps: [
      { title: 'Select Project', description: 'Choose the project containing data to process' },
      { title: 'Choose Type', description: 'Select auto-detect or specific data type' },
      { title: 'Configure Options', description: 'Enable the processing features you need' },
      { title: 'Run Processing', description: 'Click "Process All Items" to start' },
    ],
  },
]

// Default processing options
const defaultTextOptions = {
  clean: true,
  clean_options: {
    normalize_unicode: true,
    remove_extra_whitespace: true,
    remove_html_tags: true,
    lowercase: false,
  },
  detect_language: true,
  compute_stats: true,
  extract_keywords: true,
  extract_entities: false,
}

const defaultImageOptions = {
  resize: null as number[] | null,
  resize_method: 'fit',
  convert_format: null as string | null,
  optimize_quality: 85,
  generate_thumbnail: true,
  thumbnail_size: [128, 128],
  extract_colors: true,
  detect_objects: false,
}

const defaultAudioOptions = {
  get_info: true,
  transcribe: false,
  whisper_model: 'base',
  whisper_language: null as string | null,
  extract_features: false,
  normalize_audio: false,
  convert_format: null as string | null,
}

const defaultVideoOptions = {
  get_info: true,
  generate_thumbnail: true,
  thumbnail_offset: 1.0,
  thumbnail_size: [320, 180],
  // Transcription
  transcribe: false,
  whisper_model: 'base',
  language: null as string | null,
  transcribe_task: 'transcribe',
  include_segments: true,
  generate_subtitles: false,
  subtitle_format: 'srt',
  // Audio/Frames
  extract_audio: false,
  audio_format: 'mp3',
  extract_frames: false,
  frame_fps: 1.0,
  max_frames: 10,
  // GIF
  generate_gif: false,
  gif_duration: 3.0,
  gif_fps: 10,
  // Scene detection
  detect_scenes: false,
  scene_threshold: 0.3,
}

export default function ProcessingPage() {
  const t = useTranslations()
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState('')
  const [processingType, setProcessingType] = useState<'auto' | 'text' | 'image' | 'audio' | 'video'>('auto')
  const [reprocess, setReprocess] = useState(false)
  
  // Processing options state
  const [textOptions, setTextOptions] = useState(defaultTextOptions)
  const [imageOptions, setImageOptions] = useState(defaultImageOptions)
  const [audioOptions, setAudioOptions] = useState(defaultAudioOptions)
  const [videoOptions, setVideoOptions] = useState(defaultVideoOptions)

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const processAllMutation = useMutation({
    mutationFn: () => processingApi.processAll(projectId, processingType, reprocess),
    onSuccess: (data) => {
      toast.success(`Processed ${data.processed} items`)
      queryClient.invalidateQueries({ queryKey: ['data'] })
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Processing failed')
    },
  })

  const computeQualityMutation = useMutation({
    mutationFn: () => processingApi.computeQualityScores(projectId, reprocess),
    onSuccess: (data) => {
      toast.success(`Computed quality for ${data.processed} items`)
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to compute quality')
    },
  })

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Processing Settings Guide"
        description="Learn how to configure data processing for ML preparation"
        sections={processingTutorial}
        storageKey="processing"
      />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{t('nav.processing')}</h1>
        <p className="text-surface-400">{t('processing.description') || 'Configure and run data processing for text, images, audio, and video'}</p>
      </div>

      {/* Project & Type Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div>
          <label className="block text-sm font-medium mb-2">Project</label>
          <select
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
          >
            <option value="">Select a project</option>
            {projects?.map((project: any) => (
              <option key={project.id} value={project.id}>
                {project.name} ({project.data_count} items)
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Processing Type</label>
          <select
            value={processingType}
            onChange={(e) => setProcessingType(e.target.value as any)}
            className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
          >
            <option value="auto">Auto-detect</option>
            <option value="text">Text Only</option>
            <option value="image">Image Only</option>
            <option value="audio">Audio Only</option>
            <option value="video">Video Only</option>
          </select>
        </div>

        <div className="flex items-end">
          <label className="flex items-center gap-3 cursor-pointer p-3 rounded-xl bg-surface-800 border border-surface-700 w-full">
            <input
              type="checkbox"
              checked={reprocess}
              onChange={(e) => setReprocess(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm">Reprocess already processed items</span>
          </label>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={() => processAllMutation.mutate()}
          disabled={!projectId || processAllMutation.isPending}
          className="p-6 rounded-2xl bg-gradient-to-r from-brand-600/20 to-purple-600/20 border border-brand-500/30 hover:border-brand-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-brand-500/20 flex items-center justify-center">
              {processAllMutation.isPending ? (
                <Loader2 className="w-7 h-7 animate-spin text-brand-400" />
              ) : (
                <Wand2 className="w-7 h-7 text-brand-400" />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-lg">Process All Items</h3>
              <p className="text-sm text-surface-400">Run processing on all unprocessed items</p>
            </div>
          </div>
        </motion.button>

        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          onClick={() => computeQualityMutation.mutate()}
          disabled={!projectId || computeQualityMutation.isPending}
          className="p-6 rounded-2xl bg-gradient-to-r from-green-600/20 to-emerald-600/20 border border-green-500/30 hover:border-green-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-left"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-green-500/20 flex items-center justify-center">
              {computeQualityMutation.isPending ? (
                <Loader2 className="w-7 h-7 animate-spin text-green-400" />
              ) : (
                <Gauge className="w-7 h-7 text-green-400" />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-lg">Compute Quality Scores</h3>
              <p className="text-sm text-surface-400">Calculate data quality for all items</p>
            </div>
          </div>
        </motion.button>
      </div>

      {/* Processing Options Tabs */}
      <div className="space-y-6">
        {/* Text Processing Options */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Text Processing</h3>
              <p className="text-sm text-surface-400">Clean, analyze, and extract information from text</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={textOptions.clean}
                onChange={(e) => setTextOptions({ ...textOptions, clean: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Clean Text</p>
                <p className="text-xs text-surface-500">Normalize and clean text content</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={textOptions.detect_language}
                onChange={(e) => setTextOptions({ ...textOptions, detect_language: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Languages className="w-4 h-4" /> Detect Language
                </p>
                <p className="text-xs text-surface-500">Identify text language</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={textOptions.extract_keywords}
                onChange={(e) => setTextOptions({ ...textOptions, extract_keywords: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Extract Keywords</p>
                <p className="text-xs text-surface-500">Find important keywords</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={textOptions.extract_entities}
                onChange={(e) => setTextOptions({ ...textOptions, extract_entities: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Extract Entities</p>
                <p className="text-xs text-surface-500">Find names, places, etc.</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={textOptions.compute_stats}
                onChange={(e) => setTextOptions({ ...textOptions, compute_stats: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Compute Stats</p>
                <p className="text-xs text-surface-500">Word count, readability, etc.</p>
              </div>
            </label>
          </div>
        </motion.div>

        {/* Image Processing Options */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-green-500/10 flex items-center justify-center">
              <ImageIcon className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Image Processing</h3>
              <p className="text-sm text-surface-400">Resize, optimize, and analyze images</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={imageOptions.generate_thumbnail}
                onChange={(e) => setImageOptions({ ...imageOptions, generate_thumbnail: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Generate Thumbnails</p>
                <p className="text-xs text-surface-500">Create preview images</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={imageOptions.extract_colors}
                onChange={(e) => setImageOptions({ ...imageOptions, extract_colors: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Extract Colors</p>
                <p className="text-xs text-surface-500">Dominant color palette</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={imageOptions.detect_objects}
                onChange={(e) => setImageOptions({ ...imageOptions, detect_objects: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <ScanSearch className="w-4 h-4" /> Detect Objects
                </p>
                <p className="text-xs text-surface-500">AI object detection</p>
              </div>
            </label>

            <div className="p-4 rounded-xl bg-surface-800/50">
              <p className="font-medium mb-2">Quality Level</p>
              <input
                type="range"
                min="50"
                max="100"
                value={imageOptions.optimize_quality}
                onChange={(e) => setImageOptions({ ...imageOptions, optimize_quality: parseInt(e.target.value) })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-surface-500">
                <span>Smaller</span>
                <span>{imageOptions.optimize_quality}%</span>
                <span>Better</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Audio Processing Options */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <Music className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Audio Processing</h3>
              <p className="text-sm text-surface-400">Transcribe, analyze, and extract audio features</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={audioOptions.get_info}
                onChange={(e) => setAudioOptions({ ...audioOptions, get_info: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <FileAudio className="w-4 h-4" /> Get Audio Info
                </p>
                <p className="text-xs text-surface-500">Duration, bitrate, channels</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={audioOptions.transcribe}
                onChange={(e) => setAudioOptions({ ...audioOptions, transcribe: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Mic className="w-4 h-4" /> Transcribe (Whisper)
                </p>
                <p className="text-xs text-surface-500">Speech to text</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={audioOptions.extract_features}
                onChange={(e) => setAudioOptions({ ...audioOptions, extract_features: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Extract Features</p>
                <p className="text-xs text-surface-500">MFCC, spectral features</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={audioOptions.normalize_audio}
                onChange={(e) => setAudioOptions({ ...audioOptions, normalize_audio: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Volume2 className="w-4 h-4" /> Normalize Audio
                </p>
                <p className="text-xs text-surface-500">Balance volume levels</p>
              </div>
            </label>

            {audioOptions.transcribe && (
              <div className="p-4 rounded-xl bg-surface-800/50">
                <p className="font-medium mb-2">Whisper Model</p>
                <select
                  value={audioOptions.whisper_model}
                  onChange={(e) => setAudioOptions({ ...audioOptions, whisper_model: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                >
                  <option value="tiny">Tiny (fastest)</option>
                  <option value="base">Base (balanced)</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large (most accurate)</option>
                </select>
              </div>
            )}
          </div>
        </motion.div>

        {/* Video Processing Options */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="p-6 rounded-2xl glass"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
              <Video className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Video Processing</h3>
              <p className="text-sm text-surface-400">Extract frames, audio, transcribe, and analyze video content</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.get_info}
                onChange={(e) => setVideoOptions({ ...videoOptions, get_info: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Film className="w-4 h-4" /> Get Video Info
                </p>
                <p className="text-xs text-surface-500">Duration, resolution, FPS</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.generate_thumbnail}
                onChange={(e) => setVideoOptions({ ...videoOptions, generate_thumbnail: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium">Generate Thumbnail</p>
                <p className="text-xs text-surface-500">Preview frame</p>
              </div>
            </label>

            {/* Transcription - NEW */}
            <label className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-500/20 cursor-pointer hover:border-purple-500/40 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.transcribe}
                onChange={(e) => setVideoOptions({ ...videoOptions, transcribe: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2 text-purple-400">
                  <Mic className="w-4 h-4" /> Transcribe Video
                </p>
                <p className="text-xs text-surface-500">Speech to text with Whisper</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.extract_audio}
                onChange={(e) => setVideoOptions({ ...videoOptions, extract_audio: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Volume2 className="w-4 h-4" /> Extract Audio
                </p>
                <p className="text-xs text-surface-500">Save audio track</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.extract_frames}
                onChange={(e) => setVideoOptions({ ...videoOptions, extract_frames: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <ImageIcon className="w-4 h-4" /> Extract Frames
                </p>
                <p className="text-xs text-surface-500">Save video frames as images</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.generate_gif}
                onChange={(e) => setVideoOptions({ ...videoOptions, generate_gif: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Clapperboard className="w-4 h-4" /> Generate GIF
                </p>
                <p className="text-xs text-surface-500">Animated preview</p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-4 rounded-xl bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors">
              <input
                type="checkbox"
                checked={videoOptions.detect_scenes}
                onChange={(e) => setVideoOptions({ ...videoOptions, detect_scenes: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <div>
                <p className="font-medium flex items-center gap-2">
                  <Scissors className="w-4 h-4" /> Detect Scenes
                </p>
                <p className="text-xs text-surface-500">Find scene changes</p>
              </div>
            </label>

            {/* Transcription Options */}
            {videoOptions.transcribe && (
              <>
                <div className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/20">
                  <p className="font-medium mb-2 text-purple-400">Whisper Model</p>
                  <select
                    value={videoOptions.whisper_model}
                    onChange={(e) => setVideoOptions({ ...videoOptions, whisper_model: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                  >
                    <option value="tiny">Tiny (fastest)</option>
                    <option value="base">Base (balanced)</option>
                    <option value="small">Small</option>
                    <option value="medium">Medium</option>
                    <option value="large">Large (most accurate)</option>
                  </select>
                </div>

                <label className="flex items-center gap-3 p-4 rounded-xl bg-purple-500/5 border border-purple-500/20 cursor-pointer hover:border-purple-500/40 transition-colors">
                  <input
                    type="checkbox"
                    checked={videoOptions.generate_subtitles}
                    onChange={(e) => setVideoOptions({ ...videoOptions, generate_subtitles: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <div>
                    <p className="font-medium flex items-center gap-2 text-purple-400">
                      <Subtitles className="w-4 h-4" /> Generate Subtitles
                    </p>
                    <p className="text-xs text-surface-500">Create SRT/VTT files</p>
                  </div>
                </label>

                {videoOptions.generate_subtitles && (
                  <div className="p-4 rounded-xl bg-purple-500/5 border border-purple-500/20">
                    <p className="font-medium mb-2 text-purple-400">Subtitle Format</p>
                    <select
                      value={videoOptions.subtitle_format}
                      onChange={(e) => setVideoOptions({ ...videoOptions, subtitle_format: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                    >
                      <option value="srt">SRT</option>
                      <option value="vtt">WebVTT</option>
                      <option value="txt">Plain Text</option>
                    </select>
                  </div>
                )}
              </>
            )}

            {videoOptions.generate_thumbnail && (
              <div className="p-4 rounded-xl bg-surface-800/50">
                <p className="font-medium mb-2">Thumbnail Offset (seconds)</p>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={videoOptions.thumbnail_offset}
                  onChange={(e) => setVideoOptions({ ...videoOptions, thumbnail_offset: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                />
              </div>
            )}

            {videoOptions.extract_frames && (
              <>
                <div className="p-4 rounded-xl bg-surface-800/50">
                  <p className="font-medium mb-2">Frames Per Second</p>
                  <input
                    type="number"
                    min="0.1"
                    max="30"
                    step="0.5"
                    value={videoOptions.frame_fps}
                    onChange={(e) => setVideoOptions({ ...videoOptions, frame_fps: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                  />
                </div>
                <div className="p-4 rounded-xl bg-surface-800/50">
                  <p className="font-medium mb-2">Max Frames</p>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={videoOptions.max_frames}
                    onChange={(e) => setVideoOptions({ ...videoOptions, max_frames: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                  />
                </div>
              </>
            )}

            {videoOptions.generate_gif && (
              <div className="p-4 rounded-xl bg-surface-800/50">
                <p className="font-medium mb-2">GIF Duration (seconds)</p>
                <input
                  type="number"
                  min="1"
                  max="10"
                  step="0.5"
                  value={videoOptions.gif_duration}
                  onChange={(e) => setVideoOptions({ ...videoOptions, gif_duration: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                />
              </div>
            )}

            {videoOptions.extract_audio && (
              <div className="p-4 rounded-xl bg-surface-800/50">
                <p className="font-medium mb-2">Audio Format</p>
                <select
                  value={videoOptions.audio_format}
                  onChange={(e) => setVideoOptions({ ...videoOptions, audio_format: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-700 border border-surface-600"
                >
                  <option value="mp3">MP3</option>
                  <option value="wav">WAV</option>
                  <option value="aac">AAC</option>
                  <option value="flac">FLAC</option>
                </select>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Info Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="mt-8 p-6 rounded-2xl bg-surface-800/50 border border-surface-700"
      >
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          Processing Notes
        </h3>
        <ul className="text-sm text-surface-400 space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-yellow-400">•</span>
            <span><strong>Audio Transcription</strong> uses OpenAI Whisper. Larger models are more accurate but slower.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-yellow-400">•</span>
            <span><strong>Video Processing</strong> requires FFmpeg installed on the server.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-yellow-400">•</span>
            <span><strong>Object Detection</strong> uses YOLO models and may take longer for large datasets.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-yellow-400">•</span>
            <span>Processing runs in background. Check the <strong>Workers</strong> page for progress.</span>
          </li>
        </ul>
      </motion.div>
    </div>
  )
}
