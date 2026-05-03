import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { knowledgeService } from "@/services/knowledgeService";
import { STATUS_COLORS, STATUS_LABELS } from "@/utils/documentStatus";
import type { IngestionTaskResponse, DocumentStatus } from "@/types";

interface Props {
  kbId: string;
  docId: string;
  filename: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

const formatDate = (value: string | null) => {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN");
};

export function IngestionTaskDetailDrawer({ kbId, docId, filename, open, onOpenChange }: Props) {
  const [task, setTask] = useState<IngestionTaskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    knowledgeService
      .getIngestionTask(kbId, docId)
      .then(({ data }) => setTask(data))
      .catch(() => setError("加载任务详情失败"))
      .finally(() => setLoading(false));
  }, [open, kbId, docId]);

  // 按耗时降序，仅含成功节点
  const sortedTimings = task
    ? Object.entries(task.node_timings).sort(([, a], [, b]) => b - a)
    : [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[420px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="truncate pr-6" title={filename}>
            {filename}
          </SheetTitle>
        </SheetHeader>

        {loading && (
          <p className="text-sm text-muted-foreground mt-6">加载中…</p>
        )}

        {error && (
          <p className="text-sm text-destructive mt-6">{error}</p>
        )}

        {task && !loading && (
          <div className="mt-6 space-y-5 text-sm">
            {/* 基础信息 */}
            <div className="grid grid-cols-2 gap-y-3">
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

            {/* 错误信息 */}
            {task.error && (
              <div className="rounded bg-red-50 p-3 text-red-700 text-xs break-all">
                {task.error}
              </div>
            )}

            {/* 节点耗时 */}
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
      </SheetContent>
    </Sheet>
  );
}
