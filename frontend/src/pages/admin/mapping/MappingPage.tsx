import { useEffect, useState } from "react";
import { mappingService } from "@/services/mappingService";
import { knowledgeService } from "@/services/knowledgeService";
import type { Mapping, KnowledgeBase } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";

export default function MappingPage() {
  const [mappings, setMappings] = useState<Mapping[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [sourceTerm, setSourceTerm] = useState("");
  const [targetTerm, setTargetTerm] = useState("");
  const [kbId, setKbId] = useState("");
  const [loading, setLoading] = useState(false);

  async function fetchData() {
    const [mRes, kRes] = await Promise.all([
      mappingService.list(),
      knowledgeService.listKnowledgeBases(),
    ]);
    setMappings(mRes.data);
    setKbs(kRes.data);
  }

  useEffect(() => { fetchData(); }, []);

  async function handleCreate() {
    if (!sourceTerm || !targetTerm || !kbId) {
      toast.error("请填写所有字段");
      return;
    }
    setLoading(true);
    try {
      await mappingService.create({ source_term: sourceTerm, target_term: targetTerm, knowledge_base_id: kbId });
      toast.success("创建成功");
      setSourceTerm(""); setTargetTerm(""); setKbId("");
      fetchData();
    } catch {
      toast.error("创建失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    await mappingService.delete(id);
    toast.success("已删除");
    fetchData();
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">查询词映射</h1>
      <p className="text-muted-foreground text-sm">
        将用户查询中的词汇替换为知识库中的标准术语，提升检索召回率。
      </p>

      {/* 新增表单 */}
      <div className="border rounded-lg p-4 space-y-4 max-w-xl">
        <h2 className="font-semibold">新增映射</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label>原始词（用户输入）</Label>
            <Input value={sourceTerm} onChange={(e) => setSourceTerm(e.target.value)} placeholder="如：AI" />
          </div>
          <div className="space-y-1">
            <Label>目标词（检索用）</Label>
            <Input value={targetTerm} onChange={(e) => setTargetTerm(e.target.value)} placeholder="如：人工智能" />
          </div>
        </div>
        <div className="space-y-1">
          <Label>所属知识库</Label>
          <Select value={kbId} onValueChange={setKbId}>
            <SelectTrigger>
              <SelectValue placeholder="选择知识库" />
            </SelectTrigger>
            <SelectContent>
              {kbs.map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>{kb.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={handleCreate} disabled={loading}>
          {loading ? "创建中..." : "添加映射"}
        </Button>
      </div>

      {/* 列表 */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>原始词</TableHead>
            <TableHead>目标词</TableHead>
            <TableHead>知识库</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {mappings.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">暂无数据</TableCell>
            </TableRow>
          )}
          {mappings.map((m) => (
            <TableRow key={m.id}>
              <TableCell>{m.source_term}</TableCell>
              <TableCell>{m.target_term}</TableCell>
              <TableCell>{kbs.find((k) => k.id === m.knowledge_base_id)?.name ?? m.knowledge_base_id}</TableCell>
              <TableCell>{new Date(m.created_at).toLocaleString("zh-CN")}</TableCell>
              <TableCell>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(m.id)}>
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
