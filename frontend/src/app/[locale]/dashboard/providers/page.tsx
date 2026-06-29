'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { providersApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { useTranslations } from 'next-intl'
import {
  Key,
  Plus,
  Trash2,
  Check,
  Loader2,
  ExternalLink,
  Eye,
  EyeOff,
  TestTube,
  Shield,
  Globe,
  Code,
  MessageCircle,
  Search as SearchIcon,
  Chrome,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const providersTutorial: TutorialSection[] = [
  {
    title: 'What are API Providers?',
    content: 'Providers are external services that supply data for scraping. Some providers require API keys for authentication, while others work directly with public data.',
    tips: [
      'Configure required API keys before creating jobs',
      'Each provider has different rate limits and capabilities',
      'Test your API keys after adding them',
    ],
  },
  {
    title: 'Adding an API Key',
    content: 'Click "Add API Key" to configure a new provider. You\'ll need to obtain the API key from the provider\'s website first.',
    steps: [
      { title: 'Select Provider', description: 'Choose which service you want to configure' },
      { title: 'Get API Key', description: 'Click the link to visit the provider\'s website' },
      { title: 'Enter Key', description: 'Paste your API key into the input field' },
      { title: 'Save & Test', description: 'Save the key and test it works correctly' },
    ],
    warning: 'Keep your API keys secure. Never share them publicly.',
  },
  {
    title: 'Available Providers',
    content: 'Here are the main data providers supported by the platform:',
    steps: [
      { title: 'SerpAPI', description: 'Google, Bing, YouTube search results - requires paid API key' },
      { title: 'Apify', description: 'Pre-built scrapers for many websites - requires API key' },
      { title: 'Twitter/X', description: 'Tweets and social media data - requires bearer token' },
      { title: 'Reddit', description: 'Posts and comments - requires client ID and secret' },
      { title: 'Custom', description: 'Build your own scrapers with Playwright - no key needed' },
    ],
    tips: [
      'SerpAPI offers 100 free searches/month for testing',
      'Twitter API has different tiers with varying limits',
      'Custom scrapers work without any API key',
    ],
  },
  {
    title: 'Managing Keys',
    content: 'You can test, view, and delete your API keys from this page.',
    steps: [
      { title: 'Test Button', description: 'Verify the API key is valid and working' },
      { title: 'Eye Icon', description: 'Show/hide the masked key value' },
      { title: 'Trash Button', description: 'Delete the API key permanently' },
    ],
    tips: [
      'Test keys periodically to ensure they haven\'t expired',
      'Update keys before they expire to avoid job failures',
    ],
  },
]

const providerIcons: Record<string, any> = {
  serpapi: SearchIcon,
  apify: Globe,
  browserless: Chrome,
  custom: Code,
  twitter: MessageCircle,
  reddit: MessageCircle,
  youtube: Globe,
  github: Code,
  newsapi: Globe,
  google_news: Globe,
  hackernews: Globe,
  arxiv: Globe,
  wikipedia: Globe,
  sitemap: Globe,
  rss: Globe,
  webcrawler: Globe,
  image_scraper: Globe,
  audio_scraper: Globe,
  video_scraper: Globe,
}

export default function ProvidersPage() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [showKey, setShowKey] = useState<string | null>(null)

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: () => providersApi.list(),
  })

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => providersApi.listApiKeys(),
  })

  const saveMutation = useMutation({
    mutationFn: providersApi.saveApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setShowAddForm(false)
      setSelectedProvider('')
      setApiKeyInput('')
      toast.success('API key saved')
    },
    onError: () => {
      toast.error('Failed to save API key')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: providersApi.deleteApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API key deleted')
    },
  })

  const testMutation = useMutation({
    mutationFn: providersApi.testApiKey,
    onSuccess: () => {
      toast.success('API key is valid!')
    },
    onError: () => {
      toast.error('API key test failed')
    },
  })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProvider || !apiKeyInput) return
    
    saveMutation.mutate({
      provider: selectedProvider,
      api_key: apiKeyInput,
    })
  }

  const getProviderInfo = (id: string) => {
    return providers?.find((p: any) => p.id === id)
  }

  const getProviderIcon = (id: string) => {
    const Icon = providerIcons[id] || Key
    return Icon
  }

  const providersWithoutKeys = providers?.filter(
    (p: any) => p.requires_api_key && !apiKeys?.some((k: any) => k.provider === p.id)
  )

  const configuredCount = apiKeys?.length || 0
  const requiredCount = providers?.filter((p: any) => p.requires_api_key).length || 0

  return (
    <div className="p-8 max-w-4xl">
      {/* Tutorial */}
      <TutorialPanel
        title="API Providers Guide"
        description="Learn how to configure API keys for data providers"
        sections={providersTutorial}
        storageKey="providers"
      />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">API Keys</h1>
        <p className="text-surface-400">Manage your API keys for data providers</p>
      </div>

      {/* Stats */}
      <div className="flex gap-4 mb-8">
        <div className="px-4 py-2 rounded-xl bg-surface-800/50 border border-surface-700">
          <span className="text-surface-400 text-sm">Configured: </span>
          <span className="font-medium text-brand-400">{configuredCount}</span>
          <span className="text-surface-400 text-sm"> / {requiredCount}</span>
        </div>
        {configuredCount === requiredCount && requiredCount > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
            <Shield className="w-4 h-4 text-green-400" />
            <span className="text-green-400 text-sm font-medium">All providers configured</span>
          </div>
        )}
      </div>

      {/* Configured Keys */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Configured Keys</h2>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
          </div>
        ) : apiKeys?.length > 0 ? (
          <div className="space-y-3">
            {apiKeys.map((key: any) => {
              const provider = getProviderInfo(key.provider)
              const Icon = getProviderIcon(key.provider)
              
              return (
                <motion.div
                  key={key.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl glass p-4 flex items-center gap-4"
                >
                  <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center">
                    <Icon className="w-6 h-6 text-brand-400" />
                  </div>

                  <div className="flex-1">
                    <h3 className="font-medium">{provider?.name || key.provider}</h3>
                    <div className="flex items-center gap-2 text-sm text-surface-400">
                      <code className="font-mono">
                        {showKey === key.id ? key.masked_key : '••••••••••••'}
                      </code>
                      <button
                        onClick={() => setShowKey(showKey === key.id ? null : key.id)}
                        className="hover:text-white transition-colors"
                      >
                        {showKey === key.id ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => testMutation.mutate(key.id)}
                      disabled={testMutation.isPending}
                      className="px-3 py-1.5 rounded-lg text-sm bg-surface-700 hover:bg-surface-600 transition-colors flex items-center gap-2"
                      title="Test API key"
                    >
                      {testMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <TestTube className="w-4 h-4" />
                      )}
                      Test
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this API key?')) {
                          deleteMutation.mutate(key.id)
                        }
                      }}
                      className="p-2 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-red-400 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              )
            })}
          </div>
        ) : (
          <div className="rounded-xl glass p-8 text-center">
            <Key className="w-12 h-12 text-surface-400 mx-auto mb-4" />
            <p className="text-surface-400">No API keys configured yet</p>
            <p className="text-sm text-surface-500 mt-1">Add keys to start using data providers</p>
          </div>
        )}
      </div>

      {/* Add New Key */}
      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add API Key
        </button>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl glass p-6"
        >
          <h3 className="font-semibold mb-4">Add New API Key</h3>
          
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Provider</label>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors"
              >
                <option value="">Select a provider</option>
                {providersWithoutKeys?.map((p: any) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
                {apiKeys?.map((k: any) => (
                  <option key={k.provider} value={k.provider}>
                    {getProviderInfo(k.provider)?.name || k.provider} (update)
                  </option>
                ))}
              </select>
            </div>

            {selectedProvider && getProviderInfo(selectedProvider)?.documentation_url && (
              <a
                href={getProviderInfo(selectedProvider)?.documentation_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-brand-400 hover:text-brand-300"
              >
                Get your API key <ExternalLink className="w-3 h-3" />
              </a>
            )}

            <div>
              <label className="block text-sm font-medium mb-2">API Key</label>
              <input
                type="password"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 transition-colors font-mono"
                placeholder="Enter your API key"
              />
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={saveMutation.isPending || !selectedProvider || !apiKeyInput}
                className="px-6 py-2 rounded-xl bg-brand-500 text-white font-medium hover:bg-brand-600 disabled:opacity-50 transition-colors flex items-center gap-2"
              >
                {saveMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Save
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAddForm(false)
                  setSelectedProvider('')
                  setApiKeyInput('')
                }}
                className="px-6 py-2 rounded-xl border border-surface-700 hover:bg-surface-800 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </motion.div>
      )}

      {/* Available Providers */}
      <div className="mt-12">
        <h2 className="text-lg font-semibold mb-4">Available Providers</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {providers?.map((provider: any) => {
            const Icon = getProviderIcon(provider.id)
            const isConfigured = apiKeys?.some((k: any) => k.provider === provider.id)
            
            return (
              <div
                key={provider.id}
                className={`rounded-xl p-4 border transition-colors ${
                  isConfigured 
                    ? 'bg-green-500/5 border-green-500/20' 
                    : 'bg-surface-800/50 border-surface-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      isConfigured ? 'bg-green-500/10' : 'bg-surface-700'
                    }`}>
                      <Icon className={`w-5 h-5 ${isConfigured ? 'text-green-400' : 'text-surface-400'}`} />
                    </div>
                    <div>
                      <h3 className="font-medium">{provider.name}</h3>
                      <p className="text-sm text-surface-400 mt-1">{provider.description}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {provider.supported_data_types?.map((type: string) => (
                          <span
                            key={type}
                            className="px-2 py-0.5 rounded text-xs bg-surface-700"
                          >
                            {type}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  {isConfigured && (
                    <span className="px-2 py-1 rounded-lg text-xs bg-green-500/10 text-green-400 flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      Configured
                    </span>
                  )}
                </div>
                {provider.requires_api_key && !isConfigured && (
                  <div className="mt-3 pt-3 border-t border-surface-700">
                    <button
                      onClick={() => {
                        setSelectedProvider(provider.id)
                        setShowAddForm(true)
                      }}
                      className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Add API key
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
