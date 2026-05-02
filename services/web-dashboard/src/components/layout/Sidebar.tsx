"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Droplets, History, Settings, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";
import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Overview" },
  { href: "/zones", icon: Droplets, label: "Zones" },
  { href: "/history", icon: History, label: "History" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "h-screen bg-secondary border-r border-border transition-all duration-300 flex flex-col",
        sidebarOpen ? "w-64" : "w-20"
      )}
    >
      <div className="p-6 flex items-center justify-between">
        {sidebarOpen && <h1 className="font-bold text-lg tracking-tight">Irrigation</h1>}
        <Button variant="ghost" size="icon" onClick={toggleSidebar} className="ml-auto">
          {sidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </Button>
      </div>

      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon size={20} />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        {sidebarOpen ? (
          <div className="px-3 py-2 text-xs text-muted-foreground uppercase tracking-wider font-semibold">
            v1.0.0
          </div>
        ) : (
          <div className="text-center text-[10px] text-muted-foreground font-bold">V1</div>
        )}
      </div>
    </aside>
  );
}
