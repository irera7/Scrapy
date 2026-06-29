'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useRouter, Link } from '@/i18n/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, projectsApi, providersApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { ArrowLeft, Loader2, Info, AlertCircle } from 'lucide-react'
import { useTranslations } from 'next-intl'
import toast from 'react-hot-toast'

export default function NewJobPage() {
  const t = useTranslations()
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()

  const preselectedProject = searchParams.get('project')

  const [projectId, setProjectId] = useState(preselectedProject || '')
  const [name, setName] = useState('')
  const [provider, setProvider] = useState('serpapi')
  const [config, setConfig] = useState<Record<string, any>>({})
  const [schedule, setSchedule] = useState('')

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: () => providersApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: jobsApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job created!')
      router.push(`/dashboard/jobs/${data.id}`)
    },
    onError: () => {
      toast.error('Failed to create job')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      project_id: projectId,
      name,
      provider,
      config,
      schedule: schedule || undefined,
    })
  }

  const renderConfigFields = () => {
    switch (provider) {
      case 'serpapi':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="machine learning tutorials"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Search Engine</label>
                <select
                  value={config.engine || 'google'}
                  onChange={(e) => setConfig({ ...config, engine: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="google">Google</option>
                  <option value="bing">Bing</option>
                  <option value="youtube">YouTube</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Search Type</label>
                <select
                  value={config.search_type || ''}
                  onChange={(e) => setConfig({ ...config, search_type: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="">Web Results</option>
                  <option value="isch">Images</option>
                  <option value="nws">News</option>
                  <option value="vid">Videos</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Number of Results</label>
              <input
                type="number"
                value={config.num_results || 10}
                onChange={(e) => setConfig({ ...config, num_results: parseInt(e.target.value) })}
                min={1}
                max={100}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
          </>
        )

      case 'custom':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">URLs (one per line) *</label>
              <textarea
                value={(config.urls || []).join('\n')}
                onChange={(e) => setConfig({
                  ...config,
                  urls: e.target.value.split('\n').filter(u => u.trim())
                })}
                rows={5}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder="https://example.com/page1&#10;https://example.com/page2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">CSS Selector (optional)</label>
              <input
                type="text"
                value={config.selector || ''}
                onChange={(e) => setConfig({ ...config, selector: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder="article.content, .main-text"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Extract Type</label>
              <select
                value={config.extract_type || 'text'}
                onChange={(e) => setConfig({ ...config, extract_type: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              >
                <option value="text">Text</option>
                <option value="html">HTML</option>
                <option value="images">Images</option>
                <option value="links">Links</option>
              </select>
            </div>
          </>
        )

      case 'browserless':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">URL *</label>
              <input
                type="url"
                value={config.url || ''}
                onChange={(e) => setConfig({ ...config, url: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="https://example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">CSS Selector</label>
              <input
                type="text"
                value={config.selector || ''}
                onChange={(e) => setConfig({ ...config, selector: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder="body, article"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Wait For (ms)</label>
                <input
                  type="number"
                  value={config.wait_time || 2000}
                  onChange={(e) => setConfig({ ...config, wait_time: parseInt(e.target.value) })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Screenshot</label>
                <select
                  value={config.screenshot ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, screenshot: e.target.value === 'true' })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </select>
              </div>
            </div>
          </>
        )

      case 'twitter':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="#AI OR #MachineLearning"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Tweets</label>
              <input
                type="number"
                value={config.max_tweets || 100}
                onChange={(e) => setConfig({ ...config, max_tweets: parseInt(e.target.value) })}
                min={1}
                max={500}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
          </>
        )

      case 'reddit':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Subreddit *</label>
              <input
                type="text"
                value={config.subreddit || ''}
                onChange={(e) => setConfig({ ...config, subreddit: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="MachineLearning"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Sort By</label>
                <select
                  value={config.sort || 'hot'}
                  onChange={(e) => setConfig({ ...config, sort: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="hot">Hot</option>
                  <option value="new">New</option>
                  <option value="top">Top</option>
                  <option value="rising">Rising</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Limit</label>
                <input
                  type="number"
                  value={config.limit || 100}
                  onChange={(e) => setConfig({ ...config, limit: parseInt(e.target.value) })}
                  min={1}
                  max={500}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
          </>
        )

      case 'apify':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Actor ID *</label>
              <input
                type="text"
                value={config.actor_id || ''}
                onChange={(e) => setConfig({ ...config, actor_id: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="apify/web-scraper"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Actor Input (JSON)</label>
              <textarea
                value={JSON.stringify(config.input || {}, null, 2)}
                onChange={(e) => {
                  try {
                    setConfig({ ...config, input: JSON.parse(e.target.value) })
                  } catch {}
                }}
                rows={5}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder='{"startUrls": [{"url": "https://example.com"}]}'
              />
            </div>
          </>
        )

      case 'youtube':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query or Channel URL *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="machine learning tutorial OR https://youtube.com/@channel"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Search Type</label>
                <select
                  value={config.search_type || 'video'}
                  onChange={(e) => setConfig({ ...config, search_type: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="video">Videos</option>
                  <option value="channel">Channels</option>
                  <option value="playlist">Playlists</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Results</label>
                <input
                  type="number"
                  value={config.max_results || 50}
                  onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                  min={1}
                  max={500}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="include_comments"
                checked={config.include_comments || false}
                onChange={(e) => setConfig({ ...config, include_comments: e.target.checked })}
                className="rounded border-surface-700 bg-surface-800"
              />
              <label htmlFor="include_comments" className="text-sm">Include video comments</label>
            </div>
          </>
        )

      case 'github':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="machine learning language:python stars:>100"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Search Type</label>
                <select
                  value={config.search_type || 'repositories'}
                  onChange={(e) => setConfig({ ...config, search_type: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="repositories">Repositories</option>
                  <option value="code">Code</option>
                  <option value="issues">Issues</option>
                  <option value="users">Users</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Results</label>
                <input
                  type="number"
                  value={config.max_results || 100}
                  onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                  min={1}
                  max={1000}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="include_readme"
                checked={config.include_readme || false}
                onChange={(e) => setConfig({ ...config, include_readme: e.target.checked })}
                className="rounded border-surface-700 bg-surface-800"
              />
              <label htmlFor="include_readme" className="text-sm">Include README content</label>
            </div>
          </>
        )

      case 'newsapi':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="artificial intelligence"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Category</label>
                <select
                  value={config.category || ''}
                  onChange={(e) => setConfig({ ...config, category: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="">All Categories</option>
                  <option value="technology">Technology</option>
                  <option value="science">Science</option>
                  <option value="business">Business</option>
                  <option value="health">Health</option>
                  <option value="entertainment">Entertainment</option>
                  <option value="sports">Sports</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Language</label>
                <select
                  value={config.language || 'en'}
                  onChange={(e) => setConfig({ ...config, language: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="zh">Chinese</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Articles</label>
              <input
                type="number"
                value={config.page_size || 100}
                onChange={(e) => setConfig({ ...config, page_size: parseInt(e.target.value) })}
                min={1}
                max={100}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
          </>
        )

      case 'google_news':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="machine learning"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Country</label>
                <select
                  value={config.country || 'US'}
                  onChange={(e) => setConfig({ ...config, country: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="US">United States</option>
                  <option value="GB">United Kingdom</option>
                  <option value="CA">Canada</option>
                  <option value="AU">Australia</option>
                  <option value="IN">India</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Results</label>
                <input
                  type="number"
                  value={config.max_results || 100}
                  onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                  min={1}
                  max={500}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
          </>
        )

      case 'hackernews':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Content Type *</label>
              <select
                value={config.content_type || 'topstories'}
                onChange={(e) => setConfig({ ...config, content_type: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              >
                <option value="topstories">Top Stories</option>
                <option value="newstories">New Stories</option>
                <option value="beststories">Best Stories</option>
                <option value="askstories">Ask HN</option>
                <option value="showstories">Show HN</option>
                <option value="jobstories">Jobs</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Max Stories</label>
                <input
                  type="number"
                  value={config.limit || 100}
                  onChange={(e) => setConfig({ ...config, limit: parseInt(e.target.value) })}
                  min={1}
                  max={500}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Min Score</label>
                <input
                  type="number"
                  value={config.min_score || 0}
                  onChange={(e) => setConfig({ ...config, min_score: parseInt(e.target.value) })}
                  min={0}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="include_comments"
                checked={config.include_comments || false}
                onChange={(e) => setConfig({ ...config, include_comments: e.target.checked })}
                className="rounded border-surface-700 bg-surface-800"
              />
              <label htmlFor="include_comments" className="text-sm">Include comments</label>
            </div>
          </>
        )

      case 'arxiv':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="transformer neural network"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Category</label>
                <select
                  value={config.category || ''}
                  onChange={(e) => setConfig({ ...config, category: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="">All Categories</option>
                  <option value="cs.AI">Computer Science - AI</option>
                  <option value="cs.LG">Computer Science - ML</option>
                  <option value="cs.CL">Computer Science - CL</option>
                  <option value="cs.CV">Computer Science - CV</option>
                  <option value="stat.ML">Statistics - ML</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Sort By</label>
                <select
                  value={config.sort_by || 'relevance'}
                  onChange={(e) => setConfig({ ...config, sort_by: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="relevance">Relevance</option>
                  <option value="lastUpdatedDate">Last Updated</option>
                  <option value="submittedDate">Submitted Date</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Results</label>
              <input
                type="number"
                value={config.max_results || 100}
                onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                min={1}
                max={1000}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
          </>
        )

      case 'wikipedia':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query or Article Title *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="Artificial intelligence"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Language</label>
                <select
                  value={config.language || 'en'}
                  onChange={(e) => setConfig({ ...config, language: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                >
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="ja">Japanese</option>
                  <option value="zh">Chinese</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Articles</label>
                <input
                  type="number"
                  value={config.limit || 10}
                  onChange={(e) => setConfig({ ...config, limit: parseInt(e.target.value) })}
                  min={1}
                  max={100}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="include_images"
                checked={config.include_images || false}
                onChange={(e) => setConfig({ ...config, include_images: e.target.checked })}
                className="rounded border-surface-700 bg-surface-800"
              />
              <label htmlFor="include_images" className="text-sm">Include images</label>
            </div>
          </>
        )

      case 'sitemap':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Sitemap URL *</label>
              <input
                type="url"
                value={config.sitemap_url || ''}
                onChange={(e) => setConfig({ ...config, sitemap_url: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="https://example.com/sitemap.xml"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">URL Filter (regex)</label>
                <input
                  type="text"
                  value={config.url_filter || ''}
                  onChange={(e) => setConfig({ ...config, url_filter: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                  placeholder="/blog/.*"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max URLs</label>
                <input
                  type="number"
                  value={config.max_urls || 100}
                  onChange={(e) => setConfig({ ...config, max_urls: parseInt(e.target.value) })}
                  min={1}
                  max={10000}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">CSS Selector (optional)</label>
              <input
                type="text"
                value={config.selector || ''}
                onChange={(e) => setConfig({ ...config, selector: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder="article, .main-content"
              />
            </div>
          </>
        )

      case 'rss':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">RSS Feed URLs (one per line) *</label>
              <textarea
                value={(config.feed_urls || []).join('\n')}
                onChange={(e) => setConfig({
                  ...config,
                  feed_urls: e.target.value.split('\n').filter(u => u.trim())
                })}
                rows={4}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder="https://example.com/feed.xml&#10;https://blog.example.com/rss"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Max Items per Feed</label>
                <input
                  type="number"
                  value={config.max_items || 50}
                  onChange={(e) => setConfig({ ...config, max_items: parseInt(e.target.value) })}
                  min={1}
                  max={500}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
              <div className="flex items-center gap-2 pt-8">
                <input
                  type="checkbox"
                  id="fetch_full_content"
                  checked={config.fetch_full_content || false}
                  onChange={(e) => setConfig({ ...config, fetch_full_content: e.target.checked })}
                  className="rounded border-surface-700 bg-surface-800"
                />
                <label htmlFor="fetch_full_content" className="text-sm">Fetch full article content</label>
              </div>
            </div>
          </>
        )

      case 'webcrawler':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Start URL *</label>
              <input
                type="url"
                value={config.start_url || ''}
                onChange={(e) => setConfig({ ...config, start_url: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="https://example.com"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Max Depth</label>
                <input
                  type="number"
                  value={config.max_depth || 2}
                  onChange={(e) => setConfig({ ...config, max_depth: parseInt(e.target.value) })}
                  min={1}
                  max={10}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Pages</label>
                <input
                  type="number"
                  value={config.max_pages || 100}
                  onChange={(e) => setConfig({ ...config, max_pages: parseInt(e.target.value) })}
                  min={1}
                  max={10000}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Delay (ms)</label>
                <input
                  type="number"
                  value={config.delay || 1000}
                  onChange={(e) => setConfig({ ...config, delay: parseInt(e.target.value) })}
                  min={0}
                  max={10000}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">URL Pattern (regex, optional)</label>
              <input
                type="text"
                value={config.url_pattern || ''}
                onChange={(e) => setConfig({ ...config, url_pattern: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                placeholder=".*\\/blog\\/.*"
              />
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="same_domain"
                  checked={config.same_domain !== false}
                  onChange={(e) => setConfig({ ...config, same_domain: e.target.checked })}
                  className="rounded border-surface-700 bg-surface-800"
                />
                <label htmlFor="same_domain" className="text-sm">Same domain only</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="respect_robots"
                  checked={config.respect_robots !== false}
                  onChange={(e) => setConfig({ ...config, respect_robots: e.target.checked })}
                  className="rounded border-surface-700 bg-surface-800"
                />
                <label htmlFor="respect_robots" className="text-sm">Respect robots.txt</label>
              </div>
            </div>
          </>
        )

      case 'image_scraper':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Source *</label>
              <select
                value={config.source || 'unsplash'}
                onChange={(e) => setConfig({ ...config, source: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              >
                <option value="unsplash">Unsplash (Free)</option>
                <option value="wikimedia">Wikimedia Commons (Free)</option>
                <option value="pexels">Pexels (API Key Required)</option>
                <option value="urls">Custom URLs</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                {config.source === 'urls' ? 'URLs (one per line) *' : 'Search Query *'}
              </label>
              {config.source === 'urls' ? (
                <textarea
                  value={(config.urls || []).join('\n')}
                  onChange={(e) => setConfig({
                    ...config,
                    urls: e.target.value.split('\n').filter(u => u.trim())
                  })}
                  rows={4}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono text-sm"
                  placeholder="https://example.com/page1&#10;https://example.com/page2"
                />
              ) : (
                <input
                  type="text"
                  value={config.query || ''}
                  onChange={(e) => setConfig({ ...config, query: e.target.value })}
                  required
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                  placeholder="nature, technology, animals..."
                />
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Max Results</label>
                <input
                  type="number"
                  value={config.max_results || 50}
                  onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                  min={1}
                  max={500}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                />
              </div>
              <div className="flex items-center gap-2 pt-8">
                <input
                  type="checkbox"
                  id="download_images"
                  checked={config.download_media || config.download_images || false}
                  onChange={(e) => setConfig({ ...config, download_media: e.target.checked, download_images: e.target.checked })}
                  className="rounded border-surface-700 bg-surface-800"
                />
                <label htmlFor="download_images" className="text-sm">Download images to storage</label>
              </div>
            </div>
          </>
        )

      case 'audio_scraper':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Source *</label>
              <select
                value={config.source || 'wikimedia'}
                onChange={(e) => setConfig({ ...config, source: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              >
                <option value="wikimedia">Wikimedia Commons (Free)</option>
                <option value="archive">Internet Archive (Free)</option>
                <option value="freesound">Freesound (API Key Required)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="music, sound effects, nature sounds..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Results</label>
              <input
                type="number"
                value={config.max_results || 50}
                onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                min={1}
                max={500}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <div className="flex items-start gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-yellow-400">Media Download Settings</h4>
                  <p className="text-sm text-yellow-300/80 mt-1">
                    Enable this to download actual audio files to storage.
                    Without this, only metadata and source URLs are saved.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <input
                  type="checkbox"
                  id="download_media_audio"
                  checked={config.download_media || false}
                  onChange={(e) => setConfig({ ...config, download_media: e.target.checked })}
                  className="rounded border-surface-700 bg-surface-800"
                />
                <label htmlFor="download_media_audio" className="text-sm font-medium">
                  Download audio files to storage (enables preview/playback in Data Browser)
                </label>
              </div>
            </div>
          </>
        )

      case 'video_scraper':
        return (
          <>
            <div>
              <label className="block text-sm font-medium mb-2">Source *</label>
              <select
                value={config.source || 'wikimedia'}
                onChange={(e) => setConfig({ ...config, source: e.target.value })}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              >
                <option value="wikimedia">Wikimedia Commons (Free)</option>
                <option value="archive">Internet Archive (Free)</option>
                <option value="vimeo">Vimeo (API Key Required)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Search Query *</label>
              <input
                type="text"
                value={config.query || ''}
                onChange={(e) => setConfig({ ...config, query: e.target.value })}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
                placeholder="documentary, nature, tutorial..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Results</label>
              <input
                type="number"
                value={config.max_results || 50}
                onChange={(e) => setConfig({ ...config, max_results: parseInt(e.target.value) })}
                min={1}
                max={500}
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              />
            </div>
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <div className="flex items-start gap-2 mb-3">
                <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-yellow-400">Media Download Settings</h4>
                  <p className="text-sm text-yellow-300/80 mt-1">
                    Enable this to download actual video files to storage.
                    Without this, only metadata and source URLs are saved.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <input
                  type="checkbox"
                  id="download_media_video"
                  checked={config.download_media || false}
                  onChange={(e) => setConfig({ ...config, download_media: e.target.checked })}
                  className="rounded border-surface-700 bg-surface-800"
                />
                <label htmlFor="download_media_video" className="text-sm font-medium">
                  Download video files to storage (enables preview/playback in Data Browser)
                </label>
              </div>
            </div>
          </>
        )

      default:
        return (
          <div className="text-center py-8 text-surface-400">
            <Info className="w-8 h-8 mx-auto mb-2" />
            <p>Select a provider to configure</p>
          </div>
        )
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <Link
        href="/dashboard/jobs"
        className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Jobs
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold mb-2">Create Scraping Job</h1>
        <p className="text-surface-400 mb-8">Configure a new data collection job</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Project Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Project *</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
            >
              <option value="">Select a project</option>
              {projects?.map((project: any) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          {/* Job Name */}
          <div>
            <label className="block text-sm font-medium mb-2">Job Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              placeholder="Daily news scrape"
            />
          </div>

          {/* Provider Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Provider *</label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {providers?.map((p: any) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    setProvider(p.id)
                    setConfig({})
                  }}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    provider === p.id
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-surface-700 bg-surface-800 hover:border-surface-600'
                  }`}
                >
                  <div className="font-medium">{p.name}</div>
                  <div className="text-xs text-surface-400 mt-1 line-clamp-1">{p.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Provider-specific config */}
          <div className="space-y-4 p-4 rounded-xl bg-surface-800/50 border border-surface-700">
            <h3 className="font-medium">Configuration</h3>
            {renderConfigFields()}
          </div>

          {/* Schedule */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Schedule (optional)
              <span className="text-surface-400 font-normal ml-2">cron expression</span>
            </label>
            <input
              type="text"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono"
              placeholder="0 */6 * * * (every 6 hours)"
            />
            <p className="text-xs text-surface-500 mt-1">
              Leave empty for manual runs only
            </p>
          </div>

          {/* Submit */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={createMutation.isPending || !projectId || !name}
              className="flex-1 py-3 px-4 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Job'
              )}
            </button>
            <Link
              href="/dashboard/jobs"
              className="px-6 py-3 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
            >
              Cancel
            </Link>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
