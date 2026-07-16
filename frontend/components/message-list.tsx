import { Message } from './chat-container'

interface MessageListProps {
  messages: Message[]
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl ${
                message.role === 'user'
                  ? 'bg-white text-black border-2 border-white'
                  : 'bg-transparent text-white border-2 border-gray-700'
              } p-4 font-mono text-sm leading-relaxed break-words`}
            >
              <div className="font-black text-xs tracking-wider mb-2 opacity-70">
                {message.role === 'user' ? 'YOU' : 'AGENT'}
              </div>
              <div className="whitespace-pre-wrap">{message.content}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
