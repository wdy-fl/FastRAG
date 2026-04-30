import { useMemo, useState, type KeyboardEvent } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowLeftRight,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Database,
  GitBranch,
  Github,
  Menu,
  MessageSquare,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type MenuItem = {
  path: string;
  label: string;
  icon: any;
};

type MenuGroup = {
  title: string;
  items: MenuItem[];
};

const menuGroups: MenuGroup[] = [
  {
    title: "导航",
    items: [
      { path: "/admin/knowledge", label: "知识库管理", icon: Database },
      { path: "/admin/intent-list", label: "Intent 管理", icon: GitBranch },
      { path: "/admin/traces", label: "Trace 日志", icon: Activity },
      { path: "/admin/mapping", label: "查询词映射", icon: ArrowLeftRight },
    ],
  },
];

const breadcrumbMap: Record<string, string> = {
  knowledge: "知识库管理",
  "intent-list": "Intent 管理",
  traces: "Trace 日志",
  mapping: "查询词映射",
};

export function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [starCount, setStarCount] = useState<number | null>(null);
  const [kbQuery, setKbQuery] = useState("");

  const breadcrumbs = useMemo(() => {
    const segments = location.pathname.split("/").filter(Boolean);
    const items: { label: string; to?: string }[] = [
      { label: "首页", to: "/admin/knowledge" },
    ];

    if (segments[0] !== "admin") return items;
    const section = segments[1];
    if (section) {
      if (section === "intent-list") {
        if (segments.includes("edit")) {
          items.push({ label: breadcrumbMap[section] || section, to: "/admin/intent-list" });
          items.push({ label: "编辑节点" });
        } else {
          items.push({ label: breadcrumbMap[section] || section });
        }
      } else {
        items.push({ label: breadcrumbMap[section] || section, to: `/admin/${section}` });
      }
    }

    if (section === "knowledge" && segments.length > 2) {
      items.push({ label: "文档管理" });
    }

    return items;
  }, [location.pathname]);

  const starLabel = useMemo(() => {
    if (starCount === null) return "--";
    if (starCount < 1000) return String(starCount);
    const rounded = Math.round((starCount / 1000) * 10) / 10;
    return `${String(rounded).replace(/\.0$/, "")}k`;
  }, [starCount]);

  const isLeafActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`);

  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && kbQuery.trim()) {
      navigate(`/admin/knowledge?name=${encodeURIComponent(kbQuery.trim())}`);
      setKbQuery("");
    }
  };

  return (
    <div className="admin-layout flex h-screen">
      <aside className={cn("admin-sidebar", collapsed && "admin-sidebar--collapsed")}>
        <div className="admin-sidebar__brand">
          <div className={cn("flex items-center gap-3", collapsed && "justify-center")}>
            <div className="admin-sidebar__logo">F</div>
            {!collapsed && (
              <div className="min-w-0">
                <h1 className="admin-sidebar__title">FastRAG 管理后台</h1>
                <p className="admin-sidebar__subtitle">Knowledge Console</p>
              </div>
            )}
          </div>
        </div>

        <nav className="flex-1 space-y-4 px-2 pb-4">
          {menuGroups.map((group) => (
            <div key={group.title} className="space-y-2">
              {!collapsed && (
                <p className="admin-sidebar__group-title">{group.title}</p>
              )}
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = isLeafActive(item.path);
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      title={collapsed ? item.label : undefined}
                      className={cn(
                        "admin-sidebar__item",
                        isActive && "admin-sidebar__item--active",
                        collapsed && "justify-center"
                      )}
                    >
                      <span
                        className={cn(
                          "admin-sidebar__item-indicator",
                          isActive && "is-active"
                        )}
                      />
                      <Icon className="admin-sidebar__item-icon" />
                      {collapsed ? (
                        <span className="sr-only">{item.label}</span>
                      ) : (
                        <span>{item.label}</span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="admin-sidebar__footer space-y-2">
          <button
            type="button"
            className="admin-sidebar__collapse"
            onClick={() => setCollapsed((prev) => !prev)}
          >
            {collapsed ? (
              <ChevronsRight className="h-4 w-4" />
            ) : (
              <ChevronsLeft className="h-4 w-4" />
            )}
            {!collapsed && <span>收起侧边栏</span>}
          </button>
        </div>
      </aside>

      <div className="admin-main flex min-h-screen flex-1 flex-col overflow-auto">
        <header className="admin-topbar">
          <div className="admin-topbar-inner">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden"
                onClick={() => setCollapsed((prev) => !prev)}
                aria-label="切换侧边栏"
              >
                <Menu className="h-5 w-5" />
              </Button>
              <div className="admin-topbar-search">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  value={kbQuery}
                  onChange={(e) => setKbQuery(e.target.value)}
                  onKeyDown={handleSearchKeyDown}
                  name="kb-search"
                  autoComplete="off"
                  placeholder="筛选知识库..."
                  className="pl-10 pr-4"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="hidden items-center gap-2 sm:inline-flex"
                onClick={() => navigate("/chat")}
              >
                <MessageSquare className="h-4 w-4" />
                返回聊天
              </Button>
              <a
                href="https://github.com/nageoffer/fastrag"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                aria-label="打开 GitHub 仓库"
              >
                <Github className="h-4 w-4" />
                <span className="font-medium">Star</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {starLabel}
                </span>
              </a>
            </div>
          </div>
        </header>

        <div className="admin-content">
          <nav className="admin-breadcrumbs" aria-label="面包屑">
            {breadcrumbs.map((item, index) => {
              const isLast = index === breadcrumbs.length - 1;
              return (
                <span key={`${item.label}-${index}`} className="flex items-center gap-2">
                  {item.to && !isLast ? (
                    <Link to={item.to}>{item.label}</Link>
                  ) : (
                    <span className={isLast ? "text-slate-700" : undefined}>{item.label}</span>
                  )}
                  {!isLast && <span>/</span>}
                </span>
              );
            })}
          </nav>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
