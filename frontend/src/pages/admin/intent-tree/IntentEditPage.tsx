import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { intentTreeService } from "@/services/intentTreeService";
import type { IntentNode } from "@/types";
import { getErrorMessage } from "@/utils/error";

const formSchema = z.object({
  name: z.string().min(1, "请输入节点名称").max(100, "名称不能超过100个字符"),
  level: z.number().int().min(0, "层级不能为负数"),
  parent_id: z.string().optional(),
  intent_type: z.string().min(1, "请输入意图类型"),
  keywords: z.string().optional(),
  description: z.string().optional()
});

type FormValues = z.infer<typeof formSchema>;

const emptyDefaults: FormValues = {
  name: "",
  level: 0,
  parent_id: "",
  intent_type: "classify",
  keywords: "",
  description: ""
};

const nodeToFormValues = (node: IntentNode): FormValues => ({
  name: node.name || "",
  level: node.level ?? 0,
  parent_id: node.parent_id || "",
  intent_type: node.intent_type || "classify",
  keywords: (node.keywords || []).join(", "),
  description: node.description || ""
});

export function IntentEditPage() {
  const navigate = useNavigate();
  const { id: routeId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const isEdit = Boolean(routeId && routeId !== "new");

  const returnTo = useMemo(() => {
    const from = searchParams.get("from") || "";
    if (from.startsWith("/admin/")) {
      return from;
    }
    return "/admin/intent-list";
  }, [searchParams]);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: emptyDefaults
  });

  useEffect(() => {
    if (!isEdit || !routeId) return;
    const loadNode = async () => {
      try {
        setLoading(true);
        const res = await intentTreeService.listNodes();
        const node = (res.data || []).find((n) => n.id === routeId);
        if (node) {
          form.reset(nodeToFormValues(node));
        } else {
          toast.error("未找到对应意图节点");
          navigate(returnTo);
        }
      } catch (error) {
        toast.error(getErrorMessage(error, "加载意图节点失败"));
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    loadNode();
  }, [isEdit, routeId, form, navigate, returnTo]);

  const handleSubmit = async (values: FormValues) => {
    const keywords = values.keywords
      ? values.keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean)
      : [];

    const payload = {
      name: values.name.trim(),
      level: values.level,
      parent_id: values.parent_id?.trim() || null,
      intent_type: values.intent_type.trim(),
      keywords,
      description: values.description?.trim() || ""
    };

    try {
      setSaving(true);
      if (isEdit && routeId) {
        await intentTreeService.updateNode(routeId, payload);
        toast.success("更新成功");
      } else {
        await intentTreeService.createNode(payload as Omit<IntentNode, "id">);
        toast.success("创建成功");
      }
      navigate(returnTo);
    } catch (error) {
      toast.error(getErrorMessage(error, isEdit ? "更新失败" : "创建失败"));
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-page">
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">加载中...</CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">{isEdit ? "编辑意图节点" : "新增意图节点"}</h1>
          <p className="admin-page-subtitle">
            {isEdit ? "修改节点基础信息" : "创建新的意图节点"}
          </p>
        </div>
        <div className="admin-page-actions">
          <Button variant="outline" onClick={() => navigate(returnTo)}>
            返回意图列表
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>节点配置</CardTitle>
          <CardDescription>填写意图节点的基础信息</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form className="space-y-4" onSubmit={form.handleSubmit(handleSubmit)}>
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>节点名称</FormLabel>
                      <FormControl>
                        <Input placeholder="例如：OA系统" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="level"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>层级</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          placeholder="例如：0"
                          value={field.value ?? ""}
                          onChange={(event) => {
                            const value = event.target.value;
                            field.onChange(value === "" ? 0 : Number(value));
                          }}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="intent_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>意图类型</FormLabel>
                      <FormControl>
                        <Input placeholder="例如：classify" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="parent_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>父节点 ID（可选）</FormLabel>
                      <FormControl>
                        <Input placeholder="留空表示根节点" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="keywords"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>关键词（逗号分隔）</FormLabel>
                    <FormControl>
                      <Input placeholder="例如：请假, 审批, OA" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>描述（可选）</FormLabel>
                    <FormControl>
                      <Textarea placeholder="节点语义说明与适用场景" rows={4} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => navigate(returnTo)} disabled={saving}>
                  取消
                </Button>
                <Button type="submit" className="admin-primary-gradient" disabled={saving}>
                  {saving ? "保存中..." : isEdit ? "保存修改" : "创建节点"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
