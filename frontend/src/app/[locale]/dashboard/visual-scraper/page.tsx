'use client'

import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { visualScraperApi, templatesApi } from '@/lib/api'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from '@/i18n/navigation'
import { useTranslations } from 'next-intl'
import {
  ArrowLeft,
  Globe,
  MousePointer,
  Code,
  Play,
  Eye,
  Save,
  Trash2,
  Plus,
  RefreshCw,
  Copy,
  Check,
  AlertCircle,
  Maximize2,
  X,
  ChevronRight,
  Wand2,
  FileJson,
  Layers,
} from 'lucide-react'
import { TutorialPanel, TutorialSection } from '@/components/ui/tutorial-panel'

const visualScraperTutorial: TutorialSection[] = [
  {
    title: 'Visual Scraper Introduction',
    content: 'The Visual Scraper lets you build web scrapers visually by clicking on elements. No coding required! Simply load a page, click on elements, and create extraction rules.',
    tips: [
      'This tool creates CSS selectors automatically',
      'Test selectors before adding them as rules',
      'Save templates for frequently scraped sites',
    ],
  },
  {
    title: 'Getting Started',
    content: 'Enter a URL in the address bar and click "Go" to load the page. The page will be rendered and a screenshot displayed.',
    steps: [
      { title: 'Enter URL', description: 'Type or paste the full URL including https://' },
      { title: 'Click Go', description: 'The page will load and display as a screenshot' },
      { title: 'Wait for Load', description: 'Complex pages may take a few seconds to render' },
    ],
    warning: 'Some websites block automated access. If a page doesn\'t load, try a different site.',
  },
  {
    title: 'Selecting Elements',
    content: 'Click directly on any element in the screenshot to select it. The system will analyze the element and suggest CSS selectors.',
    steps: [
      { title: 'Click Element', description: 'Click on any text, image, or link in the screenshot' },
      { title: 'View Info', description: 'See tag name, classes, ID, and text content' },
      { title: 'Choose Selector', description: 'Pick from suggested selectors or write your own' },
    ],
    tips: [
      'More specific selectors (with IDs) are more reliable',
      'Check "matches count" to see how many elements match',
      'Use the Test button to verify selector accuracy',
    ],
  },
  {
    title: 'Creating Extraction Rules',
    content: 'Rules define what data to extract from each element. Add rules for each piece of information you want to collect.',
    steps: [
      { title: 'Add Rule', description: 'Click "+ Add Rule" or use the plus button next to a selector' },
      { title: 'Name the Field', description: 'Give a descriptive name like "title" or "price"' },
      { title: 'Set Extract Type', description: 'Choose text, HTML, href (links), src (images), or attribute' },
      { title: 'Enable Multiple', description: 'Check "Multiple" to extract all matching elements' },
    ],
  },
  {
    title: 'Extract Types Explained',
    content: 'Different extract types capture different data from elements.',
    steps: [
      { title: 'Text', description: 'Inner text content only (most common)' },
      { title: 'HTML', description: 'Full HTML markup including tags' },
      { title: 'Link (href)', description: 'URL from anchor tags' },
      { title: 'Image (src)', description: 'Image URL from img tags' },
      { title: 'Attribute', description: 'Any HTML attribute value (specify name)' },
    ],
  },
  {
    title: 'Testing & Extracting',
    content: 'Once you\'ve created rules, click "Extract" to test them against the current page.',
    steps: [
      { title: 'Test Selector', description: 'Use the eye icon to preview what a selector matches' },
      { title: 'Extract Data', description: 'Click "Extract" button to run all rules' },
      { title: 'View JSON', description: 'Results appear in the Data tab as JSON' },
      { title: 'Copy Results', description: 'Use the Copy button to copy extracted data' },
    ],
    tips: [
      'If results don\'t look right, adjust selectors and re-extract',
      'Save working configurations as templates for reuse',
      'The "Apply Template" button loads rules from saved templates',
    ],
  },
]

interface ExtractionRule {
  id: string
  name: string
  selector: string
  extractType: string
  attributeName?: string
  multiple: boolean
  transform?: string
}

interface SelectedElementInfo {
  tag: string
  id?: string
  classes: string[]
  text: string
  css_selector: string
  xpath: string
  suggested_selectors: Array<{
    selector: string
    specificity: number
    matches_count: number
    sample_text: string
  }>
}

export default function VisualScraperPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [url, setUrl] = useState('')
  const [currentUrl, setCurrentUrl] = useState('')
  const [pageTitle, setPageTitle] = useState('')
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [selectedElement, setSelectedElement] = useState<any>(null)
  const [rules, setRules] = useState<ExtractionRule[]>([])
  const [extractedData, setExtractedData] = useState<any>(null)
  const [selectorTest, setSelectorTest] = useState<any>(null)
  const [testSelector, setTestSelector] = useState('')
  const [activeTab, setActiveTab] = useState<'selector' | 'rules' | 'preview'>('selector')
  const [isLoading, setIsLoading] = useState(false)
  const [clickedElement, setClickedElement] = useState<SelectedElementInfo | null>(null)
  const [isSelectingElement, setIsSelectingElement] = useState(false)
  const imageRef = useRef<HTMLImageElement>(null)
  
  // Create session
  const createSession = useMutation({
    mutationFn: visualScraperApi.createSession,
    onSuccess: (data) => {
      setSessionId(data.session_id)
    },
  })
  
  // Navigate
  const navigate = useMutation({
    mutationFn: ({ sessionId, url }: { sessionId: string; url: string }) =>
      visualScraperApi.navigate(sessionId, url),
    onSuccess: (data) => {
      setCurrentUrl(data.url)
      setPageTitle(data.title)
      takeScreenshot()
    },
  })
  
  // Take screenshot
  const takeScreenshotMutation = useMutation({
    mutationFn: (sessionId: string) => visualScraperApi.takeScreenshot(sessionId, false),
    onSuccess: (data) => {
      setScreenshot(`data:image/png;base64,${data.image}`)
    },
  })
  
  // Test selector
  const testSelectorMutation = useMutation({
    mutationFn: ({ sessionId, selector }: { sessionId: string; selector: string }) =>
      visualScraperApi.testSelector(sessionId, selector),
    onSuccess: (data) => {
      setSelectorTest(data)
    },
  })
  
  // Get element at coordinates (click-to-select)
  const getElementMutation = useMutation({
    mutationFn: ({ sessionId, x, y }: { sessionId: string; x: number; y: number }) =>
      visualScraperApi.getElement(sessionId, x, y),
    onSuccess: (data) => {
      setClickedElement(data)
      setTestSelector(data.css_selector)
      setActiveTab('selector')
    },
  })
  
  // Extract data
  const extractData = useMutation({
    mutationFn: ({ sessionId, rules }: { sessionId: string; rules: any[] }) =>
      visualScraperApi.extractData(sessionId, rules),
    onSuccess: (data) => {
      setExtractedData(data.data)
    },
  })
  
  // Match template
  const { data: matchedTemplate } = useQuery({
    queryKey: ['match-template', currentUrl],
    queryFn: () => templatesApi.matchUrl(currentUrl),
    enabled: !!currentUrl,
  })
  
  // Initialize session on mount
  useEffect(() => {
    createSession.mutate()
    
    return () => {
      if (sessionId) {
        visualScraperApi.endSession(sessionId).catch(() => {})
      }
    }
  }, [])
  
  const handleNavigate = () => {
    if (!sessionId || !url) return
    navigate.mutate({ sessionId, url })
  }
  
  const takeScreenshot = () => {
    if (!sessionId) return
    takeScreenshotMutation.mutate(sessionId)
  }
  
  const handleTestSelector = () => {
    if (!sessionId || !testSelector) return
    testSelectorMutation.mutate({ sessionId, selector: testSelector })
  }
  
  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!sessionId || !imageRef.current) return
    
    const img = imageRef.current
    const rect = img.getBoundingClientRect()
    
    // Calculate the actual coordinates on the page (accounting for image scaling)
    const scaleX = img.naturalWidth / rect.width
    const scaleY = img.naturalHeight / rect.height
    
    const x = Math.round((e.clientX - rect.left) * scaleX)
    const y = Math.round((e.clientY - rect.top) * scaleY)
    
    console.log(`Clicked at: ${x}, ${y}`)
    getElementMutation.mutate({ sessionId, x, y })
  }
  
  const handleAddRule = (selector: string = testSelector) => {
    const newRule: ExtractionRule = {
      id: `rule_${Date.now()}`,
      name: `Field ${rules.length + 1}`,
      selector,
      extractType: 'text',
      multiple: false,
    }
    setRules([...rules, newRule])
    setActiveTab('rules')
  }
  
  const handleUpdateRule = (id: string, updates: Partial<ExtractionRule>) => {
    setRules(rules.map(r => r.id === id ? { ...r, ...updates } : r))
  }
  
  const handleDeleteRule = (id: string) => {
    setRules(rules.filter(r => r.id !== id))
  }
  
  const handleExtractData = () => {
    if (!sessionId || rules.length === 0) return
    
    extractData.mutate({
      sessionId,
      rules: rules.map(r => ({
        name: r.name,
        selector: r.selector,
        extract_type: r.extractType,
        attribute_name: r.attributeName,
        multiple: r.multiple,
        transform: r.transform,
      })),
    })
    setActiveTab('preview')
  }
  
  const handleApplyTemplate = () => {
    if (!matchedTemplate?.template) return
    
    const newRules: ExtractionRule[] = matchedTemplate.template.fields.map((field: any, i: number) => ({
      id: `rule_${Date.now()}_${i}`,
      name: field.name,
      selector: field.selector,
      extractType: field.extract_type,
      attributeName: field.attribute,
      multiple: field.multiple,
    }))
    
    setRules(newRules)
    setActiveTab('rules')
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Tutorial */}
      <TutorialPanel
        title="Visual Scraper Guide"
        description="Learn how to build scrapers by clicking on elements"
        sections={visualScraperTutorial}
        storageKey="visual-scraper"
      />

      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-surface-800">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="p-2 rounded-xl hover:bg-surface-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold">Visual Scraper</h1>
            <p className="text-sm text-surface-400">Point-and-click selector builder</p>
          </div>
        </div>
        
        {matchedTemplate?.matched && (
          <button
            onClick={handleApplyTemplate}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 transition-colors"
          >
            <Wand2 className="w-4 h-4" />
            Apply Template: {matchedTemplate.template.name}
          </button>
        )}
      </div>
      
      {/* URL Bar */}
      <div className="flex items-center gap-2 p-4 border-b border-surface-800">
        <div className="flex items-center gap-2 flex-1">
          <Globe className="w-5 h-5 text-surface-400" />
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
            placeholder="Enter URL to scrape..."
            className="flex-1 px-4 py-2 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none"
          />
        </div>
        <button
          onClick={handleNavigate}
          disabled={!sessionId || !url || navigate.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50"
        >
          {navigate.isPending ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Go
        </button>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Preview Panel */}
        <div className="flex-1 p-4 overflow-auto bg-surface-950">
          {screenshot ? (
            <div className="relative inline-block">
              <img
                ref={imageRef}
                src={screenshot}
                alt="Page preview"
                onClick={handleImageClick}
                className={`max-w-full border border-surface-700 rounded-lg transition-all ${
                  getElementMutation.isPending 
                    ? 'cursor-wait opacity-75' 
                    : 'cursor-crosshair hover:border-brand-500'
                }`}
                title="Click on an element to select it"
              />
              {currentUrl && (
                <div className="absolute top-2 left-2 px-3 py-1 rounded-lg bg-black/50 text-white text-sm">
                  {pageTitle || currentUrl}
                </div>
              )}
              <div className="absolute top-2 right-2 flex gap-2">
                <button
                  onClick={takeScreenshot}
                  className="p-2 rounded-lg bg-black/50 hover:bg-black/70 transition-colors"
                  title="Refresh screenshot"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              {/* Click instruction overlay */}
              <div className="absolute bottom-2 left-2 px-3 py-1 rounded-lg bg-brand-500/80 text-white text-sm flex items-center gap-2">
                <MousePointer className="w-4 h-4" />
                Click on any element to select it
              </div>
              {/* Loading indicator when selecting */}
              {getElementMutation.isPending && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/30 rounded-lg">
                  <div className="px-4 py-2 rounded-lg bg-black/70 text-white flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Analyzing element...
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Globe className="w-16 h-16 mx-auto mb-4 text-surface-600" />
                <h3 className="text-lg font-medium mb-2">Enter a URL to start</h3>
                <p className="text-surface-400">The page preview will appear here</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Side Panel */}
        <div className="w-[400px] border-l border-surface-800 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-surface-800">
            <button
              onClick={() => setActiveTab('selector')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'selector'
                  ? 'border-b-2 border-brand-500 text-brand-400'
                  : 'text-surface-400 hover:text-white'
              }`}
            >
              <MousePointer className="w-4 h-4 inline mr-2" />
              Selector
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'rules'
                  ? 'border-b-2 border-brand-500 text-brand-400'
                  : 'text-surface-400 hover:text-white'
              }`}
            >
              <Layers className="w-4 h-4 inline mr-2" />
              Rules ({rules.length})
            </button>
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'preview'
                  ? 'border-b-2 border-brand-500 text-brand-400'
                  : 'text-surface-400 hover:text-white'
              }`}
            >
              <FileJson className="w-4 h-4 inline mr-2" />
              Data
            </button>
          </div>
          
          {/* Tab Content */}
          <div className="flex-1 overflow-auto p-4">
            {/* Selector Tab */}
            {activeTab === 'selector' && (
              <div className="space-y-4">
                {/* Clicked Element Info */}
                {clickedElement && (
                  <div className="p-4 rounded-xl bg-brand-500/10 border border-brand-500/30 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-brand-400 flex items-center gap-2">
                        <MousePointer className="w-4 h-4" />
                        Selected Element
                      </h4>
                      <button
                        onClick={() => setClickedElement(null)}
                        className="p-1 rounded hover:bg-surface-700"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    
                    <div className="text-sm space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-surface-400">Tag:</span>
                        <code className="px-2 py-0.5 rounded bg-surface-800 text-purple-400">
                          &lt;{clickedElement.tag}&gt;
                        </code>
                        {clickedElement.id && (
                          <code className="px-2 py-0.5 rounded bg-surface-800 text-green-400">
                            #{clickedElement.id}
                          </code>
                        )}
                      </div>
                      
                      {clickedElement.classes.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          <span className="text-surface-400">Classes:</span>
                          {clickedElement.classes.map((cls, i) => (
                            <code key={i} className="px-2 py-0.5 rounded bg-surface-800 text-blue-400 text-xs">
                              .{cls}
                            </code>
                          ))}
                        </div>
                      )}
                      
                      {clickedElement.text && (
                        <div>
                          <span className="text-surface-400">Text:</span>
                          <div className="mt-1 p-2 rounded bg-surface-800 text-surface-300 text-xs line-clamp-2">
                            {clickedElement.text}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Suggested Selectors */}
                    {clickedElement.suggested_selectors && clickedElement.suggested_selectors.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-sm text-surface-400">Suggested Selectors:</span>
                        <div className="space-y-1">
                          {clickedElement.suggested_selectors.map((suggestion, i) => (
                            <div 
                              key={i}
                              className="flex items-center justify-between p-2 rounded-lg bg-surface-800 hover:bg-surface-700 cursor-pointer group"
                              onClick={() => {
                                setTestSelector(suggestion.selector)
                                testSelectorMutation.mutate({ sessionId: sessionId!, selector: suggestion.selector })
                              }}
                            >
                              <code className="text-xs text-surface-300 font-mono truncate flex-1">
                                {suggestion.selector}
                              </code>
                              <div className="flex items-center gap-2 ml-2">
                                <span className="text-xs text-surface-500">
                                  {suggestion.matches_count} match{suggestion.matches_count !== 1 ? 'es' : ''}
                                </span>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleAddRule(suggestion.selector)
                                  }}
                                  className="p-1 rounded bg-brand-500/20 text-brand-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                  title="Add as rule"
                                >
                                  <Plus className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                <div>
                  <label className="block text-sm font-medium mb-2">Test Selector</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={testSelector}
                      onChange={(e) => setTestSelector(e.target.value)}
                      placeholder=".product-title, #price"
                      className="flex-1 px-4 py-2 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:outline-none font-mono text-sm"
                    />
                    <button
                      onClick={handleTestSelector}
                      disabled={!sessionId || !testSelector || testSelectorMutation.isPending}
                      className="px-4 py-2 rounded-xl bg-surface-700 hover:bg-surface-600 transition-colors disabled:opacity-50"
                    >
                      {testSelectorMutation.isPending ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
                
                {/* Selector Results */}
                {selectorTest && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-surface-400">
                        Found {selectorTest.count} element{selectorTest.count !== 1 ? 's' : ''}
                      </span>
                      <button
                        onClick={() => handleAddRule(testSelector)}
                        className="flex items-center gap-1 px-3 py-1 rounded-lg bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 text-sm"
                      >
                        <Plus className="w-3 h-3" />
                        Add Rule
                      </button>
                    </div>
                    
                    <div className="space-y-2 max-h-[200px] overflow-auto">
                      {selectorTest.matches?.slice(0, 10).map((match: any, i: number) => (
                        <div key={i} className="p-3 rounded-xl bg-surface-800/50 text-sm">
                          <div className="font-mono text-xs text-surface-400 mb-1">
                            &lt;{match.tag}&gt;
                          </div>
                          <div className="text-surface-300 line-clamp-2">
                            {match.text || '(empty)'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Tips - only show if no element selected */}
                {!clickedElement && !selectorTest && (
                  <div className="p-4 rounded-xl bg-surface-800/50 text-sm">
                    <h4 className="font-medium mb-2">How to Use</h4>
                    <ul className="space-y-1 text-surface-400">
                      <li>• <strong>Click on the screenshot</strong> to select an element</li>
                      <li>• Or type a CSS selector manually above</li>
                      <li>• Use <code className="bg-surface-700 px-1 rounded">.class</code> for class names</li>
                      <li>• Use <code className="bg-surface-700 px-1 rounded">#id</code> for IDs</li>
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            {/* Rules Tab */}
            {activeTab === 'rules' && (
              <div className="space-y-4">
                {rules.length === 0 ? (
                  <div className="text-center py-8">
                    <Layers className="w-12 h-12 mx-auto mb-4 text-surface-500" />
                    <p className="text-surface-400 mb-4">No extraction rules yet</p>
                    <button
                      onClick={() => handleAddRule('')}
                      className="flex items-center gap-2 px-4 py-2 mx-auto rounded-xl bg-brand-500/10 text-brand-400 hover:bg-brand-500/20"
                    >
                      <Plus className="w-4 h-4" />
                      Add Rule
                    </button>
                  </div>
                ) : (
                  <>
                    {rules.map((rule, index) => (
                      <div key={rule.id} className="p-4 rounded-xl bg-surface-800/50 space-y-3">
                        <div className="flex items-center justify-between">
                          <input
                            type="text"
                            value={rule.name}
                            onChange={(e) => handleUpdateRule(rule.id, { name: e.target.value })}
                            className="font-medium bg-transparent border-none focus:outline-none"
                          />
                          <button
                            onClick={() => handleDeleteRule(rule.id)}
                            className="p-1 rounded hover:bg-red-500/10 text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        
                        <input
                          type="text"
                          value={rule.selector}
                          onChange={(e) => handleUpdateRule(rule.id, { selector: e.target.value })}
                          placeholder="CSS Selector"
                          className="w-full px-3 py-2 rounded-lg bg-surface-900 border border-surface-700 focus:border-brand-500 focus:outline-none font-mono text-sm"
                        />
                        
                        <div className="flex gap-2">
                          <select
                            value={rule.extractType}
                            onChange={(e) => handleUpdateRule(rule.id, { extractType: e.target.value })}
                            className="flex-1 px-3 py-2 rounded-lg bg-surface-900 border border-surface-700 focus:border-brand-500 focus:outline-none text-sm"
                          >
                            <option value="text">Text</option>
                            <option value="html">HTML</option>
                            <option value="attribute">Attribute</option>
                            <option value="href">Link (href)</option>
                            <option value="src">Image (src)</option>
                          </select>
                          
                          <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-900 border border-surface-700 text-sm">
                            <input
                              type="checkbox"
                              checked={rule.multiple}
                              onChange={(e) => handleUpdateRule(rule.id, { multiple: e.target.checked })}
                              className="rounded"
                            />
                            Multiple
                          </label>
                        </div>
                        
                        {rule.extractType === 'attribute' && (
                          <input
                            type="text"
                            value={rule.attributeName || ''}
                            onChange={(e) => handleUpdateRule(rule.id, { attributeName: e.target.value })}
                            placeholder="Attribute name (e.g., data-id)"
                            className="w-full px-3 py-2 rounded-lg bg-surface-900 border border-surface-700 focus:border-brand-500 focus:outline-none text-sm"
                          />
                        )}
                      </div>
                    ))}
                    
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleAddRule('')}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-dashed border-surface-600 hover:border-surface-500 text-surface-400 hover:text-white transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        Add Rule
                      </button>
                      
                      <button
                        onClick={handleExtractData}
                        disabled={rules.length === 0 || extractData.isPending}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-500 text-white hover:bg-brand-600 transition-colors disabled:opacity-50"
                      >
                        {extractData.isPending ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                        Extract
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
            
            {/* Data Preview Tab */}
            {activeTab === 'preview' && (
              <div className="space-y-4">
                {extractedData ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-surface-400">Extracted Data</span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(JSON.stringify(extractedData, null, 2))
                        }}
                        className="flex items-center gap-1 px-3 py-1 rounded-lg bg-surface-700 hover:bg-surface-600 text-sm"
                      >
                        <Copy className="w-3 h-3" />
                        Copy
                      </button>
                    </div>
                    
                    <pre className="p-4 rounded-xl bg-surface-900 overflow-auto text-sm font-mono max-h-[400px]">
                      {JSON.stringify(extractedData, null, 2)}
                    </pre>
                  </>
                ) : (
                  <div className="text-center py-8">
                    <FileJson className="w-12 h-12 mx-auto mb-4 text-surface-500" />
                    <p className="text-surface-400">
                      Add rules and click Extract to preview data
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

