'use client'

import { useState } from 'react'
import { useRouter, Link } from '@/i18n/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { schedulerApi, projectsApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { useTranslations } from 'next-intl'
import {
  ArrowLeft,
  Clock,
  Calendar,
  Repeat,
  Zap,
  Eye,
  Bell,
  Save,
  AlertCircle,
  Check,
} from 'lucide-react'

const scheduleTypes = [
  { id: 'cron', name: 'Cron Schedule', icon: Clock, description: 'Run on a cron expression' },
  { id: 'interval', name: 'Interval', icon: Repeat, description: 'Run every X seconds/minutes/hours' },
  { id: 'once', name: 'One-time', icon: Calendar, description: 'Run once at a specific time' },
  { id: 'on_change', name: 'On Change', icon: Eye, description: 'Run when page content changes' },
  { id: 'conditional', name: 'Conditional', icon: Zap, description: 'Run when a condition is met' },
]

const providers = [
  { id: 'custom', name: 'Custom Scraper', description: 'Scrape any URL with Playwright' },
  { id: 'serpapi', name: 'SerpAPI', description: 'Google search results' },
  { id: 'apify', name: 'Apify', description: 'Pre-built scraping actors' },
  { id: 'browserless', name: 'Browserless', description: 'Headless Chrome scraping' },
  { id: 'twitter', name: 'Twitter/X', description: 'Tweets and media' },
  { id: 'reddit', name: 'Reddit', description: 'Posts and comments' },
  { id: 'youtube', name: 'YouTube', description: 'Videos, transcripts, comments' },
  { id: 'github', name: 'GitHub', description: 'Repos, code, issues' },
  { id: 'newsapi', name: 'NewsAPI', description: 'News articles worldwide' },
  { id: 'google_news', name: 'Google News', description: 'News headlines' },
  { id: 'hackernews', name: 'Hacker News', description: 'Stories and comments' },
  { id: 'arxiv', name: 'arXiv', description: 'Academic papers' },
  { id: 'wikipedia', name: 'Wikipedia', description: 'Encyclopedia articles' },
  { id: 'rss', name: 'RSS Feed', description: 'RSS/Atom feeds' },
  { id: 'sitemap', name: 'Sitemap', description: 'Discover URLs from sitemap' },
  { id: 'webcrawler', name: 'Web Crawler', description: 'Crawl website following links' },
  { id: 'image_scraper', name: 'Image Scraper', description: 'Images from Unsplash, Wikimedia' },
  { id: 'audio_scraper', name: 'Audio Scraper', description: 'Audio from Wikimedia, Archive' },
  { id: 'video_scraper', name: 'Video Scraper', description: 'Videos from Wikimedia, Archive' },
]

export default function NewSchedulePage() {
  const router = useRouter()
  
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    name: '',
    project_id: '',
    provider: 'custom',
    schedule_type: 'cron',
    cron_expression: '0 */6 * * *',
    interval_seconds: 3600,
    run_at: '',
    check_interval_seconds: 3600,
    change_detection_selector: '',
    condition_url: '',
    condition_selector: '',
    condition_value: '',
    timezone: 'UTC',
    max_runs: null as number | null,
    expires_at: '',
    retry_on_failure: true,
    random_delay_seconds: 0,
    on_complete_webhook: '',
    on_error_webhook: '',
    // Scrape config
    urls: '',
    selector: '',
    extract_type: 'text',
    query: '',
    max_results: 100,
  })
  
  // Fetch projects
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list({}),
  })
  
  // Fetch cron presets
  const { data: presets } = useQuery({
    queryKey: ['cron-presets'],
    queryFn: schedulerApi.getCronPresets,
  })
  
  // Parse cron to preview
  const { data: cronPreview, refetch: refetchCronPreview } = useQuery({
    queryKey: ['cron-preview', formData.cron_expression],
    queryFn: () => schedulerApi.parseCron(formData.cron_expression),
    enabled: formData.schedule_type === 'cron' && !!formData.cron_expression,
  })
  
  // Create mutation
  const createSchedule = useMutation({
    mutationFn: schedulerApi.createJob,
    onSuccess: () => {
      router.push('/dashboard/scheduler')
    },
  })
  
  const handleSubmit = () => {
    // Build scrape config based on provider
    let scrapeConfig: any = {}
    
    if (formData.provider === 'custom') {
      scrapeConfig = {
        urls: formData.urls.split('\n').filter(Boolean),
        selector: formData.selector || undefined,
        extract_type: formData.extract_type,
      }
    } else if (formData.provider === 'browserless') {
      scrapeConfig = {
        url: formData.urls.split('\n')[0],
        selector: formData.selector || undefined,
        wait_time: 2000,
      }
    } else if (formData.provider === 'apify') {
      scrapeConfig = {
        actor_id: formData.query,
        input: {},
      }
    } else if (formData.provider === 'twitter') {
      scrapeConfig = {
        query: formData.query,
        max_tweets: formData.max_results,
      }
    } else if (formData.provider === 'reddit') {
      scrapeConfig = {
        subreddit: formData.query,
        limit: formData.max_results,
        sort: 'hot',
      }
    } else if (['youtube', 'github', 'hackernews', 'arxiv', 'wikipedia', 'newsapi', 'google_news'].includes(formData.provider)) {
      scrapeConfig = {
        query: formData.query,
        max_results: formData.max_results,
        type: 'search',
      }
    } else if (formData.provider === 'rss') {
      scrapeConfig = {
        feed_urls: formData.urls.split('\n').filter(Boolean),
        max_items: formData.max_results,
      }
    } else if (formData.provider === 'sitemap') {
      scrapeConfig = {
        base_url: formData.urls.split('\n')[0],
        max_urls: formData.max_results,
      }
    } else if (formData.provider === 'webcrawler') {
      scrapeConfig = {
        start_url: formData.urls.split('\n')[0],
        max_pages: formData.max_results,
        max_depth: 2,
      }
    } else {
      scrapeConfig = {
        query: formData.query,
      }
    }
    
    // Build schedule config
    const scheduleConfig: any = {
      schedule_type: formData.schedule_type,
      timezone: formData.timezone,
      retry_on_failure: formData.retry_on_failure,
      random_delay_seconds: formData.random_delay_seconds,
    }
    
    if (formData.schedule_type === 'cron') {
      scheduleConfig.cron_expression = formData.cron_expression
    } else if (formData.schedule_type === 'interval') {
      scheduleConfig.interval_seconds = formData.interval_seconds
    } else if (formData.schedule_type === 'once') {
      scheduleConfig.run_at = formData.run_at
    } else if (formData.schedule_type === 'on_change') {
      scheduleConfig.check_interval_seconds = formData.check_interval_seconds
      scheduleConfig.change_detection_selector = formData.change_detection_selector
    } else if (formData.schedule_type === 'conditional') {
      scheduleConfig.condition_url = formData.condition_url
      scheduleConfig.condition_selector = formData.condition_selector
      scheduleConfig.condition_value = formData.condition_value
    }
    
    if (formData.max_runs) {
      scheduleConfig.max_runs = formData.max_runs
    }
    if (formData.expires_at) {
      scheduleConfig.expires_at = formData.expires_at
    }
    
    createSchedule.mutate({
      name: formData.name,
      project_id: formData.project_id,
      schedule: scheduleConfig,
      scrape_config: {
        provider: formData.provider,
        ...scrapeConfig,
      },
      on_complete_webhook: formData.on_complete_webhook || undefined,
      on_error_webhook: formData.on_error_webhook || undefined,
    })
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link
          href="/dashboard/scheduler"
          className="p-2 rounded-xl hover:bg-surface-800 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Create Schedule</h1>
          <p className="text-surface-400">Set up automated scraping</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-center gap-4 mb-8">
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                step >= s
                  ? 'bg-brand-500 text-white'
                  : 'bg-surface-800 text-surface-400'
              }`}
            >
              {step > s ? <Check className="w-5 h-5" /> : s}
            </div>
            {s < 4 && (
              <div className={`w-16 h-1 ${step > s ? 'bg-brand-500' : 'bg-surface-800'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <motion.div
        key={step}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="rounded-2xl glass p-6"
      >
        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
            
            <div>
              <label className="block text-sm font-medium mb-2">Schedule Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                placeholder="My Daily Scrape"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Project</label>
              <select
                value={formData.project_id}
                onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
              >
                <option value="">Select a project</option>
                {projects?.map((p: any) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Provider</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {providers.map((provider) => (
                  <button
                    key={provider.id}
                    onClick={() => setFormData({ ...formData, provider: provider.id })}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      formData.provider === provider.id
                        ? 'border-brand-500 bg-brand-500/10'
                        : 'border-surface-700 hover:border-surface-600'
                    }`}
                  >
                    <div className="font-medium">{provider.name}</div>
                    <div className="text-xs text-surface-400">{provider.description}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Schedule Type */}
        {step === 2 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Schedule Type</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {scheduleTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setFormData({ ...formData, schedule_type: type.id })}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    formData.schedule_type === type.id
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-surface-700 hover:border-surface-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <type.icon className="w-5 h-5" />
                    <div>
                      <div className="font-medium">{type.name}</div>
                      <div className="text-xs text-surface-400">{type.description}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            
            {/* Schedule-specific options */}
            {formData.schedule_type === 'cron' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Cron Expression</label>
                  <input
                    type="text"
                    value={formData.cron_expression}
                    onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none font-mono"
                    placeholder="0 */6 * * *"
                  />
                </div>
                
                {/* Presets */}
                <div className="flex flex-wrap gap-2">
                  {presets?.presets?.slice(0, 8).map((preset: any) => (
                    <button
                      key={preset.key}
                      onClick={() => setFormData({ ...formData, cron_expression: preset.expression })}
                      className="px-3 py-1 rounded-lg bg-surface-800 hover:bg-surface-700 text-sm"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>
                
                {/* Preview */}
                {cronPreview && (
                  <div className="p-4 rounded-xl bg-surface-800/50">
                    <div className="text-sm font-medium mb-2">Next 5 runs:</div>
                    <div className="text-sm text-surface-400 space-y-1">
                      {cronPreview.next_5_runs?.map((run: string, i: number) => (
                        <div key={i}>{new Date(run).toLocaleString()}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {formData.schedule_type === 'interval' && (
              <div>
                <label className="block text-sm font-medium mb-2">Interval (seconds)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="number"
                    value={formData.interval_seconds}
                    onChange={(e) => setFormData({ ...formData, interval_seconds: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={60}
                  />
                  <div className="text-surface-400 whitespace-nowrap">
                    = {Math.floor(formData.interval_seconds / 3600)}h {Math.floor((formData.interval_seconds % 3600) / 60)}m
                  </div>
                </div>
              </div>
            )}
            
            {formData.schedule_type === 'once' && (
              <div>
                <label className="block text-sm font-medium mb-2">Run At</label>
                <input
                  type="datetime-local"
                  value={formData.run_at}
                  onChange={(e) => setFormData({ ...formData, run_at: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                />
              </div>
            )}
            
            {formData.schedule_type === 'on_change' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Check Interval (seconds)</label>
                  <input
                    type="number"
                    value={formData.check_interval_seconds}
                    onChange={(e) => setFormData({ ...formData, check_interval_seconds: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={60}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Element Selector (optional)</label>
                  <input
                    type="text"
                    value={formData.change_detection_selector}
                    onChange={(e) => setFormData({ ...formData, change_detection_selector: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder=".price, #content"
                  />
                  <p className="text-xs text-surface-400 mt-1">Monitor specific element for changes</p>
                </div>
              </div>
            )}
            
            {formData.schedule_type === 'conditional' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">URL to Check</label>
                  <input
                    type="url"
                    value={formData.condition_url}
                    onChange={(e) => setFormData({ ...formData, condition_url: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="https://example.com/status"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Element Selector</label>
                  <input
                    type="text"
                    value={formData.condition_selector}
                    onChange={(e) => setFormData({ ...formData, condition_selector: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder=".status, #indicator"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Expected Value (optional)</label>
                  <input
                    type="text"
                    value={formData.condition_value}
                    onChange={(e) => setFormData({ ...formData, condition_value: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="available"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Scrape Config */}
        {step === 3 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Scrape Configuration</h2>
            
            {formData.provider === 'custom' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">URLs (one per line)</label>
                  <textarea
                    value={formData.urls}
                    onChange={(e) => setFormData({ ...formData, urls: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none h-32"
                    placeholder="https://example.com/page1&#10;https://example.com/page2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">CSS Selector (optional)</label>
                  <input
                    type="text"
                    value={formData.selector}
                    onChange={(e) => setFormData({ ...formData, selector: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="article, .content, #main"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Extract Type</label>
                  <select
                    value={formData.extract_type}
                    onChange={(e) => setFormData({ ...formData, extract_type: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                  >
                    <option value="text">Text</option>
                    <option value="html">HTML</option>
                    <option value="images">Images</option>
                    <option value="links">Links</option>
                  </select>
                </div>
              </>
            )}

            {formData.provider === 'browserless' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">URL</label>
                  <input
                    type="url"
                    value={formData.urls}
                    onChange={(e) => setFormData({ ...formData, urls: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="https://example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">CSS Selector (optional)</label>
                  <input
                    type="text"
                    value={formData.selector}
                    onChange={(e) => setFormData({ ...formData, selector: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="body, article"
                  />
                </div>
              </>
            )}

            {formData.provider === 'apify' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Actor ID</label>
                  <input
                    type="text"
                    value={formData.query}
                    onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="apify/web-scraper"
                  />
                </div>
                <p className="text-xs text-surface-400">
                  Enter the Apify actor ID. Configure actor inputs in the job settings.
                </p>
              </>
            )}

            {formData.provider === 'twitter' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Search Query or Hashtag</label>
                  <input
                    type="text"
                    value={formData.query}
                    onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="#AI OR #MachineLearning"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Tweets</label>
                  <input
                    type="number"
                    value={formData.max_results}
                    onChange={(e) => setFormData({ ...formData, max_results: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={1}
                    max={500}
                  />
                </div>
              </>
            )}

            {formData.provider === 'reddit' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Subreddit</label>
                  <input
                    type="text"
                    value={formData.query}
                    onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="MachineLearning"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Posts</label>
                  <input
                    type="number"
                    value={formData.max_results}
                    onChange={(e) => setFormData({ ...formData, max_results: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={1}
                    max={500}
                  />
                </div>
              </>
            )}
            
            {['youtube', 'github', 'hackernews', 'arxiv', 'wikipedia', 'serpapi', 'newsapi', 'google_news'].includes(formData.provider) && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Search Query</label>
                  <input
                    type="text"
                    value={formData.query}
                    onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="machine learning, AI, etc."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Results</label>
                  <input
                    type="number"
                    value={formData.max_results}
                    onChange={(e) => setFormData({ ...formData, max_results: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={1}
                    max={1000}
                  />
                </div>
              </>
            )}
            
            {formData.provider === 'rss' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">Feed URLs (one per line)</label>
                  <textarea
                    value={formData.urls}
                    onChange={(e) => setFormData({ ...formData, urls: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none h-32"
                    placeholder="https://example.com/feed.xml&#10;https://example.com/rss"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Items per Feed</label>
                  <input
                    type="number"
                    value={formData.max_results}
                    onChange={(e) => setFormData({ ...formData, max_results: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={1}
                    max={500}
                  />
                </div>
              </>
            )}
            
            {['sitemap', 'webcrawler'].includes(formData.provider) && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {formData.provider === 'sitemap' ? 'Website URL or Sitemap URL' : 'Start URL'}
                  </label>
                  <input
                    type="url"
                    value={formData.urls}
                    onChange={(e) => setFormData({ ...formData, urls: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="https://example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Max {formData.provider === 'sitemap' ? 'URLs' : 'Pages'}
                  </label>
                  <input
                    type="number"
                    value={formData.max_results}
                    onChange={(e) => setFormData({ ...formData, max_results: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    min={1}
                    max={10000}
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Step 4: Advanced Options */}
        {step === 4 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold mb-4">Advanced Options</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium mb-2">Timezone</label>
                <select
                  value={formData.timezone}
                  onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="Europe/London">London</option>
                  <option value="Europe/Paris">Paris</option>
                  <option value="Asia/Tokyo">Tokyo</option>
                  <option value="Asia/Tehran">Tehran</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Max Runs (optional)</label>
                <input
                  type="number"
                  value={formData.max_runs || ''}
                  onChange={(e) => setFormData({ ...formData, max_runs: e.target.value ? parseInt(e.target.value) : null })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                  placeholder="Unlimited"
                  min={1}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Expires At (optional)</label>
                <input
                  type="datetime-local"
                  value={formData.expires_at}
                  onChange={(e) => setFormData({ ...formData, expires_at: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2">Random Delay (seconds)</label>
                <input
                  type="number"
                  value={formData.random_delay_seconds}
                  onChange={(e) => setFormData({ ...formData, random_delay_seconds: parseInt(e.target.value) })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                  min={0}
                />
                <p className="text-xs text-surface-400 mt-1">Add random delay to avoid detection</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="retry"
                checked={formData.retry_on_failure}
                onChange={(e) => setFormData({ ...formData, retry_on_failure: e.target.checked })}
                className="w-5 h-5 rounded bg-surface-800 border-surface-700"
              />
              <label htmlFor="retry" className="text-sm">Retry on failure</label>
            </div>
            
            <div className="border-t border-surface-800 pt-6">
              <h3 className="text-lg font-medium mb-4">Webhooks (optional)</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">On Complete Webhook URL</label>
                  <input
                    type="url"
                    value={formData.on_complete_webhook}
                    onChange={(e) => setFormData({ ...formData, on_complete_webhook: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="https://your-server.com/webhook"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">On Error Webhook URL</label>
                  <input
                    type="url"
                    value={formData.on_error_webhook}
                    onChange={(e) => setFormData({ ...formData, on_error_webhook: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
                    placeholder="https://your-server.com/webhook"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-surface-800">
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="px-6 py-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            >
              Back
            </button>
          ) : (
            <div />
          )}
          
          {step < 4 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={
                (step === 1 && (!formData.name || !formData.project_id)) ||
                (step === 2 && !formData.schedule_type)
              }
              className="px-6 py-3 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={createSchedule.isPending}
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50"
            >
              <Save className="w-5 h-5" />
              {createSchedule.isPending ? 'Creating...' : 'Create Schedule'}
            </button>
          )}
        </div>
      </motion.div>
    </div>
  )
}

