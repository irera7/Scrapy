'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datasetApi, projectsApi } from '@/lib/api'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslations } from 'next-intl'
import {
  Wand2,
  Plus,
  Trash2,
  Play,
  Loader2,
  Settings,
  Image as ImageIcon,
  FileText,
  Music,
  Video,
  ToggleLeft,
  ToggleRight,
  Shuffle,
  FlipHorizontal,
  FlipVertical,
  RotateCw,
  Sun,
  Contrast,
  Crop,
  Droplets,
  Languages,
  Replace,
  ArrowLeftRight,
  Eraser,
  Volume2,
  Waves,
  Clock,
  Gauge,
  Palette,
  Filter,
  Zap,
  Wind,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const augmentationTutorial: TutorialSection[] = [
  {
    title: 'Data Augmentation Overview',
    content: 'Data augmentation creates synthetic variations of your existing data to expand your dataset. This helps improve model generalization and reduce overfitting.',
    tips: [
      'Augmentation is especially useful for small datasets',
      'Different augmentations suit different ML tasks',
      'Start with conservative settings and increase gradually',
    ],
  },
  {
    title: 'Creating Augmentation Rules',
    content: 'Rules define which augmentations to apply to your data.',
    steps: [
      { title: 'Select Project', description: 'Choose the project containing data to augment' },
      { title: 'Click Add Rule', description: 'Open the rule creation modal' },
      { title: 'Choose Data Type', description: 'Select text, image, audio, or video' },
      { title: 'Select Augmentation', description: 'Pick the transformation to apply' },
      { title: 'Set Probability', description: 'Define how often this rule applies' },
    ],
  },
  {
    title: 'Text Augmentations',
    content: 'Transform text data while preserving meaning.',
    steps: [
      { title: 'Synonym Replacement', description: 'Replace words with synonyms' },
      { title: 'Random Swap', description: 'Randomly swap word positions' },
      { title: 'Random Deletion', description: 'Remove random words' },
      { title: 'Random Insertion', description: 'Insert random relevant words' },
      { title: 'Add Typos', description: 'Simulate typing errors' },
    ],
    tips: [
      'Synonym replacement works best for classification tasks',
      'Use moderate settings to avoid destroying semantic meaning',
    ],
  },
  {
    title: 'Image Augmentations',
    content: 'Transform images to create variations.',
    steps: [
      { title: 'Flip H/V', description: 'Mirror images horizontally or vertically' },
      { title: 'Rotation', description: 'Rotate images by random angles' },
      { title: 'Brightness/Contrast', description: 'Adjust lighting conditions' },
      { title: 'Crop', description: 'Random cropping and resize' },
      { title: 'Noise/Blur', description: 'Add noise or blur effects' },
      { title: 'Color Jitter', description: 'Vary hue, saturation, brightness' },
    ],
    tips: [
      'Horizontal flip is safe for most tasks (not text/faces)',
      'Color jitter helps with lighting variation robustness',
    ],
  },
  {
    title: 'Audio Augmentations',
    content: 'Transform audio files to create variations.',
    steps: [
      { title: 'Speed Change', description: 'Speed up or slow down audio (0.8x-1.2x)' },
      { title: 'Pitch Shift', description: 'Change pitch up or down' },
      { title: 'Add Noise', description: 'Add background noise' },
      { title: 'Time Stretch', description: 'Stretch or compress duration' },
      { title: 'Reverb', description: 'Add room reverb effect' },
    ],
  },
  {
    title: 'Running Augmentation',
    content: 'Configure and execute the augmentation process.',
    steps: [
      { title: 'Set Count', description: 'How many augmented versions per original item' },
      { title: 'Only Labeled', description: 'Option to only augment labeled items' },
      { title: 'Click Run', description: 'Execute all configured rules' },
    ],
    tips: [
      'Start with 1-2 augmentations per item',
      'Enable "Only labeled items" to preserve test data integrity',
      'Augmented items inherit labels from original items',
    ],
    warning: 'Augmentation creates new data items. Monitor storage usage for large datasets.',
  },
]

const TEXT_AUGMENTATIONS = [
  { value: 'text_synonym', label: 'Synonym Replacement', icon: Replace, description: 'Replace words with synonyms' },
  { value: 'text_random_swap', label: 'Random Word Swap', icon: ArrowLeftRight, description: 'Randomly swap word positions' },
  { value: 'text_random_delete', label: 'Random Deletion', icon: Eraser, description: 'Randomly delete words' },
  { value: 'text_random_insert', label: 'Random Insertion', icon: Plus, description: 'Randomly insert words' },
  { value: 'text_noise', label: 'Add Typos', icon: Zap, description: 'Add character-level noise' },
]

const IMAGE_AUGMENTATIONS = [
  { value: 'image_flip_horizontal', label: 'Horizontal Flip', icon: FlipHorizontal, description: 'Flip image horizontally' },
  { value: 'image_flip_vertical', label: 'Vertical Flip', icon: FlipVertical, description: 'Flip image vertically' },
  { value: 'image_rotate', label: 'Random Rotation', icon: RotateCw, description: 'Rotate up to ±30 degrees' },
  { value: 'image_brightness', label: 'Brightness', icon: Sun, description: 'Adjust brightness randomly' },
  { value: 'image_contrast', label: 'Contrast', icon: Contrast, description: 'Adjust contrast randomly' },
  { value: 'image_crop', label: 'Random Crop', icon: Crop, description: 'Random crop and resize' },
  { value: 'image_noise', label: 'Add Noise', icon: Droplets, description: 'Add Gaussian noise' },
  { value: 'image_blur', label: 'Blur', icon: Wind, description: 'Apply Gaussian blur' },
  { value: 'image_color_jitter', label: 'Color Jitter', icon: Shuffle, description: 'Random color variations' },
  { value: 'image_grayscale', label: 'Grayscale', icon: Filter, description: 'Convert to grayscale' },
]

const AUDIO_AUGMENTATIONS = [
  { value: 'audio_speed', label: 'Speed Change', icon: Gauge, description: 'Change playback speed (0.8x-1.2x)' },
  { value: 'audio_pitch', label: 'Pitch Shift', icon: Waves, description: 'Shift pitch up or down' },
  { value: 'audio_noise', label: 'Add Noise', icon: Droplets, description: 'Add background noise' },
  { value: 'audio_time_stretch', label: 'Time Stretch', icon: Clock, description: 'Stretch or compress time' },
  { value: 'audio_reverb', label: 'Add Reverb', icon: Wind, description: 'Add reverb effect' },
  { value: 'audio_volume', label: 'Volume Change', icon: Volume2, description: 'Random volume adjustment' },
  { value: 'audio_time_shift', label: 'Time Shift', icon: ArrowLeftRight, description: 'Shift audio in time' },
  { value: 'audio_low_pass', label: 'Low-Pass Filter', icon: Filter, description: 'Apply low-pass filter' },
]

const VIDEO_AUGMENTATIONS = [
  { value: 'video_flip_horizontal', label: 'Horizontal Flip', icon: FlipHorizontal, description: 'Flip video horizontally' },
  { value: 'video_flip_vertical', label: 'Vertical Flip', icon: FlipVertical, description: 'Flip video vertically' },
  { value: 'video_rotate', label: 'Rotation', icon: RotateCw, description: 'Rotate video (±15 degrees)' },
  { value: 'video_speed', label: 'Speed Change', icon: Gauge, description: 'Change playback speed (0.5x-2x)' },
  { value: 'video_brightness', label: 'Brightness', icon: Sun, description: 'Adjust brightness' },
  { value: 'video_contrast', label: 'Contrast', icon: Contrast, description: 'Adjust contrast' },
  { value: 'video_saturation', label: 'Saturation', icon: Palette, description: 'Adjust color saturation' },
  { value: 'video_crop', label: 'Random Crop', icon: Crop, description: 'Random crop (70%-90%)' },
  { value: 'video_noise', label: 'Add Noise', icon: Droplets, description: 'Add visual noise' },
  { value: 'video_blur', label: 'Blur', icon: Wind, description: 'Apply blur effect' },
  { value: 'video_color_jitter', label: 'Color Jitter', icon: Shuffle, description: 'Random color variations' },
  { value: 'video_grayscale', label: 'Grayscale', icon: Filter, description: 'Convert to grayscale' },
]

export default function AugmentationPage() {
  const queryClient = useQueryClient()
  const searchParams = useSearchParams()
  const preselectedProject = searchParams.get('project')
  
  const [projectId, setProjectId] = useState(preselectedProject || '')
  const [showAddRule, setShowAddRule] = useState(false)
  const [newRule, setNewRule] = useState({
    name: '',
    data_type: 'text',
    augmentation_type: '',
    probability: 1.0,
    parameters: {} as Record<string, any>,
  })
  const [runConfig, setRunConfig] = useState({
    max_augmented_per_item: 1,
    only_labeled: true,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: rules, isLoading } = useQuery({
    queryKey: ['augmentation-rules', projectId],
    queryFn: () => datasetApi.listAugmentationRules(projectId),
    enabled: !!projectId,
  })

  const createRuleMutation = useMutation({
    mutationFn: (data: any) => datasetApi.createAugmentationRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-rules'] })
      toast.success('Rule created')
      setShowAddRule(false)
      setNewRule({
        name: '',
        data_type: 'text',
        augmentation_type: '',
        probability: 1.0,
        parameters: {},
      })
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create rule')
    },
  })

  const deleteRuleMutation = useMutation({
    mutationFn: (ruleId: string) => datasetApi.deleteAugmentationRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-rules'] })
      toast.success('Rule deleted')
    },
  })

  const runAugmentationMutation = useMutation({
    mutationFn: () => datasetApi.runAugmentation({
      project_id: projectId,
      max_augmented_per_item: runConfig.max_augmented_per_item,
      only_labeled: runConfig.only_labeled,
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['data'] })
      toast.success(`Created ${data.augmented_count} augmented items`)
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Augmentation failed')
    },
  })

  const getAugmentations = (dataType: string) => {
    switch (dataType) {
      case 'text': return TEXT_AUGMENTATIONS
      case 'image': return IMAGE_AUGMENTATIONS
      case 'audio': return AUDIO_AUGMENTATIONS
      case 'video': return VIDEO_AUGMENTATIONS
      default: return []
    }
  }

  const getDataTypeIcon = (type: string) => {
    switch (type) {
      case 'text': return <FileText className="w-4 h-4" />
      case 'image': return <ImageIcon className="w-4 h-4" />
      case 'audio': return <Music className="w-4 h-4" />
      case 'video': return <Video className="w-4 h-4" />
      default: return <Settings className="w-4 h-4" />
    }
  }
  
  const getDataTypeColor = (type: string) => {
    switch (type) {
      case 'text': return 'text-blue-400 bg-blue-500/20'
      case 'image': return 'text-green-400 bg-green-500/20'
      case 'audio': return 'text-purple-400 bg-purple-500/20'
      case 'video': return 'text-orange-400 bg-orange-500/20'
      default: return 'text-surface-400 bg-surface-700'
    }
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Data Augmentation Guide"
        description="Learn how to expand your dataset with synthetic variations"
        sections={augmentationTutorial}
        storageKey="augmentation"
      />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
          <Wand2 className="w-8 h-8" />
          Data Augmentation
        </h1>
        <p className="text-surface-400">Expand your dataset with automated variations</p>
      </div>

      {/* Project Selector */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          className="px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors min-w-[300px]"
        >
          <option value="">Select a project</option>
          {projects?.map((project: any) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>

        {projectId && (
          <button
            onClick={() => setShowAddRule(true)}
            className="px-4 py-3 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Rule
          </button>
        )}
      </div>

      {!projectId ? (
        <div className="text-center py-20">
          <Wand2 className="w-16 h-16 text-surface-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Select a Project</h3>
          <p className="text-surface-400">Choose a project to configure data augmentation</p>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-surface-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Rules List */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-semibold">Augmentation Rules</h2>
            
            {rules && rules.length > 0 ? (
              <div className="space-y-3">
                {rules.map((rule: any) => (
                  <motion.div
                    key={rule.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 rounded-xl bg-surface-900 border border-surface-800"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${rule.is_active ? getDataTypeColor(rule.data_type) : 'bg-surface-700 text-surface-400'}`}>
                          {getDataTypeIcon(rule.data_type)}
                        </div>
                        <div>
                          <h3 className="font-medium">{rule.name}</h3>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-0.5 rounded ${getDataTypeColor(rule.data_type)}`}>
                              {rule.data_type}
                            </span>
                            <span className="text-sm text-surface-400">
                              {rule.augmentation_type.replace(/_/g, ' ').replace(/^(text|image|audio|video)\s*/, '').trim()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-surface-400">
                          {(rule.probability * 100).toFixed(0)}%
                        </span>
                        <button
                          onClick={() => deleteRuleMutation.mutate(rule.id)}
                          className="p-2 hover:bg-surface-800 rounded-lg text-surface-400 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 rounded-xl bg-surface-900 border border-surface-800">
                <Wand2 className="w-12 h-12 text-surface-600 mx-auto mb-3" />
                <p className="text-surface-400">No augmentation rules defined</p>
                <p className="text-sm text-surface-500 mt-1">Click "Add Rule" to create one</p>
              </div>
            )}
          </div>

          {/* Run Panel */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Run Augmentation</h2>
            
            <div className="p-6 rounded-xl bg-surface-900 border border-surface-800 space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-2">
                  Augmentations per item
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={runConfig.max_augmented_per_item}
                  onChange={(e) => setRunConfig({ ...runConfig, max_augmented_per_item: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div className="flex items-center justify-between">
                <label className="text-sm text-surface-400">Only labeled items</label>
                <button
                  onClick={() => setRunConfig({ ...runConfig, only_labeled: !runConfig.only_labeled })}
                  className={`p-1 rounded ${runConfig.only_labeled ? 'text-brand-400' : 'text-surface-500'}`}
                >
                  {runConfig.only_labeled ? <ToggleRight className="w-8 h-8" /> : <ToggleLeft className="w-8 h-8" />}
                </button>
              </div>
              
              <button
                onClick={() => runAugmentationMutation.mutate()}
                disabled={runAugmentationMutation.isPending || !rules || rules.length === 0}
                className="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium hover:from-green-400 hover:to-emerald-400 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {runAugmentationMutation.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Play className="w-5 h-5" />
                )}
                Run Augmentation
              </button>
              
              <p className="text-xs text-surface-500 text-center">
                This will create augmented copies of your data
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Add Rule Modal */}
      {showAddRule && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface-900 rounded-2xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto"
          >
            <h2 className="text-xl font-semibold mb-4">Add Augmentation Rule</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-surface-400 mb-1">Rule Name</label>
                <input
                  type="text"
                  placeholder="e.g., Random Rotation"
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700"
                />
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-2">Data Type</label>
                <div className="grid grid-cols-4 gap-2">
                  {['text', 'image', 'audio', 'video'].map((type) => (
                    <button
                      key={type}
                      onClick={() => setNewRule({ ...newRule, data_type: type, augmentation_type: '' })}
                      className={`p-3 rounded-lg flex flex-col items-center gap-1 transition-colors ${
                        newRule.data_type === type
                          ? 'bg-brand-500/20 border border-brand-500'
                          : 'bg-surface-800 hover:bg-surface-700 border border-transparent'
                      }`}
                    >
                      <span className={getDataTypeColor(type).split(' ')[0]}>
                        {type === 'text' && <FileText className="w-5 h-5" />}
                        {type === 'image' && <ImageIcon className="w-5 h-5" />}
                        {type === 'audio' && <Music className="w-5 h-5" />}
                        {type === 'video' && <Video className="w-5 h-5" />}
                      </span>
                      <span className="text-xs capitalize">{type}</span>
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-2">Augmentation Type</label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {getAugmentations(newRule.data_type).map((aug) => (
                    <button
                      key={aug.value}
                      onClick={() => setNewRule({ ...newRule, augmentation_type: aug.value })}
                      className={`w-full p-3 rounded-lg text-left flex items-center gap-3 transition-colors ${
                        newRule.augmentation_type === aug.value
                          ? 'bg-brand-500/20 border border-brand-500'
                          : 'bg-surface-800 hover:bg-surface-700'
                      }`}
                    >
                      <aug.icon className="w-5 h-5 text-surface-400" />
                      <div>
                        <p className="font-medium">{aug.label}</p>
                        <p className="text-xs text-surface-500">{aug.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm text-surface-400 mb-1">
                  Probability ({(newRule.probability * 100).toFixed(0)}%)
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={newRule.probability}
                  onChange={(e) => setNewRule({ ...newRule, probability: parseFloat(e.target.value) })}
                  className="w-full"
                />
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAddRule(false)}
                className="px-4 py-2 rounded-lg text-surface-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => createRuleMutation.mutate({
                  project_id: projectId,
                  ...newRule,
                })}
                disabled={createRuleMutation.isPending || !newRule.name || !newRule.augmentation_type}
                className="px-4 py-2 rounded-lg bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {createRuleMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Create Rule
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
