'use client'

import * as React from 'react'
import { useCallback, useState } from 'react'
import { Upload, X, File, Image, Music, Video, FileText, Loader2 } from 'lucide-react'
import { cn, formatBytes } from '@/lib/utils'
import { Button } from './button'

interface FileUploadProps {
  accept?: string
  multiple?: boolean
  maxSize?: number // in bytes
  maxFiles?: number
  onUpload: (files: File[]) => Promise<void>
  disabled?: boolean
  className?: string
}

interface UploadedFile {
  file: File
  progress: number
  error?: string
}

function FileUpload({
  accept,
  multiple = false,
  maxSize = 100 * 1024 * 1024, // 100MB default
  maxFiles = 10,
  onUpload,
  disabled = false,
  className,
}: FileUploadProps) {
  const [isDragActive, setIsDragActive] = useState(false)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <Image className="h-5 w-5" />
    if (type.startsWith('audio/')) return <Music className="h-5 w-5" />
    if (type.startsWith('video/')) return <Video className="h-5 w-5" />
    if (type.includes('text') || type.includes('pdf')) return <FileText className="h-5 w-5" />
    return <File className="h-5 w-5" />
  }

  const validateFiles = useCallback((fileList: File[]): File[] => {
    const validFiles: File[] = []
    
    for (const file of fileList) {
      if (file.size > maxSize) {
        continue // Skip files that are too large
      }
      if (validFiles.length >= maxFiles) {
        break
      }
      validFiles.push(file)
    }
    
    return validFiles
  }, [maxSize, maxFiles])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true)
    } else if (e.type === 'dragleave') {
      setIsDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
    
    if (disabled) return
    
    const droppedFiles = Array.from(e.dataTransfer.files)
    const validFiles = validateFiles(droppedFiles)
    
    setFiles(prev => [
      ...prev,
      ...validFiles.map(file => ({ file, progress: 0 }))
    ])
  }, [disabled, validateFiles])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled || !e.target.files) return
    
    const selectedFiles = Array.from(e.target.files)
    const validFiles = validateFiles(selectedFiles)
    
    setFiles(prev => [
      ...prev,
      ...validFiles.map(file => ({ file, progress: 0 }))
    ])
    
    // Reset input
    e.target.value = ''
  }, [disabled, validateFiles])

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0 || isUploading) return
    
    setIsUploading(true)
    try {
      await onUpload(files.map(f => f.file))
      setFiles([])
    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const openFileDialog = () => {
    inputRef.current?.click()
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
        className={cn(
          'relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
          isDragActive
            ? 'border-brand-500 bg-brand-500/10'
            : 'border-surface-700 hover:border-surface-600 hover:bg-surface-800/50',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          disabled={disabled}
          className="hidden"
        />
        
        <div className="flex flex-col items-center gap-3">
          <div className={cn(
            'w-14 h-14 rounded-xl flex items-center justify-center transition-colors',
            isDragActive ? 'bg-brand-500/20 text-brand-400' : 'bg-surface-700 text-surface-400'
          )}>
            <Upload className="h-7 w-7" />
          </div>
          <div>
            <p className="font-medium">
              {isDragActive ? 'Drop files here' : 'Click or drag files to upload'}
            </p>
            <p className="text-sm text-surface-400 mt-1">
              {accept ? `Accepted: ${accept}` : 'All file types accepted'}
              {' • '}
              Max {formatBytes(maxSize)}
            </p>
          </div>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item, index) => (
            <div
              key={`${item.file.name}-${index}`}
              className="flex items-center gap-3 p-3 rounded-xl bg-surface-800/50 border border-surface-700"
            >
              <div className="text-surface-400">
                {getFileIcon(item.file.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{item.file.name}</p>
                <p className="text-xs text-surface-400">{formatBytes(item.file.size)}</p>
              </div>
              {item.error ? (
                <span className="text-xs text-red-400">{item.error}</span>
              ) : item.progress > 0 && item.progress < 100 ? (
                <span className="text-xs text-surface-400">{item.progress}%</span>
              ) : null}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  removeFile(index)
                }}
                disabled={isUploading}
                className="p-1.5 rounded-lg hover:bg-surface-700 text-surface-400 hover:text-white transition-colors disabled:opacity-50"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
          
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              onClick={() => setFiles([])}
              disabled={isUploading}
            >
              Clear All
            </Button>
            <Button
              onClick={handleUpload}
              isLoading={isUploading}
              disabled={files.length === 0}
            >
              Upload {files.length} file{files.length > 1 ? 's' : ''}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export { FileUpload }

