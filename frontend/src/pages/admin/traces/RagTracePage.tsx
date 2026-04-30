import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Activity, Clock3, Layers, RefreshCw, Search, TrendingUp } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ragTraceService } from "@/services/ragTraceService";
import type { TraceRun } from "@/types";
import { getErrorMessage } from "@/utils/error";
import { RunsTable } from "@/pages/admin/traces/components/RunsTable";
import { StatCard, type StatCardTone } from "@/pages/admin/traces/components/StatCard";

const PAGE_SIZE = 20;

type DurationMetric = {
  value: string;
  unit: string;
};

const formatDurationMetric = (durationMs: number): DurationMetric => {
  const duration = Number.isFinite(durationMs) && durationMs > 0 ? durationMs : 0;
  if (duration < 1000) {
    return { value: `${Math.round(duration)}`, unit: "ms" };
  }
  if (duration < 60_000) {
    return { value: (duration / 1000).toFixed(2), unit: "s" };
  }
  return { value: (duration / 1000).toFixed(1), unit: "s" };
};

export function RagTracePage() {
  const runsRequestRef = useRef(0);
  const [queryFilter, setQueryFilter] = useState("");
  const [pageNo, setPageNo] = useState(1);
  const [allRuns, setAllRuns] = useState<TraceRun[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRuns = async () => {
    const requestId = ++runsRequestRef.current;
    setLoading(true);
    try {
      const res = await ragTraceService.listRuns();
      if (runsRequestRef.current !== requestId) return;
      setAllRuns(res.data);
    } catch (error) {
      if (runsRequestRef.current !== requestId) return;
      toast.error(getErrorMessage(error, "加载链路运行列表失败"));
      console.error(error);
    } finally {
      if (runsRequestRef.current !== requestId) return;
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleSearch = () => {
    setPageNo(1);
  };

  const handleRefresh = () => {
    loadRuns();
  };

  // Filter by query string
  const filteredRuns = useMemo(() => {
    const q = queryFilter.trim().toLowerCase();
    if (!q) return allRuns;
    return allRuns.filter((r) => r.query.toLowerCase().includes(q) || r.id.toLowerCase().includes(q));
  }, [allRuns, queryFilter]);

  // Paginate client-side
  const total = filteredRuns.length;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.min(pageNo, pages);
  const runs = filteredRuns.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const stats = useMemo(() => ({
    total: filteredRuns.length,
    success: filteredRuns.filter((r) => r.status === "success").length,
    failed: filteredRuns.filter((r) => r.status === "failed").length,
    running: filteredRuns.filter((r) => r.status === "running").length,
    avgDurationMs: filteredRuns.length
      ? Math.round(filteredRuns.reduce((s, r) => s + r.total_duration_ms, 0) / filteredRuns.length)
      : 0,
  }), [filteredRuns]);

  const successRate = stats.total ? Math.round((stats.success / stats.total) * 1000) / 10 : 0;
  const avgDurationMetric = formatDurationMetric(stats.avgDurationMs);

  const statCards: {
    key: string;
    title: string;
    value: string;
    unit?: string;
    icon: ReactNode;
    tone: StatCardTone;
  }[] = [
    {
      key: "status",
      title: "成功 / 失败 / 运行中",
      value: `${stats.success} / ${stats.failed} / ${stats.running}`,
      icon: <Activity className="h-4 w-4" />,
      tone: "emerald"
    },
    {
      key: "successRate",
      title: "成功率",
      value: `${successRate}%`,
      icon: <TrendingUp className="h-4 w-4" />,
      tone: "cyan"
    },
    {
      key: "avg",
      title: "平均耗时",
      value: avgDurationMetric.value,
      unit: avgDurationMetric.unit,
      icon: <Clock3 className="h-4 w-4" />,
      tone: "indigo"
    },
    {
      key: "total",
      title: "总运行次数",
      value: `${stats.total}`,
      icon: <Layers className="h-4 w-4" />,
      tone: "amber"
    }
  ];

  return (
    <div className="admin-page trace-page trace-list-page">
      <div className="trace-list-shell">
        <div className="admin-page-header">
          <div>
            <h1 className="admin-page-title">链路追踪</h1>
            <p className="admin-page-subtitle">
              独立列表页聚焦运行检索，点击任意运行记录进入详情页分析慢节点与失败节点
            </p>
          </div>
          <div className="admin-page-actions">
            <Input
              value={queryFilter}
              onChange={(event) => setQueryFilter(event.target.value)}
              placeholder="搜索 Query / Trace Id"
              className="w-[300px]"
            />
            <Button className="admin-primary-gradient" onClick={handleSearch}>
              <Search className="h-4 w-4 mr-2" />
              查询
            </Button>
            <Button variant="outline" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              刷新
            </Button>
          </div>
        </div>

        <section className="trace-list-stat-grid">
          {statCards.map((stat) => (
            <StatCard
              key={stat.key}
              title={stat.title}
              value={stat.value}
              unit={stat.unit}
              icon={stat.icon}
              tone={stat.tone}
            />
          ))}
        </section>

        <RunsTable
          runs={runs}
          loading={loading}
          current={currentPage}
          pages={pages}
          total={total}
          onPrevPage={() => setPageNo((prev) => Math.max(1, prev - 1))}
          onNextPage={() => setPageNo((prev) => Math.min(pages, prev + 1))}
        />
      </div>
    </div>
  );
}
