import { createBrowserRouter, Navigate } from "react-router-dom";
import { ChatPage } from "./pages/ChatPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { KnowledgeListPage } from "./pages/admin/knowledge/KnowledgeListPage";
import { KnowledgeDocumentsPage } from "./pages/admin/knowledge/KnowledgeDocumentsPage";
import { IntentListPage } from "./pages/admin/intent-tree/IntentListPage";
import { IntentEditPage } from "./pages/admin/intent-tree/IntentEditPage";
import { RagTracePage } from "./pages/admin/traces/RagTracePage";
import { RagTraceDetailPage } from "./pages/admin/traces/RagTraceDetailPage";
import { MappingPage } from "./pages/admin/mapping/MappingPage";
import { KnowledgeDocumentDetailPage } from "./pages/admin/knowledge/KnowledgeDocumentDetailPage";

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/chat" replace /> },
  { path: "/chat", element: <ChatPage /> },
  { path: "/chat/:sessionId", element: <ChatPage /> },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      { index: true, element: <Navigate to="/admin/knowledge" replace /> },
      { path: "knowledge", element: <KnowledgeListPage /> },
      { path: "knowledge/:kbId", element: <KnowledgeDocumentsPage /> },
      { path: "knowledge/:kbId/docs/:docId", element: <KnowledgeDocumentDetailPage /> },
      { path: "intent-list", element: <IntentListPage /> },
      { path: "intent-list/:id/edit", element: <IntentEditPage /> },
      { path: "traces", element: <RagTracePage /> },
      { path: "traces/:runId", element: <RagTraceDetailPage /> },
      { path: "mapping", element: <MappingPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
