import { Fragment, useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronDown, ChevronRight, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { knowledgeService } from "@/services/knowledgeService";
import { STATUS_COLORS, STATUS_LABELS } from "@/utils/documentStatus";
import type { Chunk, IngestionTaskResponse, DocumentStatus } from "@/types";

const formatDate = (value: string | null | undefined) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN");
};

const PAGE_SIZE = 20;

export function KnowledgeDocumentDetailPage() {
  const { kbId, docId } = useParams<{ kbId: string; docId: string }>();
  const navigate = useNavigate();

  const [task, setTask] = useState<IngestionTaskResponse | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);

  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [chunksLoading, setChunksLoading] = useState(false);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchTask = useCallback(async () => {
    if (!kbId || !docId) return;
    setTaskLoading(true);
    try {
      const res = await knowledgeService.getIngestionTask(kbId, docId);
      setTask(res.data);
    } catch {
      toast.error("加载摄入任务失败");
    } finally {
      setTaskLoading(false);
    }
  }, [kbId, docId]);

  const fetchChunks = useCallback(async (p: number) => {
    if (!kbId || !docId) return;
    setChunksLoading(true);
    try {
      const res = await knowledgeService.listChunks(kbId, docId, p, PAGE_SIZE);
      setChunks(res.data.items);
      setTotal(res.data.total);
    } catch {
      toast.error("加载 Chunk 列表失败");
    } finally {
      setChunksLoading(false);
    }
  }, [kbId, docId]);

  useEffect(() => {
    fetchTask();
    fetchChunks(1);
  }, [fetchTask, fetchChunks]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    fetchChunks(newPage);
    setExpandedId(null);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const sortedTimings = task
    ? Object.entries(task.node_timings).sort(([, a], [, b]) => b - a)
    : [];

  return (
    <div className="admin-page">
      {/* 页头 */}
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">文档详情</h1>
        </div>
        <div className="admin-page-actions">
          <Button variant="outline" onClick={() => navigate(`/admin/knowledge/${kbId}`)}>
            返回文档列表
          </Button>
        </div>
      </div>

      {/* 摄入任务区块 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>摄入任务</CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchTask} disabled={taskLoading}>
              <RefreshCw className={cn("h-4 w-4", taskLoading && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {taskLoading && <p className="text-sm text-muted-foreground">加载中…</p>}
          {task && !taskLoading && (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-y-3 max-w-md">
                <span className="text-muted-foreground">状态</span>
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium w-fit",
                    STATUS_COLORS[task.status as DocumentStatus] ?? "bg-gray-100 text-gray-600"
                  )}
                >
                  {STATUS_LABELS[task.status as DocumentStatus] ?? task.status}
                </span>

                <span className="text-muted-foreground">Chunk 数</span>
                <span>{task.chunk_count ?? "—"}</span>

                <span className="text-muted-foreground">开始时间</span>
                <span>{formatDate(task.started_at)}</span>

                <span className="text-muted-foreground">完成时间</span>
                <span>{formatDate(task.finished_at)}</span>
              </div>

              {task.error && (
                <div className="rounded bg-red-50 p-3 text-red-700 text-xs break-all">
                  {task.error}
                </div>
              )}

              {sortedTimings.length > 0 && (
                <div>
                  <p className="font-medium mb-2">节点耗时</p>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>节点</TableHead>
                        <TableHead className="text-right">耗时</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedTimings.map(([node, ms]) => (
                        <TableRow key={node}>
                          <TableCell>{node}</TableCell>
                          <TableCell className="text-right">{ms} ms</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Chunk 列表区块 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Chunk 列表（共 {total} 条）</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => fetchChunks(page)} disabled={chunksLoading}>
              <RefreshCw className={cn("h-4 w-4", chunksLoading && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {chunksLoading && chunks.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">加载中…</p>
          ) : chunks.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">暂无 Chunk</p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">序号</TableHead>
                    <TableHead>内容预览</TableHead>
                    <TableHead className="w-[180px]">创建时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {chunks.map((chunk) => (
                    <Fragment key={chunk.id}>
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() =>
                          setExpandedId(expandedId === chunk.id ? null : chunk.id)
                        }
                      >
                        <TableCell className="text-muted-foreground">
                          <div className="flex items-center gap-1">
                            {expandedId === chunk.id ? (
                              <ChevronDown className="h-3 w-3" />
                            ) : (
                              <ChevronRight className="h-3 w-3" />
                            )}
                            {chunk.chunk_index}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="line-clamp-2 text-sm">
                            {chunk.content.slice(0, 120)}
                            {chunk.content.length > 120 ? "…" : ""}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(chunk.created_at)}
                        </TableCell>
                      </TableRow>

                      {expandedId === chunk.id && (
                        <TableRow>
                          <TableCell colSpan={3} className="bg-muted/30 p-4">
                            <div className="space-y-3">
                              <div>
                                <p className="text-xs font-medium text-muted-foreground mb-1">完整内容</p>
                                <pre className="text-sm whitespace-pre-wrap break-all bg-background rounded p-3 border">
                                  {chunk.content}
                                </pre>
                              </div>
                              {Object.keys(chunk.metadata).length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground mb-1">Metadata</p>
                                  <pre className="text-xs bg-background rounded p-3 border overflow-auto">
                                    {JSON.stringify(chunk.metadata, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </Fragment>
                  ))}
                </TableBody>
              </Table>

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-end gap-2 mt-4 text-sm">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1 || chunksLoading}
                    onClick={() => handlePageChange(page - 1)}
                  >
                    上一页
                  </Button>
                  <span className="text-muted-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages || chunksLoading}
                    onClick={() => handlePageChange(page + 1)}
                  >
                    下一页
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
