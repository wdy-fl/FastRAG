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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import type { KnowledgeBase, Document } from "@/types";
import { knowledgeService } from "@/services/knowledgeService";

const statusColors: Record<string, string> = {
  pending:   "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed:    "bg-red-100 text-red-800",
};

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

  // Upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [parserType, setParserType] = useState("markdown");
  const [chunkerType, setChunkerType] = useState("structure_aware");
  const [chunkSize, setChunkSize] = useState(512);
  const [overlap, setOverlap] = useState(50);
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

  // Poll every 3s when any document is still processing
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === "pending");
    if (!hasProcessing) return;
    const timer = setInterval(fetchDocuments, 3000);
    return () => clearInterval(timer);
  }, [documents]);

  const handleUpload = async () => {
    if (!uploadFile || !kbId) return;
    setUploading(true);
    try {
      await knowledgeService.uploadDocument(kbId, {
        file: uploadFile,
        parser_type: parserType,
        chunker_type: chunkerType,
        chunk_size: chunkSize,
        overlap,
      });
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
          <CardDescription>选择文件并配置解析与分块参数</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <div className="xl:col-span-2">
              <Label htmlFor="upload-file" className="mb-2 block text-sm font-medium">
                选择文件
              </Label>
              <Input
                id="upload-file"
                type="file"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              />
            </div>

            <div>
              <Label htmlFor="parser-type" className="mb-2 block text-sm font-medium">
                解析器
              </Label>
              <Select value={parserType} onValueChange={setParserType}>
                <SelectTrigger id="parser-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unstructured">unstructured</SelectItem>
                  <SelectItem value="markdown">markdown</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="chunker-type" className="mb-2 block text-sm font-medium">
                分块策略
              </Label>
              <Select value={chunkerType} onValueChange={setChunkerType}>
                <SelectTrigger id="chunker-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="structure_aware">structure_aware</SelectItem>
                  <SelectItem value="fixed">fixed</SelectItem>
                  <SelectItem value="sentence">sentence</SelectItem>
                  <SelectItem value="paragraph">paragraph</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="chunk-size" className="mb-2 block text-sm font-medium">
                块大小
              </Label>
              <Input
                id="chunk-size"
                type="number"
                min={64}
                max={4096}
                value={chunkSize}
                onChange={(e) => setChunkSize(Number(e.target.value))}
              />
            </div>

            <div>
              <Label htmlFor="overlap" className="mb-2 block text-sm font-medium">
                重叠大小
              </Label>
              <Input
                id="overlap"
                type="number"
                min={0}
                max={512}
                value={overlap}
                onChange={(e) => setOverlap(Number(e.target.value))}
              />
            </div>
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
                          statusColors[doc.status] ?? "bg-gray-100 text-gray-700"
                        )}
                      >
                        {doc.status}
                      </span>
                    </TableCell>
                    <TableCell>{doc.chunk_count ?? "-"}</TableCell>
                    <TableCell>{formatDate(doc.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteTarget(doc)}
                        title="删除"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
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
    </div>
  );
}
