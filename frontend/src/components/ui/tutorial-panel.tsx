'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  X,
  Lightbulb,
  CheckCircle,
  ArrowRight,
  Info,
  AlertCircle,
  Zap,
} from 'lucide-react'

export interface TutorialStep {
  title: string
  description: string
  icon?: React.ReactNode
}

export interface TutorialSection {
  title: string
  content: string
  tips?: string[]
  warning?: string
  steps?: TutorialStep[]
}

interface TutorialPanelProps {
  title: string
  description: string
  sections: TutorialSection[]
  storageKey?: string
}

export function TutorialPanel({
  title,
  description,
  sections,
  storageKey,
}: TutorialPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [expandedSection, setExpandedSection] = useState<number | null>(0)
  const [hasSeenTutorial, setHasSeenTutorial] = useState(true)

  useEffect(() => {
    if (storageKey) {
      const seen = localStorage.getItem(`tutorial_seen_${storageKey}`)
      if (!seen) {
        setHasSeenTutorial(false)
        setIsOpen(true)
      }
    }
  }, [storageKey])

  const handleDismiss = () => {
    setIsOpen(false)
    if (storageKey) {
      localStorage.setItem(`tutorial_seen_${storageKey}`, 'true')
      setHasSeenTutorial(true)
    }
  }

  return (
    <>
      {/* Tutorial Toggle Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 rounded-2xl shadow-lg transition-all ${
          isOpen
            ? 'bg-surface-800 text-white'
            : hasSeenTutorial
            ? 'bg-surface-800/90 text-surface-300 hover:text-white hover:bg-surface-700'
            : 'bg-gradient-to-r from-brand-500 to-purple-600 text-white animate-pulse'
        }`}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <BookOpen className="w-5 h-5" />
        <span className="font-medium">Tutorial</span>
        {!hasSeenTutorial && (
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full" />
        )}
      </motion.button>

      {/* Tutorial Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, x: 400 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 400 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-surface-900 border-l border-surface-700 z-50 flex flex-col"
            >
              {/* Header */}
              <div className="flex items-start justify-between p-6 border-b border-surface-800">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                    <BookOpen className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">{title}</h2>
                    <p className="text-sm text-surface-400 mt-1">{description}</p>
                  </div>
                </div>
                <button
                  onClick={handleDismiss}
                  className="p-2 rounded-xl hover:bg-surface-800 text-surface-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {sections.map((section, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="rounded-2xl border border-surface-700 overflow-hidden"
                  >
                    {/* Section Header */}
                    <button
                      onClick={() =>
                        setExpandedSection(expandedSection === index ? null : index)
                      }
                      className="w-full flex items-center justify-between p-4 bg-surface-800/50 hover:bg-surface-800 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center text-brand-400">
                          {index + 1}
                        </div>
                        <h3 className="font-semibold text-white">{section.title}</h3>
                      </div>
                      {expandedSection === index ? (
                        <ChevronUp className="w-5 h-5 text-surface-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-surface-400" />
                      )}
                    </button>

                    {/* Section Content */}
                    <AnimatePresence>
                      {expandedSection === index && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="p-4 space-y-4 bg-surface-900/50">
                            {/* Main Content */}
                            <p className="text-surface-300 leading-relaxed">
                              {section.content}
                            </p>

                            {/* Steps */}
                            {section.steps && section.steps.length > 0 && (
                              <div className="space-y-3 mt-4">
                                {section.steps.map((step, stepIndex) => (
                                  <div
                                    key={stepIndex}
                                    className="flex items-start gap-3 p-3 rounded-xl bg-surface-800/50"
                                  >
                                    <div className="w-6 h-6 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 text-xs font-bold flex-shrink-0 mt-0.5">
                                      {stepIndex + 1}
                                    </div>
                                    <div>
                                      <h4 className="font-medium text-white text-sm">
                                        {step.title}
                                      </h4>
                                      <p className="text-xs text-surface-400 mt-1">
                                        {step.description}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Tips */}
                            {section.tips && section.tips.length > 0 && (
                              <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                                <div className="flex items-center gap-2 mb-2">
                                  <Lightbulb className="w-4 h-4 text-green-400" />
                                  <span className="text-sm font-medium text-green-400">
                                    Pro Tips
                                  </span>
                                </div>
                                <ul className="space-y-2">
                                  {section.tips.map((tip, tipIndex) => (
                                    <li
                                      key={tipIndex}
                                      className="flex items-start gap-2 text-sm text-green-300/80"
                                    >
                                      <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                      <span>{tip}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Warning */}
                            {section.warning && (
                              <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
                                <div className="flex items-start gap-2">
                                  <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                                  <p className="text-sm text-yellow-300/80">
                                    {section.warning}
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-surface-800 bg-surface-900">
                <button
                  onClick={handleDismiss}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 transition-colors"
                >
                  <Zap className="w-5 h-5" />
                  Got it, let's start!
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}

// Quick Tip Component for inline hints
export function QuickTip({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-sm">
      <Info className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
      <span className="text-blue-300/80">{children}</span>
    </div>
  )
}

