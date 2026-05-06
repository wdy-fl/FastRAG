import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Pencil, RefreshCw, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { intentTreeService } from "@/services/intentTreeService";
import { knowledgeService } from "@/services/knowledgeService";
import type { IntentNode, KnowledgeBase } from "@/types";
import { getErrorMessage } from "@/utils/error";

const PAGE_SIZE_OPTIONS = [10, 20, 50];

const FILTER_INPUT_CLASS =
  "h-10 border-slate-200 pl-10 text-sm focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-slate-200";

export function IntentListPage() {
  const navigate = useNavigate();
  const [nodes, setNodes] = useState<IntentNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState("");
  const [pageNo, setPageNo] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);

  const loadNodes = async () => {
    try {
      setLoading(true);
      const res = await intentTreeService.listNodes();
      setNodes(res.data || []);
    } catch (error) {
      toast.error(getErrorMessage(error, "加载意图列表失败"));
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNodes();
    knowledgeService.listKnowledgeBases()
      .then((res) => setKbs(res.data || []))
      .catch((error) => {
        toast.error(getErrorMessage(error, "加载知识库列表失败"));
        console.error(error);
      });
  }, []);

  const filteredNodes = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return nodes.filter((node) => {
      if (normalizedKeyword) {
        const searchable = [node.name, node.id, (node.keywords || []).join(" ")]
          .join(" ")
          .toLowerCase();
        if (!searchable.includes(normalizedKeyword)) {
          return false;
        }
      }
      return true;
    });
  }, [nodes, keyword]);

  const total = filteredNodes.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(pageNo, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const pageNodes = filteredNodes.slice(startIndex, startIndex + pageSize);

  useEffect(() => {
    if (pageNo !== currentPage) {
      setPageNo(currentPage);
    }
  }, [currentPage, pageNo]);

  const handleResetFilters = () => {
    setKeyword("");
    setPageNo(1);
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await intentTreeService.deleteNode(id);
      toast.success("删除成功");
      await loadNodes();
    } catch (error) {
      toast.error(getErrorMessage(error, "删除失败"));
      console.error(error);
    } finally {
      setDeletingId(null);
    }
  };

  const rangeStart = total === 0 ? 0 : startIndex + 1;
  const rangeEnd = total === 0 ? 0 : Math.min(startIndex + pageNodes.length, total);
  const showPagination = !loading && total > 0;

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">意图列表</h1>
          <p className="admin-page-subtitle">查看和管理意图节点</p>
        </div>
        <div className="admin-page-actions">
          <Button
            className="admin-primary-gradient"
            onClick={() => navigate("/admin/intent-list/new/edit")}
          >
            新增意图节点
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="relative w-full lg:min-w-[280px] lg:max-w-[420px] lg:flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={keyword}
                onChange={(event) => {
                  setKeyword(event.target.value);
                  setPageNo(1);
                }}
                placeholder="搜索意图名称/关键词..."
                aria-label="搜索意图名称或关键词"
                className={FILTER_INPUT_CLASS}
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                className="h-10 gap-1.5 border-slate-200 px-3 text-sm"
                onClick={loadNodes}
                disabled={loading}
              >
                <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                刷新
              </Button>
              <Button
                variant="outline"
                className="h-10 gap-1.5 border-rose-200 bg-rose-50 px-3 text-sm font-medium text-rose-700 hover:bg-rose-100 hover:text-rose-800"
                onClick={handleResetFilters}
              >
                <X className="h-4 w-4" />
                清空筛选
              </Button>
            </div>
          </div>
        </div>
      </div>

      <Card className="overflow-hidden">
        <CardContent className="space-y-3 pt-4">
          {loading ? (
            <div className="py-10 text-center text-muted-foreground">加载中...</div>
          ) : pageNodes.length === 0 ? (
            <div className="py-10 text-center text-muted-foreground">
              {nodes.length === 0
                ? "暂无意图节点，点击「新增意图节点」创建"
                : "没有匹配结果，请调整筛选条件"}
            </div>
          ) : (
            <Table className="min-w-[700px] [&_th]:h-10 [&_th]:py-2 [&_td]:py-2">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[220px]">名称</TableHead>
                  <TableHead className="w-[160px]">知识库</TableHead>
                  <TableHead>关键词</TableHead>
                  <TableHead className="sticky right-0 z-20 w-[140px] bg-[#F9FAFB] text-left shadow-[-1px_0_0_rgba(226,232,240,1)]">
                    操作
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pageNodes.map((node) => (
                  <TableRow key={node.id} className="group text-[13px] hover:!bg-slate-50">
                    <TableCell>
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-900">{node.name}</div>
                        <div className="font-mono text-xs text-slate-400">{node.id}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-slate-600">
                        {node.knowledge_base_id
                          ? (kbs.find((kb) => kb.id === node.knowledge_base_id)?.name ?? node.knowledge_base_id)
                          : <span className="text-slate-300">-</span>}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-slate-600">
                        {(node.keywords && node.keywords.length > 0)
                          ? node.keywords.join(", ")
                          : <span className="text-slate-300">-</span>}
                      </span>
                    </TableCell>
                    <TableCell className="sticky right-0 z-10 bg-white shadow-[-1px_0_0_rgba(226,232,240,1)] group-hover:bg-slate-50">
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 px-2.5 text-xs"
                          title="编辑"
                          aria-label={`编辑 ${node.name}`}
                          onClick={() => navigate(`/admin/intent-list/${node.id}/edit`)}
                        >
                          <Pencil className="mr-0.5 h-4 w-4" />
                          编辑
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 px-2.5 text-xs text-destructive hover:text-destructive"
                              title="删除"
                              aria-label={`删除 ${node.name}`}
                              disabled={deletingId === node.id}
                            >
                              <Trash2 className="mr-0.5 h-4 w-4" />
                              删除
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>确认删除？</AlertDialogTitle>
                              <AlertDialogDescription>
                                将删除意图节点「{node.name}」，该操作不可恢复。
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                onClick={() => handleDelete(node.id)}
                              >
                                删除
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {showPagination ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-500">
          <span>
            共 {total} 条，显示 {rangeStart}-{rangeEnd}
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <span>每页</span>
            <Select
              value={String(pageSize)}
              onValueChange={(value) => {
                setPageSize(Number(value));
                setPageNo(1);
              }}
            >
              <SelectTrigger className="h-8 w-[92px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size} 条
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageNo(1)}
              disabled={currentPage <= 1}
            >
              首页
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageNo((prev) => Math.max(1, prev - 1))}
              disabled={currentPage <= 1}
            >
              上一页
            </Button>
            <span>
              {currentPage} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageNo((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage >= totalPages}
            >
              下一页
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageNo(totalPages)}
              disabled={currentPage >= totalPages}
            >
              末页
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
