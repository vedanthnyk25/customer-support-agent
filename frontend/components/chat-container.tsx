'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageList } from './message-list'
import { ChatInput } from './chat-input'

export interface OrderConfirmationPayload {
  type: string
  product_id: string
  product_name: string
  quantity: number
  unit_price: number
  total_price: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  confirmation?: {
    payload: OrderConfirmationPayload
    threadId: string
    resolved: boolean
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Reveals text on a steady per-frame cadence, decoupled from how bursty
// the underlying SSE chunk arrival is (see earlier fix -- short replies
// can have all their chunks land within milliseconds of each other).
function createTypewriter(
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  messageId: string
) {
  let fullText = ''
  let revealedLength = 0
  let streamDone = false
  let frameId: number | null = null
  const CHARS_PER_FRAME = 2

  const tick = () => {
    if (revealedLength < fullText.length) {
      revealedLength = Math.min(revealedLength + CHARS_PER_FRAME, fullText.length)
      const visible = fullText.slice(0, revealedLength)
      setMessages((prev) => {
        const updated = [...prev]
        const idx = updated.findIndex((m) => m.id === messageId)
        if (idx !== -1) updated[idx] = { ...updated[idx], content: visible }
        return updated
      })
    }
    frameId = !streamDone || revealedLength < fullText.length ? requestAnimationFrame(tick) : null
  }

  return {
    feed(text: string) {
      fullText += text
      if (frameId === null) frameId = requestAnimationFrame(tick)
    },
    finish() {
      streamDone = true
      if (frameId === null && revealedLength < fullText.length) {
        frameId = requestAnimationFrame(tick)
      }
    },
  }
}

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

  const [threadId] = useState<string>(() =>
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `thread-${Date.now()}-${Math.random().toString(36).slice(2)}`
  )

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /**
   * Consumes an SSE response from either /api/chat or /api/chat/resume.
   * Both endpoints emit the same event shapes ({chunk}, {type: "confirmation_required", payload},
   * {error}, [DONE]), so this logic is fully shared between a fresh send
   * and a post-confirmation resume.
   */
  async function consumeStream(response: Response) {
    if (!response.ok) throw new Error(`API error: ${response.statusText}`)
    if (!response.body) throw new Error('No response body')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    let assistantId: string | null = null
    let typewriter: ReturnType<typeof createTypewriter> | null = null

    // Buffer across reads -- a single "data: {...}\n\n" event can be split
    // across multiple network chunks/reader.read() calls.
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

          let parsed: any
          try {
            parsed = JSON.parse(data)
          } catch {
            continue
          }

          if (parsed.chunk) {
            if (!assistantId) {
              assistantId = `assistant-${Date.now()}`
              setMessages((prev) => [
                ...prev,
                { id: assistantId!, role: 'assistant', content: '', timestamp: new Date() },
              ])
              typewriter = createTypewriter(setMessages, assistantId)
            }
            typewriter?.feed(parsed.chunk)
          }

          if (parsed.type === 'confirmation_required') {
            setMessages((prev) => [
              ...prev,
              {
                id: `confirm-${Date.now()}`,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                confirmation: { payload: parsed.payload, threadId, resolved: false },
              },
            ])
          }

          if (parsed.error) {
            throw new Error(parsed.error)
          }
        }
      }
    } finally {
      typewriter?.finish()
    }
  }

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return

    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content, timestamp: new Date() },
    ])
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, thread_id: threadId }),
      })
      await consumeStream(response)
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to send message'
      setMessages((prev) => [
        ...prev,
        { id: `error-${Date.now()}`, role: 'assistant', content: `Error: ${msg}`, timestamp: new Date() },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirmOrder = async (confirmMessageId: string, confirmed: boolean) => {
    // Mark this confirmation card resolved so its buttons disappear, and
    // record the user's choice as a small inline note.
    setMessages((prev) =>
      prev.map((m) =>
        m.id === confirmMessageId && m.confirmation
          ? { ...m, confirmation: { ...m.confirmation, resolved: true } }
          : m
      )
    )
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/api/chat/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, confirmed }),
      })
      await consumeStream(response)
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to resume'
      setMessages((prev) => [
        ...prev,
        { id: `error-${Date.now()}`, role: 'assistant', content: `Error: ${msg}`, timestamp: new Date() },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <MessageList messages={messages} onConfirmOrder={handleConfirmOrder} />
      <div ref={messagesEndRef} />
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  )
}
