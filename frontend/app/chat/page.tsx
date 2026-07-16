'use client'

import { ChatContainer } from '@/components/chat-container'
import { Header } from '@/components/header'

export default function ChatPage() {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Header />
      <ChatContainer />
    </div>
  )
}
