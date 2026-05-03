import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FileUp, FolderOpen, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import type { KnowledgeBase, Document } from "@/types";
import { knowledgeService } from "@/services/knowledgeService";
import { STATUS_COLORS, STATUS_LABELS, IN_PROGRESS_STATUSES } from "@/utils/documentStatus";
import { IngestionTaskDetailDrawer } from "@/components/admin/IngestionTaskDetailDrawer";

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN");
};

export function KnowledgeDocumentsPage() {
  const { kbId } = useParams();
  const navigate = useNavigate();

  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const [detailDoc, setDetailDoc] = useState<Document | null>(null);

  // Upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const loadKnowledgeBase = async () => {
    if (!kbId) return;
    try {
      const res = await knowledgeService.listKnowledgeBases();
      const found = res.data.find((item) => item.id === kbId);
      if (found) setKb(found);
    } catch (error) {
      console.error("加载知识库失败", error);
    }
  };

  const fetchDocuments = async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      const res = await knowledgeService.listDocuments(kbId);
      setDocuments(res.data);
    } catch (error) {
      toast.error("加载文档失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBase();
  }, [kbId]);

  useEffect(() => {
    fetchDocuments();
  }, [kbId]);


  const handleUpload = async () => {
    if (!uploadFile || !kbId) return;
    setUploading(true);
    try {
      await knowledgeService.uploadDocument(kbId, uploadFile);
      toast.success("文档上传成功，正在处理中...");
      setUploadFile(null);
      fetchDocuments();
    } catch {
      toast.error("上传失败");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget || !kbId) return;
    try {
      // deleteDocument not yet in service; show placeholder notice
      toast.info("删除功能暂未开放");
      setDeleteTarget(null);
    } catch (error) {
      toast.error("删除失败");
      console.error(error);
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">文档管理</h1>
          <p className="admin-page-subtitle">
            {kb ? `${kb.name}` : kbId}
          </p>
        </div>
        <div className="admin-page-actions">
          <Button variant="outline" onClick={() => navigate("/admin/knowledge")}>
            返回知识库
          </Button>
        </div>
      </div>

      {/* Upload Section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileUp className="h-4 w-4" />
            上传文档
          </CardTitle>
          <CardDescription>选择文件上传至知识库</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="max-w-sm">
            <Label htmlFor="upload-file" className="mb-2 block text-sm font-medium">
              选择文件
            </Label>
            <Input
              id="upload-file"
              type="file"
              onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              解析与分块策略由知识库摄取配置决定，可在知识库设置中调整。
            </p>
          </div>

          <div className="mt-4">
            <Button
              className="admin-primary-gradient"
              disabled={!uploadFile || uploading}
              onClick={handleUpload}
            >
              <FileUp className="mr-2 h-4 w-4" />
              {uploading ? "上传中..." : "上传"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Document List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>文档列表</CardTitle>
              <CardDescription>共 {documents.length} 个文档</CardDescription>
            </div>
            <Button variant="outline" onClick={fetchDocuments} disabled={loading}>
              <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading && documents.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">加载中...</div>
          ) : documents.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">暂无文档，请先上传</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[280px]">文件名</TableHead>
                  <TableHead className="w-[120px]">来源类型</TableHead>
                  <TableHead className="w-[120px]">状态</TableHead>
                  <TableHead className="w-[90px]">分块数</TableHead>
                  <TableHead className="w-[180px]">创建时间</TableHead>
                  <TableHead className="w-[80px] text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="font-medium">
                      <div className="flex min-w-0 max-w-[280px] items-center gap-2">
                        <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="truncate" title={doc.filename}>
                          {doc.filename || "-"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">
                        {doc.source_type || "-"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                          STATUS_COLORS[doc.status] ?? "bg-gray-100 text-gray-700"
                        )}
                      >
                        {STATUS_LABELS[doc.status] ?? doc.status}
                      </span>
                    </TableCell>
                    <TableCell>{doc.chunk_count ?? "-"}</TableCell>
                    <TableCell>{formatDate(doc.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setDetailDoc(doc)}
                        >
                          详情
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeleteTarget(doc)}
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4" />
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

      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => (!open ? setDeleteTarget(null) : undefined)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除文档？</AlertDialogTitle>
            <AlertDialogDescription>
              文档 [{deleteTarget?.filename}] 将被删除，且向量数据会清理。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {detailDoc && (
        <IngestionTaskDetailDrawer
          kbId={kbId!}
          docId={detailDoc.id}
          filename={detailDoc.filename}
          open={!!detailDoc}
          onOpenChange={(v) => { if (!v) setDetailDoc(null); }}
        />
      )}
    </div>
  );
}
