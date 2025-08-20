"use client";

import { useState } from "react";
import { useProjectContext } from "~/hooks/project-context";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Button } from "~/components/ui/button";

export default function ProjectSelector() {
  const { projects, selectedProjectId, setSelectedProjectId, addProject } = useProjectContext();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  return (
    <div className="flex items-center gap-2">
      <Select
        value={selectedProjectId ?? undefined}
        onValueChange={(v) => setSelectedProjectId(v === "ALL" ? null : v)}
      >
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="All projects" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All projects</SelectItem>
          {projects.map((p) => (
            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">New</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Project</DialogTitle>
            <DialogDescription>Projects scope agents, runs, and logs within your team.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <input
              type="text"
              className="w-full rounded border px-3 py-2"
              placeholder="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                if (!name.trim()) return;
                addProject(name.trim());
                setName("");
                setOpen(false);
              }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

