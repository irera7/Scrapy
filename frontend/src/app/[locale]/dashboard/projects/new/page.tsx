'use client'

import { useState } from 'react'
import { useRouter, Link } from '@/i18n/navigation'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { ArrowLeft, Loader2, FileText, Image as ImageIcon, Music, Video, Package } from 'lucide-react'
import { useTranslations } from 'next-intl'
import toast from 'react-hot-toast'

const dataTypes = [
  { id: 'text', label: 'Text', icon: FileText, description: 'Articles, documents, web pages', color: 'text-yellow-400 bg-yellow-500/10' },
  { id: 'image', label: 'Image', icon: ImageIcon, description: 'Photos, screenshots, graphics', color: 'text-pink-400 bg-pink-500/10' },
  { id: 'audio', label: 'Audio', icon: Music, description: 'Speech, music, podcasts', color: 'text-blue-400 bg-blue-500/10' },
  { id: 'video', label: 'Video', icon: Video, description: 'Clips, tutorials, streams', color: 'text-purple-400 bg-purple-500/10' },
  { id: 'mixed', label: 'Mixed', icon: Package, description: 'Multiple data types', color: 'text-cyan-400 bg-cyan-500/10' },
]

export default function NewProjectPage() {
  const t = useTranslations()
  const router = useRouter()
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [dataType, setDataType] = useState('text')

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project created!')
      router.push(`/dashboard/projects/${data.id}`)
    },
    onError: () => {
      toast.error('Failed to create project')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      name,
      description,
      data_type: dataType,
    })
  }

  return (
    <div className="p-8 max-w-2xl">
      <Link
        href="/dashboard/projects"
        className="inline-flex items-center gap-2 text-surface-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Projects
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold mb-2">Create New Project</h1>
        <p className="text-surface-400 mb-8">Set up a new data collection project</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-2">
              Project Name *
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
              placeholder="My AI Dataset"
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-surface-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors resize-none"
              placeholder="Describe what this project is for..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-3">
              Primary Data Type *
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {dataTypes.map((type) => {
                const Icon = type.icon
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => setDataType(type.id)}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      dataType === type.id
                        ? 'border-brand-500 bg-brand-500/10'
                        : 'border-surface-700 bg-surface-800 hover:border-surface-600'
                    }`}
                  >
                    <div className={`w-10 h-10 rounded-lg ${type.color} flex items-center justify-center mb-2`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="font-medium">{type.label}</div>
                    <div className="text-xs text-surface-400">{type.description}</div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={createMutation.isPending || !name}
              className="flex-1 py-3 px-4 rounded-xl bg-brand-500 text-white font-semibold hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Project'
              )}
            </button>
            <Link
              href="/dashboard/projects"
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
