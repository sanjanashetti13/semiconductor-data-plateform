import { Modal } from "@/components/ui/modal";
import { ArrowDown } from "lucide-react";

interface ArchitectureModalProps {
  open: boolean;
  onClose: () => void;
}

const STAGES = [
  "Azure Databricks",
  "Azure SQL",
  "FastAPI",
  "AI Copilot",
  "React",
];

export function ArchitectureModal({ open, onClose }: ArchitectureModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Architecture" wide>
      <div className="space-y-3">
        {STAGES.map((stage, index) => (
          <div key={stage} className="flex flex-col items-center">
            <div className="w-full rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-center text-sm font-medium text-zinc-100">
              {stage}
            </div>
            {index < STAGES.length - 1 && (
              <ArrowDown className="my-2 h-4 w-4 text-zinc-500" aria-hidden />
            )}
          </div>
        ))}
        <p className="pt-2 text-center text-xs text-zinc-500">
          Power BI connects to Azure SQL separately for executive dashboards.
        </p>
      </div>
    </Modal>
  );
}
