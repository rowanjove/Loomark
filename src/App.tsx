import React, { useState, useEffect } from "react";
import { Project, DocumentItem, CrawlJob } from "./types";
import { api } from "./services/api";
import { Sidebar, NavTab } from "./components/layout/Sidebar";
import { StatusBar } from "./components/layout/StatusBar";
import { ProjectList } from "./components/projects/ProjectList";
import { ProjectDetail } from "./components/projects/ProjectDetail";
import { CreateProjectModal } from "./components/projects/CreateProjectModal";
import { CrawlWizard } from "./components/crawl/CrawlWizard";
import { CrawlMonitor } from "./components/crawl/CrawlMonitor";
import { DocumentTable } from "./components/documents/DocumentTable";
import { DocumentViewer } from "./components/documents/DocumentViewer";
import { ExportModal } from "./components/export/ExportModal";
import { MonitoringView } from "./components/monitoring/MonitoringView";
import { PluginsView } from "./components/plugins/PluginsView";
import { SettingsView } from "./components/settings/SettingsView";
import { ResearchView } from "./components/research/ResearchView";
import { WorkflowGuideModal } from "./components/guide/WorkflowGuideModal";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJobs, setActiveJobs] = useState<CrawlJob[]>([]);

  // Modals
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [isCrawlWizardOpen, setIsCrawlWizardOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<DocumentItem | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [exportDocIds, setExportDocIds] = useState<string[] | undefined>(undefined);
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  // Engine status
  const [engineOnline, setEngineOnline] = useState(true);

  const handleStartDemo = async () => {
    try {
      let demoProj = projects.find((p) => p.name.includes("MDN") || p.name.includes("示例"));
      if (!demoProj) {
        demoProj = await api.createProject(
          "MDN Web 技术文档采集",
          "新手快速体验项目：演示无需 AI 的纯规则文章提取与本地 Markdown 归档"
        );
        await fetchProjects();
      }
      setSelectedProject(demoProj);
      setIsCrawlWizardOpen(true);
    } catch (e: any) {
      alert("启动示例失败: " + e.message);
    }
  };

  const fetchProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
      setEngineOnline(true);
    } catch {
      setEngineOnline(false);
    }
  };

  const fetchActiveJobs = async () => {
    try {
      const allJobs = await api.getCrawlJobs();
      const running = allJobs.filter((j) => j.status === "RUNNING");
      setActiveJobs(running);
      if (!activeJobId && running.length > 0) {
        setActiveJobId(running[0].id);
      }
    } catch {}
  };

  useEffect(() => {
    fetchProjects();
    fetchActiveJobs();
    const timer = setInterval(() => {
      api.checkHealth().then(setEngineOnline);
      fetchActiveJobs();
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleCreateProject = async (name: string, description: string) => {
    const newProj = await api.createProject(name, description);
    await fetchProjects();
    setSelectedProject(newProj);
  };

  const handleDeleteProject = async (projectId: string) => {
    await api.deleteProject(projectId);
    if (selectedProject?.id === projectId) {
      setSelectedProject(null);
    }
    fetchProjects();
  };

  const handleStartCrawl = (project: Project) => {
    setSelectedProject(project);
    setIsCrawlWizardOpen(true);
  };

  const handleJobStarted = (jobId: string) => {
    setActiveJobId(jobId);
    setActiveTab("crawls");
  };

  return (
    <div className="flex h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          if (tab === "projects") {
            setSelectedProject(null);
          }
        }}
        onNewProject={() => setIsCreateProjectOpen(true)}
        onOpenGuide={() => setIsGuideOpen(true)}
      />

      {/* Main Work Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {/* View Switch */}
          {activeTab === "projects" && (
            selectedProject ? (
              <ProjectDetail
                project={selectedProject}
                onBack={() => {
                  setSelectedProject(null);
                  fetchProjects();
                }}
                onStartCrawl={handleStartCrawl}
                onSelectJob={(jobId) => {
                  setActiveJobId(jobId);
                  setActiveTab("crawls");
                }}
                onSelectDocument={(doc) => setSelectedDocument(doc)}
                onOpenExport={(docIds) => {
                  setExportDocIds(docIds);
                  setIsExportOpen(true);
                }}
                onOpenGuide={() => setIsGuideOpen(true)}
              />
            ) : (
              <ProjectList
                projects={projects}
                onSelectProject={(p) => setSelectedProject(p)}
                onNewProject={() => setIsCreateProjectOpen(true)}
                onDeleteProject={handleDeleteProject}
                onStartCrawl={handleStartCrawl}
                onOpenGuide={() => setIsGuideOpen(true)}
              />
            )
          )}

          {activeTab === "crawls" && (
            activeJobId ? (
              <CrawlMonitor
                jobId={activeJobId}
                onBack={() => setActiveTab("projects")}
                onViewDocuments={(projId) => {
                  const targetProj = projects.find((p) => p.id === projId);
                  if (targetProj) setSelectedProject(targetProj);
                  setActiveTab("documents");
                }}
              />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-zinc-500">
                <p className="text-sm font-medium text-zinc-300">当前没有运行中的采集任务</p>
                <p className="text-xs text-zinc-500 mt-1 mb-4">进入任意项目即可发起新的抓取。</p>
                <button
                  onClick={() => setActiveTab("projects")}
                  className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-md transition-colors"
                >
                  浏览项目列表
                </button>
              </div>
            )
          )}

          {activeTab === "documents" && (
            selectedProject ? (
              <DocumentTable
                projectId={selectedProject.id}
                onSelectDocument={(doc) => setSelectedDocument(doc)}
                onOpenExport={(docIds) => {
                  setExportDocIds(docIds);
                  setIsExportOpen(true);
                }}
              />
            ) : projects.length > 0 ? (
              <DocumentTable
                projectId={projects[0].id}
                onSelectDocument={(doc) => setSelectedDocument(doc)}
                onOpenExport={(docIds) => {
                  setExportDocIds(docIds);
                  setIsExportOpen(true);
                }}
              />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 text-xs">
                暂无项目，请先创建项目。
              </div>
            )
          )}

          {activeTab === "monitoring" && <MonitoringView projects={projects} />}

          {activeTab === "plugins" && <PluginsView />}

          {activeTab === "research" && <ResearchView projects={projects} />}

          {activeTab === "settings" && <SettingsView />}
        </main>

        {/* Global Bottom Status Bar */}
        <StatusBar
          engineOnline={engineOnline}
          activeJobsCount={activeJobs.length}
        />
      </div>

      {/* Global Modals */}
      <CreateProjectModal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        onCreate={handleCreateProject}
      />

      {selectedProject && (
        <CrawlWizard
          project={selectedProject}
          isOpen={isCrawlWizardOpen}
          onClose={() => setIsCrawlWizardOpen(false)}
          onJobStarted={handleJobStarted}
          onOpenGuide={() => setIsGuideOpen(true)}
        />
      )}

      {selectedDocument && (
        <DocumentViewer
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
        />
      )}

      {selectedProject && (
        <ExportModal
          projectId={selectedProject.id}
          docIds={exportDocIds}
          isOpen={isExportOpen}
          onClose={() => {
            setIsExportOpen(false);
            setExportDocIds(undefined);
          }}
        />
      )}

      {/* Beginner Workflow & Tutorial Modal */}
      <WorkflowGuideModal
        isOpen={isGuideOpen}
        onClose={() => setIsGuideOpen(false)}
        onStartDemo={handleStartDemo}
      />
    </div>
  );
};
