import { Message } from './chat-container'

interface MessageListProps {
  messages: Message[]
  onConfirmOrder: (messageId: string, confirmed: boolean) => void
}

export function MessageList({ messages, onConfirmOrder }: MessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {messages.map((message) => {
          if (message.confirmation) {
            const { payload, resolved } = message.confirmation
            return (
              <div key={message.id} className="flex justify-start">
                <div className="max-w-2xl w-full bg-transparent border-2 border-yellow-500 p-4 font-mono text-sm">
                  <div className="font-black text-xs tracking-wider mb-3 text-yellow-500">
                    CONFIRM ORDER
                  </div>
                  <div className="text-white space-y-1 mb-4">
                    <div>{payload.product_name} x{payload.quantity}</div>
                    <div className="text-gray-400">
                      ${payload.unit_price.toFixed(2)} each &middot; Total: ${payload.total_price.toFixed(2)}
                    </div>
                  </div>
                  {!resolved ? (
                    <div className="flex gap-3">
                      <button
                        onClick={() => onConfirmOrder(message.id, true)}
                        className="px-4 py-2 bg-white text-black border-2 border-white font-black text-xs hover:bg-gray-100"
                      >
                        CONFIRM
                      </button>
                      <button
                        onClick={() => onConfirmOrder(message.id, false)}
                        className="px-4 py-2 bg-transparent text-white border-2 border-gray-700 font-black text-xs hover:border-white"
                      >
                        CANCEL
                      </button>
                    </div>
                  ) : (
                    <div className="text-gray-500 text-xs">Response sent.</div>
                  )}
                </div>
              </div>
            )
          }

          return (
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
          )
        })}
      </div>
    </div>
  )
}
