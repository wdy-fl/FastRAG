import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChevronRight, Eye } from "lucide-react";
import type { TraceRun } from "@/types";

// ── local helpers (replaced deleted traceUtils) ──────────────────────────────

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

function statusBadgeVariant(status: TraceRun["status"]): BadgeVariant {
  if (status === "success") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

function statusLabel(status: TraceRun["status"]): string {
  if (status === "success") return "成功";
  if (status === "failed") return "失败";
  if (status === "running") return "运行中";
  return status;
}

// ─────────────────────────────────────────────────────────────────────────────

interface RunsTableProps {
  runs: TraceRun[];
  loading: boolean;
  current: number;
  pages: number;
  total: number;
  onPrevPage: () => void;
  onNextPage: () => void;
  onViewDetail: (runId: string) => void;
}

export function RunsTable({
  runs,
  loading,
  current,
  pages,
  total,
  onPrevPage,
  onNextPage,
  onViewDetail,
}: RunsTableProps) {
  return (
    <Card className="trace-list-table-card">
      <div className="trace-list-table-header">
        <h2 className="trace-list-table-title">运行列表</h2>
        <p className="trace-list-table-description">按时间倒序查看运行记录，通过操作按钮进入独立详情页</p>
      </div>
      <CardContent className="trace-list-table-content">
        {loading ? (
          <div className="trace-list-table-empty">加载中...</div>
        ) : runs.length === 0 ? (
          <div className="trace-list-table-empty">暂无链路数据</div>
        ) : (
          <div className="trace-list-table-wrap">
            <Table className="trace-list-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="trace-col-run-id">Trace Id</TableHead>
                  <TableHead className="trace-col-meta">会话ID</TableHead>
                  <TableHead>Query</TableHead>
                  <TableHead className="trace-col-duration">耗时</TableHead>
                  <TableHead className="trace-col-status">状态</TableHead>
                  <TableHead>执行时间</TableHead>
                  <TableHead className="trace-col-action">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id} className="trace-list-table-row">
                    <TableCell className="trace-col-run-id">
                      <span className="trace-list-run-id" title={run.id}>
                        {run.id}
                      </span>
                    </TableCell>
                    <TableCell className="trace-col-meta">
                      <p className="trace-list-run-meta-line" title={`会话ID: ${run.conversation_id || "-"}`}>
                        {run.conversation_id || "-"}
                      </p>
                    </TableCell>
                    <TableCell>
                      <span className="line-clamp-2" title={run.query}>
                        {run.query}
                      </span>
                    </TableCell>
                    <TableCell className="trace-col-duration trace-list-duration-cell">
                      {formatDuration(run.total_duration_ms)}
                    </TableCell>
                    <TableCell className="trace-col-status trace-list-status-cell">
                      <Badge className="trace-list-status-badge" variant={statusBadgeVariant(run.status)}>
                        {statusLabel(run.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatDateTime(run.created_at)}</TableCell>
                    <TableCell className="trace-col-action trace-list-action-cell">
                      <Button
                        size="sm"
                        variant="outline"
                        className="trace-list-action-btn"
                        onClick={() => onViewDetail(run.id)}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        查看链路
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <div className="trace-list-table-footer">
          <span className="trace-list-table-meta">
            第 {current} / {pages} 页，共 {total.toLocaleString("zh-CN")} 条
          </span>
          <div className="trace-list-pagination">
            <Button
              className="trace-list-pagination-btn"
              variant="outline"
              disabled={current <= 1 || loading}
              onClick={onPrevPage}
            >
              上一页
            </Button>
            <Button
              className="trace-list-pagination-btn"
              variant="outline"
              disabled={current >= pages || loading}
              onClick={onNextPage}
            >
              下一页
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
