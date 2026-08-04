import { ConversationView } from "@/components/chat/ConversationView";

export default function Page() {
  return (
    <main className="flex h-screen w-full flex-col items-center">
      <ConversationView />
    </main>
  );
}
