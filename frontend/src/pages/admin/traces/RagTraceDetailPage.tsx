import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ragTraceService } from "@/services/ragTraceService";
import type { TraceRunDetail } from "@/types";

function formatDuration(ms: number | undefined): string {
  if (ms == null || !Number.isFinite(ms) || ms <= 0) return "-";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)} s`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function formatDateTime(iso: string | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString("zh-CN", { hour12: false });
}

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

function statusBadgeVariant(status: string): BadgeVariant {
  if (status === "success") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

function statusLabel(status: string): string {
  if (status === "success") return "成功";
  if (status === "failed") return "失败";
  if (status === "running") return "运行中";
  return status;
}

export function RagTraceDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<TraceRunDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchRun = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    try {
      const res = await ragTraceService.getRun(runId);
      setRun(res.data);
    } catch {
      toast.error("加载 Trace 详情失败");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  const failedNodes = run?.nodes.filter((n) => n.status === "failed") ?? [];

  return (
    <div className="admin-page">
      {/* 页头 */}
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Trace 详情</h1>
        </div>
        <div className="admin-page-actions">
          <Button variant="outline" onClick={() => navigate("/admin/traces")}>
            返回链路列表
          </Button>
        </div>
      </div>

      {/* Run 信息 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Run 信息</CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchRun} disabled={loading}>
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-muted-foreground">加载中…</p>}
          {run && !loading && (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-y-3 max-w-lg">
                <span className="text-muted-foreground">状态</span>
                <span>
                  <Badge variant={statusBadgeVariant(run.status)}>
                    {statusLabel(run.status)}
                  </Badge>
                </span>

                <span className="text-muted-foreground">总耗时</span>
                <span>{formatDuration(run.total_duration_ms)}</span>

                <span className="text-muted-foreground">执行时间</span>
                <span>{formatDateTime(run.created_at)}</span>

                <span className="text-muted-foreground">Query</span>
                <span className="break-all">{run.query}</span>
              </div>

              {failedNodes.length > 0 && (
                <div className="rounded bg-red-50 p-3 text-red-700 text-xs space-y-1">
                  {failedNodes.map((n) => (
                    <div key={n.node_name}>
                      <span className="font-medium">{n.node_name}：</span>
                      {n.error ?? "未知错误"}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 节点执行 */}
      <Card>
        <CardHeader>
          <CardTitle>节点执行</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-muted-foreground py-4">加载中…</p>}
          {run && !loading && run.nodes.length === 0 && (
            <p className="text-sm text-muted-foreground py-4">暂无节点数据</p>
          )}
          {run && !loading && run.nodes.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>节点名</TableHead>
                  <TableHead className="w-[100px]">状态</TableHead>
                  <TableHead className="w-[120px]">耗时</TableHead>
                  <TableHead>错误信息</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.nodes.map((node) => (
                  <TableRow key={node.node_name}>
                    <TableCell className="font-mono text-sm">{node.node_name}</TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(node.status)}>
                        {statusLabel(node.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDuration(node.duration_ms)}</TableCell>
                    <TableCell className="text-xs text-red-600 break-all">
                      {node.error ?? "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
