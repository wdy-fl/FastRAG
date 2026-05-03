import { useState } from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { knowledgeService } from "@/services/knowledgeService";
import { toast } from "sonner";
import type { KnowledgeBase, IngestionConfig } from "@/types";

interface Props {
  kb: KnowledgeBase;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSaved: (updated: KnowledgeBase) => void;
}

export function KbIngestionConfigDialog({ kb, open, onOpenChange, onSaved }: Props) {
  const cfg = kb.ingestion_config ?? {};

  const [parserType, setParserType] = useState(cfg.parser?.parser_type ?? "unstructured");
  const [chunkerType, setChunkerType] = useState(cfg.chunker?.chunker_type ?? "structure_aware");
  const [minChars, setMinChars] = useState(cfg.chunker?.min_chars ?? 600);
  const [targetChars, setTargetChars] = useState(cfg.chunker?.target_chars ?? 1400);
  const [maxChars, setMaxChars] = useState(cfg.chunker?.max_chars ?? 1800);
  const [chunkSize, setChunkSize] = useState(cfg.chunker?.chunk_size ?? 500);
  const [overlap, setOverlap] = useState(cfg.chunker?.overlap ?? 50);

  const [enhancerEnabled, setEnhancerEnabled] = useState(cfg.enhancer != null);
  const [enhancerModel, setEnhancerModel] = useState(cfg.enhancer?.model_id ?? "");
  const [enhancerTasks, setEnhancerTasks] = useState<string[]>(
    cfg.enhancer?.tasks?.map((t) => t.type) ?? []
  );

  const [enricherEnabled, setEnricherEnabled] = useState(cfg.enricher != null);
  const [enricherModel, setEnricherModel] = useState(cfg.enricher?.model_id ?? "");
  const [attachMeta, setAttachMeta] = useState(cfg.enricher?.attach_document_metadata ?? true);
  const [enricherTasks, setEnricherTasks] = useState<string[]>(
    cfg.enricher?.tasks?.map((t) => t.type) ?? []
  );

  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const ingestionConfig: IngestionConfig = {
        parser: { parser_type: parserType as "unstructured" | "markdown" },
        chunker:
          chunkerType === "structure_aware"
            ? { chunker_type: "structure_aware", min_chars: minChars, target_chars: targetChars, max_chars: maxChars }
            : { chunker_type: chunkerType as "fixed" | "sentence" | "paragraph", chunk_size: chunkSize, overlap },
        enhancer: enhancerEnabled
          ? {
              model_id: enhancerModel || undefined,
              tasks: enhancerTasks.map((type) => ({
                type: type as "context_enhance" | "keywords" | "questions" | "metadata",
              })),
            }
          : null,
        enricher: enricherEnabled
          ? {
              model_id: enricherModel || undefined,
              attach_document_metadata: attachMeta,
              tasks: enricherTasks.map((type) => ({
                type: type as "keywords" | "summary" | "metadata",
              })),
            }
          : null,
      };
      const { data } = await knowledgeService.updateKnowledgeBase(kb.id, { ingestion_config: ingestionConfig });
      onSaved(data);
      toast.success("摄取配置已保存");
      onOpenChange(false);
    } catch {
      toast.error("保存失败");
    } finally {
      setSaving(false);
    }
  };

  const toggleTask = (list: string[], setList: (v: string[]) => void, type: string, checked: boolean) => {
    setList(checked ? [...list, type] : list.filter((t) => t !== type));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>摄取配置 · {kb.name}</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-2">
          {/* ① 解析与分块 */}
          <div className="space-y-3">
            <p className="font-medium text-sm">解析与分块</p>
            <div className="grid grid-cols-2 items-center gap-x-4 gap-y-3">
              <Label>Parser 类型</Label>
              <Select value={parserType} onValueChange={setParserType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="unstructured">unstructured</SelectItem>
                  <SelectItem value="markdown">markdown</SelectItem>
                </SelectContent>
              </Select>

              <Label>Chunker 类型</Label>
              <Select value={chunkerType} onValueChange={setChunkerType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="structure_aware">structure_aware</SelectItem>
                  <SelectItem value="fixed">fixed</SelectItem>
                  <SelectItem value="sentence">sentence</SelectItem>
                  <SelectItem value="paragraph">paragraph</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {chunkerType === "structure_aware" ? (
              <div className="grid grid-cols-2 items-center gap-x-4 gap-y-3">
                <Label>最小块字符数</Label>
                <Input type="number" value={minChars} onChange={(e) => setMinChars(+e.target.value)} />
                <Label>目标块字符数</Label>
                <Input type="number" value={targetChars} onChange={(e) => setTargetChars(+e.target.value)} />
                <Label>最大块字符数</Label>
                <Input type="number" value={maxChars} onChange={(e) => setMaxChars(+e.target.value)} />
              </div>
            ) : (
              <div className="grid grid-cols-2 items-center gap-x-4 gap-y-3">
                <Label>块大小（字符）</Label>
                <Input type="number" value={chunkSize} onChange={(e) => setChunkSize(+e.target.value)} />
                <Label>重叠（字符）</Label>
                <Input type="number" value={overlap} onChange={(e) => setOverlap(+e.target.value)} />
              </div>
            )}
          </div>

          {/* ② LLM 增强（Enhancer） */}
          <div className="space-y-3">
            <p className="font-medium text-sm">LLM 增强（Enhancer）</p>
            <div className="flex items-center gap-2">
              <Switch checked={enhancerEnabled} onCheckedChange={setEnhancerEnabled} id="enhancer-switch" />
              <Label htmlFor="enhancer-switch">启用 Enhancer</Label>
            </div>
            {enhancerEnabled && (
              <div className="grid grid-cols-2 items-start gap-x-4 gap-y-3">
                <Label className="pt-2">模型 ID</Label>
                <Input
                  placeholder="留空使用默认模型"
                  value={enhancerModel}
                  onChange={(e) => setEnhancerModel(e.target.value)}
                />
                <Label className="pt-1">内置任务</Label>
                <div className="flex flex-col gap-2">
                  {(
                    [
                      { value: "context_enhance", label: "上下文增强" },
                      { value: "keywords", label: "关键词提取" },
                      { value: "questions", label: "问题生成" },
                      { value: "metadata", label: "元数据" },
                    ] as const
                  ).map(({ value, label }) => (
                    <label key={value} className="flex items-center gap-2 text-sm cursor-pointer">
                      <Checkbox
                        checked={enhancerTasks.includes(value)}
                        onCheckedChange={(v) => toggleTask(enhancerTasks, setEnhancerTasks, value, !!v)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ③ Chunk 丰富（Enricher） */}
          <div className="space-y-3">
            <p className="font-medium text-sm">Chunk 丰富（Enricher）</p>
            <div className="flex items-center gap-2">
              <Switch checked={enricherEnabled} onCheckedChange={setEnricherEnabled} id="enricher-switch" />
              <Label htmlFor="enricher-switch">启用 Enricher</Label>
            </div>
            {enricherEnabled && (
              <div className="grid grid-cols-2 items-start gap-x-4 gap-y-3">
                <Label className="pt-2">模型 ID</Label>
                <Input
                  placeholder="留空使用默认模型"
                  value={enricherModel}
                  onChange={(e) => setEnricherModel(e.target.value)}
                />
                <Label className="pt-2">附加文档元数据</Label>
                <Switch checked={attachMeta} onCheckedChange={setAttachMeta} />
                <Label className="pt-1">内置任务</Label>
                <div className="flex flex-col gap-2">
                  {(
                    [
                      { value: "keywords", label: "关键词提取" },
                      { value: "summary", label: "摘要" },
                      { value: "metadata", label: "元数据" },
                    ] as const
                  ).map(({ value, label }) => (
                    <label key={value} className="flex items-center gap-2 text-sm cursor-pointer">
                      <Checkbox
                        checked={enricherTasks.includes(value)}
                        onCheckedChange={(v) => toggleTask(enricherTasks, setEnricherTasks, value, !!v)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中…" : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
