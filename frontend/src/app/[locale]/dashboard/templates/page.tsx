'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { templatesApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  FileCode,
  Search,
  Globe,
  ShoppingCart,
  MessageSquare,
  BookOpen,
  Briefcase,
  Home,
  Folder,
  MessageCircle,
  GraduationCap,
  Layers,
  ChevronRight,
  Eye,
  Copy,
  Check,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const templatesTutorial: TutorialSection[] = [
  {
    title: 'Scraping Templates',
    content: 'Templates are pre-built extraction configurations for popular websites. Instead of manually creating CSS selectors, use templates to quickly set up scraping jobs for common sources.',
    tips: [
      'Templates save time by providing ready-to-use selectors',
      'Each template is optimized for its target website structure',
      'Copy template configs to customize for your specific needs',
    ],
  },
  {
    title: 'Template Categories',
    content: 'Templates are organized by website category: News, E-commerce, Social Media, Blogs, Job Boards, Real Estate, and more. Select a category to filter relevant templates.',
    steps: [
      { title: 'Browse Categories', description: 'Click category buttons to filter templates' },
      { title: 'Search', description: 'Use the search box to find specific websites' },
      { title: 'View All', description: 'Click "All" to see templates from all categories' },
    ],
  },
  {
    title: 'Template Details',
    content: 'Click on a template to view its full configuration including URL patterns, extraction fields, pagination settings, and JavaScript requirements.',
    tips: [
      'Fields define what data will be extracted (title, price, date, etc.)',
      'URL patterns show which pages the template works with',
      'JS badge indicates the page requires JavaScript rendering',
    ],
  },
  {
    title: 'Using a Template',
    content: 'Once you find a suitable template, click "Use Template" to create a new scraping job with the template\'s configuration pre-filled.',
    steps: [
      { title: 'Select Template', description: 'Click on a template card to view details' },
      { title: 'Review Fields', description: 'Check that the extraction fields match your needs' },
      { title: 'Use Template', description: 'Click "Use Template" to create a job' },
      { title: 'Configure Job', description: 'Adjust settings and target URLs as needed' },
    ],
  },
  {
    title: 'Copying Configuration',
    content: 'Use the "Copy" button to copy a template\'s configuration as JSON. This is useful for creating custom variations or using the config in API calls.',
    tips: [
      'Copied config includes all selectors and settings',
      'Paste into custom job creation for modifications',
      'Useful for programmatic job creation via API',
    ],
  },
  {
    title: 'Template Requirements',
    content: 'Some templates have special requirements like JavaScript rendering, scroll-to-bottom, or waiting for specific elements. Check the badges on template details.',
    warning: 'JavaScript-required templates need more resources and may be slower. Ensure your scraping infrastructure supports JS rendering.',
  },
]

const categoryIcons: Record<string, any> = {
  news: Globe,
  ecommerce: ShoppingCart,
  social_media: MessageSquare,
  blog: BookOpen,
  job_board: Briefcase,
  real_estate: Home,
  directory: Folder,
  forum: MessageCircle,
  academic: GraduationCap,
  general: Layers,
}

export default function TemplatesPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null)
  const [copied, setCopied] = useState(false)
  
  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ['template-categories'],
    queryFn: templatesApi.getCategories,
  })
  
  // Fetch templates
  const { data: templatesData, isLoading } = useQuery({
    queryKey: ['templates', selectedCategory, searchQuery],
    queryFn: () => templatesApi.list({
      category: selectedCategory || undefined,
      query: searchQuery || undefined,
    }),
  })
  
  const categories = categoriesData?.categories || []
  const templates = templatesData?.templates || []
  
  const handleCopyConfig = (template: any) => {
    const config = JSON.stringify({
      template_id: template.id,
      fields: template.fields,
      pagination: template.pagination_selector ? {
        selector: template.pagination_selector,
        type: template.pagination_type,
        max_pages: template.max_pages,
      } : null,
      wait_for: template.wait_for_selector,
      javascript_required: template.javascript_required,
    }, null, 2)
    
    navigator.clipboard.writeText(config)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-8">
      {/* Tutorial */}
      <TutorialPanel
        title="Scraping Templates Guide"
        description="Learn how to use pre-built templates for popular websites"
        sections={templatesTutorial}
        storageKey="templates"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Scraping Templates</h1>
          <p className="text-surface-400">Pre-built extraction configurations for popular websites</p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search templates..."
            className="w-full pl-12 pr-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Categories */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-4 py-2 rounded-xl transition-colors ${
            selectedCategory === null
              ? 'bg-brand-500 text-white'
              : 'bg-surface-800 text-surface-300 hover:bg-surface-700'
          }`}
        >
          All
        </button>
        {categories.map((cat: any) => {
          const Icon = categoryIcons[cat.id] || Layers
          return (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-brand-500 text-white'
                  : 'bg-surface-800 text-surface-300 hover:bg-surface-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {cat.name}
            </button>
          )
        })}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Templates List */}
        <div className="lg:col-span-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full" />
            </div>
          ) : templates.length > 0 ? (
            <div className="grid gap-4">
              {templates.map((template: any) => {
                const Icon = categoryIcons[template.category] || Layers
                return (
                  <motion.div
                    key={template.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      selectedTemplate?.id === template.id
                        ? 'border-brand-500 bg-brand-500/5'
                        : 'border-surface-800 bg-surface-900/50 hover:border-surface-700'
                    }`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
                        <Icon className="w-5 h-5 text-brand-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold">{template.name}</h3>
                          {template.javascript_required && (
                            <span className="px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 text-xs">
                              JS
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-surface-400 mb-2 line-clamp-2">
                          {template.description}
                        </p>
                        <div className="flex items-center gap-2 flex-wrap">
                          {template.tags?.slice(0, 3).map((tag: string) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 rounded-full bg-surface-800 text-surface-400 text-xs"
                            >
                              {tag}
                            </span>
                          ))}
                          <span className="text-xs text-surface-500">
                            {template.fields?.length || 0} fields
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-surface-500 flex-shrink-0" />
                    </div>
                  </motion.div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <FileCode className="w-12 h-12 mx-auto mb-4 text-surface-500" />
              <h3 className="text-lg font-medium mb-2">No templates found</h3>
              <p className="text-surface-400">Try adjusting your search or filters</p>
            </div>
          )}
        </div>

        {/* Template Detail */}
        <div className="lg:col-span-1">
          {selectedTemplate ? (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="rounded-2xl glass p-6 sticky top-8"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">{selectedTemplate.name}</h2>
                <button
                  onClick={() => handleCopyConfig(selectedTemplate)}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg bg-surface-800 hover:bg-surface-700 text-sm"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              
              <p className="text-surface-400 text-sm mb-6">
                {selectedTemplate.description}
              </p>
              
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-surface-400 mb-2">URL Patterns</h4>
                  <div className="space-y-1">
                    {selectedTemplate.url_patterns?.slice(0, 3).map((pattern: string, i: number) => (
                      <div key={i} className="text-xs font-mono text-surface-500 truncate">
                        {pattern}
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <h4 className="text-sm font-medium text-surface-400 mb-2">
                    Fields ({selectedTemplate.fields?.length})
                  </h4>
                  <div className="space-y-2 max-h-[300px] overflow-auto">
                    {selectedTemplate.fields?.map((field: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg bg-surface-800/50">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{field.name}</span>
                          <span className="text-xs text-surface-500">{field.extract_type}</span>
                        </div>
                        <div className="text-xs font-mono text-surface-400 truncate">
                          {field.selector}
                        </div>
                        {field.required && (
                          <span className="text-xs text-red-400">Required</span>
                        )}
                        {field.multiple && (
                          <span className="text-xs text-blue-400 ml-2">Multiple</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                
                {selectedTemplate.pagination_selector && (
                  <div>
                    <h4 className="text-sm font-medium text-surface-400 mb-2">Pagination</h4>
                    <div className="p-3 rounded-lg bg-surface-800/50 text-sm">
                      <div className="text-xs font-mono text-surface-400 truncate mb-1">
                        {selectedTemplate.pagination_selector}
                      </div>
                      <div className="text-xs text-surface-500">
                        Type: {selectedTemplate.pagination_type} | Max: {selectedTemplate.max_pages} pages
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="flex flex-wrap gap-2 pt-4 border-t border-surface-800">
                  {selectedTemplate.javascript_required && (
                    <span className="px-3 py-1 rounded-full bg-yellow-500/10 text-yellow-400 text-xs">
                      JavaScript Required
                    </span>
                  )}
                  {selectedTemplate.scroll_to_bottom && (
                    <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs">
                      Scroll Required
                    </span>
                  )}
                  {selectedTemplate.wait_for_selector && (
                    <span className="px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 text-xs">
                      Wait for Element
                    </span>
                  )}
                </div>
                
                <Link
                  href={`/dashboard/jobs/new?template=${selectedTemplate.id}`}
                  className="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors"
                >
                  Use Template
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            </motion.div>
          ) : (
            <div className="rounded-2xl glass p-6 text-center">
              <Eye className="w-12 h-12 mx-auto mb-4 text-surface-500" />
              <h3 className="font-medium mb-2">Select a Template</h3>
              <p className="text-sm text-surface-400">
                Click on a template to view details and extraction fields
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

