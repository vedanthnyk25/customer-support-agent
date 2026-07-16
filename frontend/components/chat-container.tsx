'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageList } from './message-list'
import { ChatInput } from './chat-input'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: 'Hello. I am your support agent. Ask me about orders, products, policies, or create a support ticket.',
      timestamp: new Date(),
    },
  ])
  const [isLoading, setIsLoading] = useState(false)

  // Generate a stable per-session thread id up front instead of starting
  // from ''. Previously every user's *first* message was sent with
  // thread_id: '' -- since that's an explicit (non-omitted) field value,
  // the backend's default_factory never kicks in, so every new user's
  // first message landed in the SAME shared conversation thread until
  // the server handed back a real UUID. Generating it client-side fixes
  // that entirely.
  const [threadId] = useState<string>(() =>
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `thread-${Date.now()}-${Math.random().toString(36).slice(2)}`
  )

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          thread_id: threadId,
        }),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`)
      }

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      const assistantId = `assistant-${Date.now()}`
      let messageAdded = false

      let fullText = ''
      let revealedLength = 0
      let streamDone = false
      let animationFrameId: number | null = null
      const REVEAL_CHARS_PER_FRAME = 2 // higher = faster typing

      const tick = () => {
        if (revealedLength < fullText.length) {
          revealedLength = Math.min(revealedLength + REVEAL_CHARS_PER_FRAME, fullText.length)
          const visibleText = fullText.slice(0, revealedLength)

          setMessages((prev) => {
            const updated = [...prev]
            const lastIndex = updated.length - 1
            if (updated[lastIndex]?.id === assistantId) {
              updated[lastIndex] = { ...updated[lastIndex], content: visibleText }
            }
            return updated
          })
        }

        if (!streamDone || revealedLength < fullText.length) {
          animationFrameId = requestAnimationFrame(tick)
        } else {
          animationFrameId = null
        }
      }

      // Buffer across reads: a single "data: {...}\n\n" SSE event can be
      // split across multiple network chunks / reader.read() calls. If
      // we naively split each chunk on '\n' independently, a line can
      // arrive truncated, fail JSON.parse, and get silently dropped as
      // a SyntaxError -- quietly eating part of the response. Instead
      // we accumulate into `buffer` and only process lines once we know
      // they're complete (i.e. everything before the last, possibly
      // incomplete, trailing segment).
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue

            const data = line.slice(6).trim()
            if (!data || data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)

              if (parsed.chunk) {
                fullText += parsed.chunk

                if (!messageAdded) {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: assistantId,
                      role: 'assistant',
                      content: '',
                      timestamp: new Date(),
                    },
                  ])
                  messageAdded = true
                  animationFrameId = requestAnimationFrame(tick)
                }
              }

              if (parsed.error) {
                throw new Error(parsed.error)
              }
            } catch (e) {
              if (e instanceof SyntaxError) continue
              throw e
            }
          }
        }
      } finally {
        streamDone = true
        // If nothing was ever added (e.g. an empty/errored response with
        // no chunks), there's no animation loop running to clean up.
        if (animationFrameId === null && messageAdded && revealedLength < fullText.length) {
          animationFrameId = requestAnimationFrame(tick)
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message'
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${errorMessage}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <MessageList messages={messages} />
      <div ref={messagesEndRef} />
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  )
}
