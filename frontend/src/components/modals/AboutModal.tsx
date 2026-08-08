import { Modal } from "@/components/ui/modal";

interface AboutModalProps {
  open: boolean;
  onClose: () => void;
}

export function AboutModal({ open, onClose }: AboutModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="About">
      <div className="space-y-4 text-sm leading-relaxed text-zinc-300">
        <section>
          <h3 className="mb-1 font-medium text-zinc-100">Project overview</h3>
          <p>
            Azure Data Copilot is an AI workspace for analyzing your connected
            data. Ask natural-language questions about yield, sensors, production
            quality, or any Azure SQL database you connect. Power BI remains the
            system of record for dashboards.
          </p>
        </section>
        <section>
          <h3 className="mb-1 font-medium text-zinc-100">Architecture</h3>
          <p>
            Databricks prepares gold-layer data in Azure SQL. FastAPI exposes a
            modular AI copilot that routes questions to analytics tools and returns
            explanations through this React workspace.
          </p>
        </section>
        <section>
          <h3 className="mb-1 font-medium text-zinc-100">Technology stack</h3>
          <p>
            Azure Databricks · Azure SQL · Power BI · FastAPI · Groq · React ·
            Vite · Tailwind CSS
          </p>
        </section>
      </div>
    </Modal>
  );
}
