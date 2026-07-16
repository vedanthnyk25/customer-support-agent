'use client'

import { useState } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  isLoading: boolean
}

export function ChatInput({ onSendMessage, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSendMessage(input)
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      if (input.trim() && !isLoading) {
        onSendMessage(input)
        setInput('')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-800 bg-black px-6 py-6">
      <div className="max-w-4xl mx-auto flex gap-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="TYPE YOUR MESSAGE..."
          disabled={isLoading}
          className="flex-1 bg-gray-950 text-white border-2 border-gray-800 p-4 font-mono text-sm resize-none focus:outline-none focus:border-white disabled:opacity-50 placeholder-gray-700"
          rows={3}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-6 bg-white text-black border-2 border-white font-black text-xs tracking-wider hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-black border-t-transparent animate-spin" />
          ) : (
            <Send size={20} />
          )}
        </button>
      </div>
    </form>
  )
}
