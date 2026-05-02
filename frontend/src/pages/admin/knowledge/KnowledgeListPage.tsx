import { useEffect, useState } from "react";
import { FolderOpen, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import type { KnowledgeBase } from "@/types";
import { knowledgeService } from "@/services/knowledgeService";
import { CreateKnowledgeBaseDialog } from "@/components/admin/CreateKnowledgeBaseDialog";
import { getErrorMessage } from "@/utils/error";

export function KnowledgeListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nameFromQuery = searchParams.get("name") || "";
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [searchName, setSearchName] = useState(nameFromQuery);

  const loadKnowledgeBases = async () => {
    try {
      setLoading(true);
      const res = await knowledgeService.listKnowledgeBases();
      setKnowledgeBases(res.data);
    } catch (error) {
      toast.error(getErrorMessage(error, "加载知识库列表失败"));
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await knowledgeService.deleteKnowledgeBase(deleteTarget.id);
      toast.success("删除成功");
      setDeleteTarget(null);
      await loadKnowledgeBases();
    } catch (error) {
      toast.error(getErrorMessage(error, "删除失败"));
      console.error(error);
    } finally {
      setDeleteTarget(null);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("zh-CN");
  };

  const filtered = searchName.trim()
    ? knowledgeBases.filter((kb) =>
        kb.name.toLowerCase().includes(searchName.trim().toLowerCase())
      )
    : knowledgeBases;

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">知识库管理</h1>
          <p className="admin-page-subtitle">管理所有知识库及其文档</p>
        </div>
        <div className="admin-page-actions">
          <Input
            value={searchName}
            onChange={(event) => setSearchName(event.target.value)}
            placeholder="搜索知识库名称"
            className="w-[220px]"
          />
          <Button variant="outline" onClick={loadKnowledgeBases}>
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新
          </Button>
          <Button className="admin-primary-gradient" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            新建知识库
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">加载中...</div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              暂无知识库，点击上方按钮创建
            </div>
          ) : (
            <Table className="min-w-[640px]">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[220px]">名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead className="w-[180px]">创建时间</TableHead>
                  <TableHead className="w-[120px] text-left">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((kb) => (
                  <TableRow key={kb.id}>
                    <TableCell className="font-medium">
                      <span className="max-w-[220px] truncate block">{kb.name}</span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {kb.description || "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(kb.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/admin/knowledge/${kb.id}`)}
                        >
                          <FolderOpen className="w-4 h-4 mr-0.5" />
                          文档管理
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeleteTarget(kb)}
                        >
                          <Trash2 className="w-4 h-4 mr-0.5" />
                          删除
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              此操作将永久删除该知识库及其所有文档和数据，无法恢复。确定要继续吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 创建知识库对话框 */}
      <CreateKnowledgeBaseDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => loadKnowledgeBases()}
      />
    </div>
  );
}
